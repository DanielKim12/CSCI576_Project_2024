import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import cv2
import os

class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Player")

        # Initialize video capture
        self.cap = None
        self.paused = False

        # Create a label to display video frames
        self.video_label = tk.Label(root)
        self.video_label.pack()

        # Control buttons
        self.start_button = ttk.Button(root, text="▶ Start", command=self.start_video, style="ControlButton.TButton")
        self.start_button.pack(side=tk.LEFT)

        self.refresh_button = ttk.Button(root, text="⟳ Refresh", command=self.refresh_video, style="ControlButton.TButton")
        self.refresh_button.pack(side=tk.LEFT)

        self.pause_button = ttk.Button(root, text="❚❚ Pause", command=self.pause_video, style="ControlButton.TButton")
        self.pause_button.pack(side=tk.LEFT)

        # Create a custom style for buttons
        self.style = ttk.Style()
        self.style.configure("ControlButton.TButton", font=("Helvetica", 10), padding=5, width=10)

        # Store reference to PhotoImage
        self.photo = None

    def load_video(self, video_path, start_time=0):
        if not os.path.exists(video_path):
            messagebox.showerror("Error", "Video file not found.")
            return

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Failed to load video.")
            return

        # Set the frame position to the desired time point
        frame_pos = int(start_time * self.cap.get(cv2.CAP_PROP_FPS))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)

        self.display_frame()

    def display_frame(self):
        # Capture frame-by-frame
        ret, frame = self.cap.read()

        if ret:
            # Convert the image from BGR (CV2 default) to RGB
            cv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(cv_image)

            # Update the image of the label to display the frame
            self.photo = ImageTk.PhotoImage(image=pil_image)
            self.video_label.configure(image=self.photo)
            self.video_label.image = self.photo

            if not self.paused:
                self.video_label.after(30, self.display_frame)  # Adjust timing based on video fps
        else:
            self.refresh_video()

    def start_video(self):
        if self.paused:
            self.paused = False
            self.display_frame()

    def refresh_video(self):
        if self.cap is not None:
            self.cap.release()
            start_time = self.calculate_start_time()
            video_path = self.decide_video_to_play()
            self.load_video(video_path,start_time=start_time)

    def pause_video(self):
        self.paused = True
        
    def decide_video_to_play(self):
        # Implement the logic to decide which video to play dynamically
        # For demonstration purposes, returning a hardcoded video path
        return './data/Videos/video10.mp4'
        
    def calculate_start_time(self):
        #where the sliding window algo takes place and calculate 
        return 30

def main():
    root = tk.Tk()
    player = VideoPlayer(root)
    video_path = player.decide_video_to_play()
    start_time = player.calculate_start_time()
    player.load_video(video_path, start_time=start_time)   
    root.mainloop()

if __name__ == "__main__":
    main()

