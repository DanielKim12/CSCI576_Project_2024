from scenedetect import detect, ContentDetector
import csv
import os 
import tempfile

def find_scenes(video_path, metrics_outpath, scenes_outpath):
    """
    Analyzes delta frame information and scenes for input videopath.
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

def add_column_to_csv(filepath, column_name, column_vals):
    """
    Adds column to a CSV file.
    """
    original_csv = open(filepath)

    temp_file, temp_file_path = tempfile.mkstemp()
    try:
        with open(original_csv, "r", newline="") as csvfile, os.fdopen(temp_file, "w", newline="") as newfile:
            reader = csv.reader(csvfile)
            writer = csv.writer(newfile)

            headers = next(reader)
            headers.append(column_name)
            writer.writerow(headers)
            
            # Checking added column has exact number of values as existing CSV
            if len(reader) != len(column_vals):
                raise Exception("Added column does not have enough values")
            for i in range(len(reader)):
                row = reader[i]
                val = column_vals[i]
                row.append(val)
                writer.writerow(row)
    
        os.replace(temp_file_path, original_csv)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    
def main():
    """
    Processes framestats and scene info for all 20 input videos under /Videos
    """
    for i in range(1, 21):
        video_path = "../Videos/video" + str(i) + ".mp4"
        metrics_path = "FrameStats/video" + str(i) + "_framestats.csv"
        scenes_path = "SceneInfo/video" + str(i) + "_scenesinfo.csv"
        print("Processing video" + str(i) + ".mp4")
        find_scenes(video_path=video_path, metrics_outpath=metrics_path, scenes_outpath=scenes_path)
        # Add additional columns if necessary

if __name__ == '__main__':
    main()