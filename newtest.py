import tkinter as tk
import threading
import time
import numpy as np
from PIL import ImageGrab, ImageOps, Image
from skimage.color import rgb2lab

resized_width = 200
resized_height = 100
rate = .001
timeout_var = .5
rgb_threshold_percentage = 1000
luminance_threshold_percentage = 70
lum_consecutive_frames = 3
rgb_consecutive_frames = 3


class EpilepsyMonitor:
    def __init__(self):
        self.paused = False
        self.root = tk.Tk()
        self.root.title("Epilepsy Monitor")
        self.root.geometry("0x0")
        self.root.resizable(False, False)

        font = ("Helvetica", 14)
        label_color = "#333333"
        button_color = "#4CAF50"
        button_text_color = "white"

        self.label = tk.Label(
            self.root,
            text="Strange light activity detected, click to disregard",
            font=font,
            bg=label_color,
            fg="white",
            padx=20,
            pady=20,
        )
        self.label.pack(fill=tk.BOTH)

        self.ok_button = tk.Button(
            self.root,
            text="Okay",
            font=font,
            bg=button_color,
            fg=button_text_color,
            padx=10,
            pady=5,
            command=self.resume_screen
        )
        self.ok_button.pack(pady=10)

        self.last_luminance = None
        self.last_rgb_frame = None
        self.luminance_change_count = 0
        self.rgb_change_count = 0
        self.rgb_threshold_percentage = rgb_threshold_percentage
        self.luminance_threshold_percentage = luminance_threshold_percentage
        self.lum_consecutive_frames = lum_consecutive_frames
        self.rgb_consecutive_frames = rgb_consecutive_frames
        self.timeout_start = time.time()
        self.timeout_duration = timeout_var

        self.alert_shown = False

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.start_monitor_thread()
        self.root.mainloop()

    def start_monitor_thread(self):
        self.monitor_thread = threading.Thread(target=self.monitor_screen)
        self.monitor_thread.start()

    def monitor_screen(self):
        last_change_time = time.time()  # Initialize last_change_time
        while True:
            if not self.paused:
                screenshot = ImageGrab.grab(bbox=(0, 0, 1920, 1080))
                screenshot = screenshot.resize((resized_width, resized_height), Image.LANCZOS)
                current_rgb_frame = screenshot.convert("RGB")
                current_luminance, luminance_percentage_change = self.calculate_luminance(screenshot)
                rgb_percentage_change, _ = self.calculate_rgb_change(screenshot)
                self.last_luminance = current_luminance
                self.last_rgb_frame = screenshot

                # Check if the change counts exceed the consecutive frames threshold
                if (
                        self.rgb_change_count >= self.rgb_consecutive_frames

                ):
                    self.label.config(text="Strange light activity detected, click to disregard - RGB", bg="#333333")
                    self.pause_screen()
                    # Reset the change counts
                    self.luminance_change_count = 0
                    self.rgb_change_count = 0

                if (
                        self.luminance_change_count >= self.lum_consecutive_frames
                ):
                    self.label.config(text="Strange light activity detected, click to disregard - LUM", bg="#333333")
                    self.pause_screen()
                    # Reset the change counts
                    self.luminance_change_count = 0
                    self.rgb_change_count = 0

                # Update last_change_time when a change count is incremented
                if (
                        luminance_percentage_change >= self.luminance_threshold_percentage
                        or rgb_percentage_change >= self.rgb_threshold_percentage
                ):
                    last_change_time = time.time()  # Update last_change_time

                # Check if the timeout duration has passed
                if time.time() - last_change_time >= self.timeout_duration:
                    print("Timed Out, count has been reset.")
                    # Reset the change counts
                    self.luminance_change_count = 0
                    self.rgb_change_count = 0

                time.sleep(rate)

    def calculate_luminance(self, image):
        grayscale_image = ImageOps.grayscale(image)
        luminance = np.mean(grayscale_image)
        percentage_change = (
            abs(luminance - self.last_luminance) / (self.last_luminance + 1e-5) * 100
            if self.last_luminance is not None
            else 0
        )
        if percentage_change >= self.luminance_threshold_percentage:
            self.luminance_change_count += 1
            print(f"Luminance Change Count: {self.luminance_change_count}")
        print(f"Luminance Percentage Change: {percentage_change}")
        return luminance, percentage_change

    def calculate_rgb_change(self, current_frame):
        if isinstance(self.last_rgb_frame, Image.Image):
            current_lab_frame = rgb2lab(current_frame)
            lab_last_frame = rgb2lab(self.last_rgb_frame)

            # Get LAB values for each pixel
            pixels_current = list(current_lab_frame.reshape(-1, 3))
            pixels_last = list(lab_last_frame.reshape(-1, 3))

            # Calculate the color difference for each pixel
            color_differences = [
                abs(a1 - a2) + abs(b1 - b2)
                for (_, a1, b1), (_, a2, b2) in zip(pixels_current, pixels_last)
            ]

            # Calculate the average color difference
            total_color_difference = sum(color_differences)
            average_color_difference = total_color_difference / (2 * len(pixels_current))

            # Scale up the average color difference for better readability
            scaled_color_difference = average_color_difference * 100

            # Update rgb_change_count when the condition is met
            if scaled_color_difference >= self.rgb_threshold_percentage:
                self.rgb_change_count += 1
                print(f"RGB Change Count: {self.rgb_change_count}")

            print(f"RGB Percentage Change: {scaled_color_difference}")
            return scaled_color_difference, 0  # Return a tuple with two values
        return 0, 0  # Return a tuple with two values

    def pause_screen(self):
        self.minimize_all_windows()
        self.paused = True
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.geometry("{0}x{1}+0+0".format(self.root.winfo_screenwidth(), self.root.winfo_screenheight()))
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.luminance_change_count = 0
        self.rgb_change_count = 0
        time.sleep(3)

    def resume_screen(self):
        self.label.config(text="Strange light activity detected, click to disregard", bg="#333333")
        self.paused = False
        self.alert_shown = False
        self.root.attributes("-fullscreen", False)
        self.root.withdraw()
        print("Okay button clicked")
        self.luminance_change_count = 0
        self.rgb_change_count = 0

    def minimize_all_windows(self):
        try:
            import pyautogui
            pyautogui.hotkey('win', 'd')
        except ImportError:
            print("PyAutoGUI is not installed. Please install it with 'pip install pyautogui'.")

    def on_close(self):
        self.root.destroy()


if __name__ == "__main__":
    monitor = EpilepsyMonitor()