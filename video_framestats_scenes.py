from scenedetect import detect, ContentDetector

def find_scenes(video_path, metrics_outpath, scenes_outpath):
    """
    Analyzes delta frame information and scenes for input videopath
    """
    scenes_list = detect(video_path, ContentDetector(), stats_file_path=metrics_outpath, show_progress=True)

    scenes_file = open(scenes_outpath, "w")
    scenes_file.write("Scene #, Start Time, Start Frame, End Time, End Frame\n")
    for i, scene in enumerate(scenes_list):
        scene_num = str(i+1)
        start_time = str(scene[0].get_timecode())
        start_frame = str(scene[0].get_frames())
        end_time = str(scene[1].get_timecode())
        end_frame = str(scene[1].get_frames())
        scenes_file.write(scene_num + "," + start_time + "," + start_frame + "," + end_time + "," + end_frame + "\n")
    
def main():
    """
    Processes framestats and scene info for all 20 input videos under /Videos
    """
    for i in range(1, 21):
        video_path = "Videos/video" + str(i) + ".mp4"
        metrics_path = "VideoStats/FrameStats/video" + str(i) + "_framestats.csv"
        scenes_path = "VideoStats/SceneInfo/video" + str(i) + "_scenesinfo.csv"
        print("Processing video" + str(i) + ".mp4")
        find_scenes(video_path=video_path, metrics_outpath=metrics_path, scenes_outpath=scenes_path)

if __name__ == '__main__':
    main()