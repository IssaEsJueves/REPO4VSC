import customtkinter as ctk
import threading
import time
import numpy as np
from PIL import ImageGrab, ImageOps
from PIL import Image
from skimage.color import rgb2lab


class Configuration:
    # Rescaled resolution of the image
    resized_width = 200
    resized_height = 100

    # Rate at which it takes and analyzes a screenshot
    rate = 0.001

    # How long without a flag does it reset the counters
    timeout_var = 0.25

    # The threshold percentage; the lower the percentage, the higher the risk for false flags
    rgb_threshold_percentage = 1000
    luminance_threshold_percentage = 70

    # How many consecutive flagged frames before the GUI is full-screened
    lum_consecutive_frames = 3
    rgb_consecutive_frames = 3


class EpilepsyMonitor:
    # creating the GUI
    def __init__(self):
        self.paused = False
        self.root = ctk.CTk()
        self.root.title("Epilepsy Monitor")
        # self.root.configure(background=ctk.ThemeManager.theme["Blue"]["frame_low"])
        self.root.resizable(False, False)

        font = ("Impact", 20)  # "bold")

        self.label = ctk.CTkLabel(
            self.root,
            text="Strange light activity detected,\nclick to disregard",
            font=font,  # Using text_font instead of font for customtkinter
            # fg_color=ctk.ThemeManager.theme["Blue"]["frame_high"],  # Text color
            #  bg_color=ctk.ThemeManager.theme["Blue"]["frame_low"],  # Background color
            width=380,  # Adjust the width to fit the window
            height=60,  # Adjust the height for better visual
            corner_radius=10  # Rounded corners for a modern look
        )
        self.label.pack(pady=20)  # Add some vertical padding for spacing
        self.ok_button = ctk.CTkButton(
            self.root,
            text="Disregard",
            font=font,  # Using text_font instead of font for customtkinter
            # fg_color=ctk.ThemeManager.theme["Blue"]["button"],  # Text color
            # bg_color=ctk.ThemeManager.theme["Blue"]["button"],  # Background color
            # hover_color=ctk.ThemeManager.theme["Blue"]["button_hover"],  # Hover color
            width=180,  # Width of the button
            height=50,  # Height of the button
            corner_radius=10,  # Rounded corners for the button
            command=self.resume_screen
        )
        self.ok_button.pack(pady=20)  # Add some vertical padding for spacing

        # local call to variables
        self.last_luminance = None
        self.last_rgb_frame = None
        self.luminance_change_count = 0
        self.rgb_change_count = 0
        self.rgb_threshold_percentage = Configuration.rgb_threshold_percentage
        self.luminance_threshold_percentage = Configuration.luminance_threshold_percentage
        self.lum_consecutive_frames = Configuration.lum_consecutive_frames
        self.rgb_consecutive_frames = Configuration.rgb_consecutive_frames
        self.timeout_start = time.time()
        self.timeout_duration = Configuration.timeout_var

        self.alert_shown = False

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.start_monitor_thread()
        self.root.mainloop()

    def start_monitor_thread(self):
        self.monitor_thread = threading.Thread(target=self.monitor_screen)
        self.root.withdraw()
        self.monitor_thread.start()

    def monitor_screen(self):
        last_change_time = time.time()  # Initialize last_change_time
        while True:
            if not self.paused:
                screenshot = ImageGrab.grab(bbox=(0, 0, 1920, 1080))
                screenshot = screenshot.resize((Configuration.resized_width, Configuration.resized_height),
                                               Image.LANCZOS)
                current_luminance, luminance_percentage_change = self.calculate_luminance(screenshot)
                rgb_percentage_change, _ = self.calculate_rgb_change(screenshot)
                self.last_luminance = current_luminance
                self.last_rgb_frame = screenshot

                # Check if the change counts exceed the consecutive frames threshold
                if (
                        self.rgb_change_count >= self.rgb_consecutive_frames

                ):
                    self.label.configure(text="Strange light activity detected, click to disregard - RGB")
                    self.pause_screen()
                    # Reset the change counts
                    self.luminance_change_count = 0
                    self.rgb_change_count = 0

                if (
                        self.luminance_change_count >= self.lum_consecutive_frames
                ):
                    self.label.configure(text="Strange light activity detected, click to disregard - LUM")
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

                time.sleep(Configuration.rate)

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
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f'{700}x{200}+{620}+{300}')
        self.root.deiconify()
        self.root.focus_force()
        self.resume_event = threading.Event()
        self.resume_event.wait()

    def resume_screen(self):
        self.label.configure(text="Strange light activity detected, click to disregard")
        self.paused = False
        self.alert_shown = False
        self.root.attributes("-fullscreen", False)
        self.root.withdraw()
        print("Okay button clicked")
        self.luminance_change_count = 0
        self.rgb_change_count = 0
        self.resume_event.set()

    @staticmethod
    def minimize_all_windows():
        try:
            import pyautogui
            pyautogui.hotkey('win', 'd')
        except ImportError:
            print("PyAutoGUI is not installed. Please install it with 'pip install pyautogui'.")

    def on_close(self):
        self.root.destroy()


if __name__ == "__main__":
    monitor = EpilepsyMonitor()
