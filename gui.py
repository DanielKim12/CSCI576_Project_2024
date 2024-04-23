import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import cv2
import os

class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Player")
        self.video_path = ''
        self.start_time = 0
        self.cap = None
        self.paused = False
        self.after_id = None

        # Create a label to display video frames
        self.video_label = tk.Label(root)
        self.video_label.pack()

        # Control buttons
        self.start_button = ttk.Button(root, text="▶ Start", command=self.start_video, style="ControlButton.TButton")
        self.start_button.pack(side=tk.LEFT)

        self.refresh_button = ttk.Button(root, text="⟳ Refresh", command=lambda: self.load_video(self.video_path, self.start_time), style="ControlButton.TButton")
        self.refresh_button.pack(side=tk.LEFT)

        self.pause_button = ttk.Button(root, text="❚❚ Pause", command=self.pause_video, style="ControlButton.TButton")
        self.pause_button.pack(side=tk.LEFT)

        # Create a custom style for buttons
        self.style = ttk.Style()
        self.style.configure("ControlButton.TButton", font=("Helvetica", 10), padding=5, width=10)

        # Store reference to PhotoImage
        self.photo = None

    def load_video(self, video_path, start_time=0):
        self.video_path = video_path
        self.start_time = start_time

        if not os.path.exists(self.video_path):
            messagebox.showerror("Error", "Video file not found.")
            return
        
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Failed to load video.")
            return

        # Set the frame position
        frame_pos = int(self.start_time * self.cap.get(cv2.CAP_PROP_FPS))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)

        self.start_video()

    def display_frame(self):
        if self.paused:
            return
        
        ret, frame = self.cap.read()
        if ret:
            cv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(cv_image)
            self.photo = ImageTk.PhotoImage(image=pil_image)
            self.video_label.configure(image=self.photo)
            # self.video_label.image = self.photo
            if self.after_id is not None:
                self.root.after_cancel(self.after_id)
            self.after_id = self.video_label.after(int(1000 / self.cap.get(cv2.CAP_PROP_FPS)), self.display_frame)
        else:
            self.refresh_video()

    def start_video(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.paused = False
        self.display_frame()

    def refresh_video(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.load_video(self.video_path, self.start_time)

    def pause_video(self):
        self.paused = True
