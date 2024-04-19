from scenedetect import detect, ContentDetector

class QueryVideo:
    """
    Class to hold information about an input query video and perform the query.
    """
    def __init__(self, videopath):
        self.query_videopath = videopath
        self.stats_outpath = "query_framestats.csv"
        self.scenes_outpath = "query_scenes.csv"

        self.original_video = ""
        self.video_timestamp = ""
        self.video_frame_number = -1


    def query_and_display(self):
        """
        Function to query video and find original video + timestamp. Displays result in outputted UI.
        """
        # Analyze framestats and scenes of input query video 
        self.__analyze_framestats_scenes()
        pass
    

    def __analyze_framestats_scenes(self):
        """
        Analyzes frame stats and scenes of input query video and stores in "query_framestats.csv" and "query_scenes.csv" repsectively
        """
        scenes_list = detect(self.query_videopath, ContentDetector(), self.stats_outpath, show_progress=True)
        scenes_file = open(self.scenes_outpath, "w")
        scenes_file.write("Scene #, Start Time, Start Frame, End Time, End Frame\n")
        for i, scene in enumerate(scenes_list):
            scene_num = str(i+1)
            start_time = str(scene[0].get_timecode())
            start_frame = str(scene[0].get_frames())
            end_time = str(scene[1].get_timecode())
            end_frame = str(scene[1].get_frames())
            scenes_file.write(scene_num + "," + start_time + "," + start_frame + "," + end_time + "," + end_frame + "\n")

    def __find_original_video_and_frame(self):
        """
        Function using input framestats and scenes to query precomputed data of videos in database to find the right original video. 
        """
        pass
