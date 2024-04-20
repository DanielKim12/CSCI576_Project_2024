from vindex import VideoIndexManager
from gui import VideoPlayer
import tkinter as tk
def main():
    """
    Takes in input video path to query and outputs result of query
    """
    vindex = VideoIndexManager('./data/videos/', './data/fingerprints/')
    while True:
        input_filepath = input("Please enter the relative filepath of the input video:\n")
        root = tk.Tk()
        vplayer = VideoPlayer(root)
        result = vindex.query(input_filepath)
        vplayer.load_video(result['fp'], start_time=result['t'])   
        root.mainloop()
        

if __name__ == '__main__':
    main()