from Utils.Control.cardalgo import *
from Utils.Hardware.package import *
import cv2
import threading
import os
import time
import datetime
import numpy as np
import math
import tkinter as tk
from tkinter import ttk

# List to store the motor angle values
motor_angle_list = [0]


def command_listener(card, vibration_var, encoder_var, calibrate_btn_var, start_btn_var, stop_btn_var):
    """
    Thread function to listen for commands and control hardware accordingly.

    Parameters:
    - card: Hardware control object
    - vibration_var: Tkinter IntVar for vibration control
    - encoder_var: Tkinter IntVar for encoder angle
    - calibrate_btn_var: Tkinter IntVar for calibration button
    - start_btn_var: Tkinter IntVar for start button
    - stop_btn_var: Tkinter IntVar for stop button
    """
    hardware_started = False
    last_encoder_value = 0  # Track the last encoder value

    while True:
        if calibrate_btn_var.get() == 1:
            # Calibrate hardware
            print("Calibrating...")
            card.calibrate()
            calibrate_btn_var.set(0)
            last_encoder_value = 0  # Reset the last encoder value on calibration
            motor_angle_list.clear()  # Clear angle list
            motor_angle_list.append(0)  # Start angle list with zero after calibration
            print("Calibration done.")

        if start_btn_var.get() == 1:
            # Start hardware
            print("Starting hardware...")
            card.start_hardware()
            hardware_started = True
            start_btn_var.set(0)
            print("Hardware started.")

        if stop_btn_var.get() == 1:
            # Stop hardware
            print("Stopping hardware...")
            card.stop_hardware()
            hardware_started = False
            vibration_var.set(0)
            encoder_var.set(0)
            stop_btn_var.set(0)
            last_encoder_value = 0  # Reset the last encoder value on stop
            print("Hardware stopped and sliders reset.")

        if hardware_started:
            # Apply the vibration setting
            card.vibrate_hardware(vibration_var.get())

            # Calculate the difference for the encoder
            current_encoder_value = encoder_var.get()
            encoder_difference = current_encoder_value - last_encoder_value
            card.set_encoder_angle(encoder_difference)
            motor_angle_list.append(encoder_difference + motor_angle_list[-1])
            last_encoder_value = current_encoder_value  # Update the last encoder value

        time.sleep(0.1)


def main():
    """
    Main function to initialize the GUI and start the hardware control and video processing.
    """
    # Initialize the hardware control object
    card = Card(x_d=0, y_d=0, a_d=-1, x=-1, y=-1, a=-1, baud=115200, port='/dev/ttyACM0')
    algo = card_algorithms(x_d=0, y_d=0)  # Define the card algorithm object
    tip_pos = (323, 150)
    des_oreientation = random.randint(0,359)

    # Initialize the Tkinter root window
    root = tk.Tk()
    root.title("Hardware Control")

    # Tkinter variables for GUI controls
    vibration_var = tk.IntVar()
    encoder_var = tk.IntVar()
    calibrate_btn_var = tk.IntVar()
    start_btn_var = tk.IntVar()
    stop_btn_var = tk.IntVar()

    # Functions to update labels based on slider values
    def update_vibration_label(*args):
        vibration_label_var.set(f"Vibration: {vibration_var.get()}%")

    def update_encoder_label(*args):
        encoder_label_var.set(f"Encoder: {encoder_var.get()}°")

    # Trace changes to the variables to update labels
    vibration_var.trace_add("write", update_vibration_label)
    encoder_var.trace_add("write", update_encoder_label)

    vibration_label_var = tk.StringVar()
    encoder_label_var = tk.StringVar()

    # Initialize label text
    update_vibration_label()
    update_encoder_label()

    # Create and place GUI elements
    ttk.Label(root, text="Vibration (%)").grid(column=0, row=0, padx=10, pady=10)
    vibration_slider = ttk.Scale(root, from_=0, to=100, orient='horizontal', variable=vibration_var)
    vibration_slider.grid(column=1, row=0, padx=10, pady=10)
    ttk.Label(root, textvariable=vibration_label_var).grid(column=2, row=0, padx=10, pady=10)

    ttk.Label(root, text="Encoder (°)").grid(column=0, row=1, padx=10, pady=10)
    encoder_slider = ttk.Scale(root, from_=0, to=360, orient='horizontal', variable=encoder_var)
    encoder_slider.grid(column=1, row=1, padx=10, pady=10)
    ttk.Label(root, textvariable=encoder_label_var).grid(column=2, row=1, padx=10, pady=10)

    calibrate_btn = ttk.Button(root, text="Calibrate", command=lambda: calibrate_btn_var.set(1))
    calibrate_btn.grid(column=0, row=2, columnspan=2, padx=10, pady=10)

    start_btn = ttk.Button(root, text="Start", command=lambda: start_btn_var.set(1))
    start_btn.grid(column=0, row=3, columnspan=2, padx=10, pady=10)

    stop_btn = ttk.Button(root, text="Stop", command=lambda: stop_btn_var.set(1))
    stop_btn.grid(column=0, row=4, columnspan=2, padx=10, pady=10)

    # Functions to adjust slider values with arrow keys
    def adjust_vibration(event):
        if event.keysym == "Up":
            vibration_var.set(min(vibration_var.get() + 1, 100))
        elif event.keysym == "Down":
            vibration_var.set(max(vibration_var.get() - 1, 0))

    def adjust_encoder(event):
        if event.keysym == "Right":
            encoder_var.set(min(encoder_var.get() + 1, 360))
        elif event.keysym == "Left":
            encoder_var.set(max(encoder_var.get() - 1, 0))

    # Bind arrow keys to adjust functions
    root.bind("<Up>", adjust_vibration)
    root.bind("<Down>", adjust_vibration)
    root.bind("<Right>", adjust_encoder)
    root.bind("<Left>", adjust_encoder)

    # Start the command listener thread
    command_thread = threading.Thread(target=command_listener, args=(
        card, vibration_var, encoder_var, calibrate_btn_var, start_btn_var, stop_btn_var))
    command_thread.daemon = True
    command_thread.start()

    # Initialize video capture
    cap = cv2.VideoCapture(0)

    # Define the codec and create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'XVID')

    # Specify the directory path for saving the video
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    video_path = f"/home/roblab20/Desktop/experiments/output_{timestamp}.avi"
    out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))

    # Function to update video frame
    def update_frame():
        stop_applied = False
        calibrate_applied = False

        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            return

        frame_copy = frame.copy()  # Create a copy of the frame for drawing purposes

        # Detect circles and get centers
        frame, centers = algo.detect_circles_and_get_centers(frame_copy)

        # Detect ArUco markers and get their centers and ids
        aruco_centers, ids = algo.detect_aruco_centers(frame_copy)
        algo.arrow_coordinate_sys_motor(frame, tip_pos)
        if aruco_centers and ids is not None:
            for idx, center in enumerate(centers):
                # Display circle centers on the screen
                cv2.putText(frame, f"{(center[0], center[1])}", (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                # Calculate and display orientation angle
                angle = algo.ids_to_angle(frame ,ids, center, aruco_centers)
                if angle is not None:
                    orientation_error = abs(des_oreientation-angle)
                    end_orientation = (round(center[0] + 50 * math.cos(np.deg2rad(angle))),
                                       round(center[1] - 50 * math.sin(np.deg2rad(angle))))
                    end_des_orientation = (round(center[0] + 50 * math.cos(np.deg2rad(des_oreientation))),
                                       round(center[1] - 50 * math.sin(np.deg2rad(des_oreientation))))

                    cv2.putText(frame, f"Orientation: {angle}", (10, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                    cv2.putText(frame, f"Orientation_error: {orientation_error}", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)


                    cv2.arrowedLine(frame,  center, end_orientation, (255, 255, 0), 2)
                    cv2.arrowedLine(frame, center, end_des_orientation, (255, 0, 0), 2)

                    # Check if orientation error is less than 5 degrees
                    if orientation_error < 5 and not stop_applied:
                        print("Orientation error is less than 5 degrees")
                        stop_btn_var.set(1)  # Apply the stop button action
                        # calibrate_btn_var.set(1) # Apply the calibration button action
                        stop_applied = True  # Set the flag to prevent repeated action

                else:
                    print("Failed to calculate orientation angle")

        # Draw the motor angle on the frame
        if len(motor_angle_list) > 0:
            # tip_pos = (323, 150)
            start_point = tip_pos
            end_point = (round(tip_pos[0] + 50 * math.cos(np.deg2rad(motor_angle_list[-1]))),
                         round(tip_pos[1] - 50 * math.sin(np.deg2rad(motor_angle_list[-1]))))


            rotated_end_point = algo.rotate_point(start_point, end_point, 90)

            # Draw the rotated arrow
            cv2.arrowedLine(frame, start_point, tuple(rotated_end_point), (0, 0, 255), 2)

        # Write the frame to the video file
        out.write(frame)
        # Display the frame
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            root.quit()
            return

        # Schedule the next update
        root.after(10, update_frame)

    # Start updating frames
    root.after(10, update_frame)
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()

    # Release resources
    cap.release()
    out.release()  # Release the VideoWriter object
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
