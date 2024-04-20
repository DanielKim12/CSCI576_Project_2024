from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import numpy as np
import cv2
from numpy.fft import fft
import librosa
from matplotlib import pyplot as plt
from glob import glob
import os
from tqdm import tqdm
import pickle
from packaging import version
from PIL import Image
import imagehash
from datetime import timedelta
import time
from scipy.spatial.distance import cosine
from tabulate import tabulate
import statistics

IMAGEHASH_AVG_WINDOW_T = 2 # 1 imagehash per 2 seconds
FIRST_K_IMAGEHASH_CANDIDATES = 3
MAX_MATCH_MFCC_WINDOW_LEN = 600

# Function to compute the average hash for a given list of frames
def compute_average_hash(frames):
    total_hashes = 0
    average_hash = None
    
    # Loop through each frame in the list
    for frame in frames:
        # Convert the frame to PIL Image format
        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # Compute the hash for the current frame
        frame_hash = imagehash.average_hash(frame_pil)
        
        # Add the hash to the total
        total_hashes += 1
        
        # Update the average hash
        if average_hash is None:
            average_hash = np.array(frame_hash.hash, dtype=np.float64)
        else:
            average_hash += np.array(frame_hash.hash, dtype=np.float64)
    
    # Compute the average hash
    average_hash /= total_hashes
    
    # Convert the average hash back to imagehash format
    average_hash = imagehash.ImageHash(average_hash.astype(bool))
    
    return average_hash

def get_average_hashes(video_path):
    # Open the video file
    video_capture = cv2.VideoCapture(video_path)

    # Get the frame rate of the video
    frame_rate = video_capture.get(cv2.CAP_PROP_FPS)

    # Calculate the number of frames for `AVG_WINDOW_T` seconds
    num_frames_per_chunk = int(frame_rate * IMAGEHASH_AVG_WINDOW_T)

    # List to store average hashes for each chunk
    average_hashes = []

    # List to temporarily store frames for each chunk
    frames_chunk = []

    # Loop through each frame in the video
    while True:
        # Read the next frame
        ret, frame = video_capture.read()
        
        # If there are no more frames, break out of the loop
        if not ret:
            break
        
        # Add the frame to the current chunk
        frames_chunk.append(frame)
        
        # Check if the chunk is complete
        if len(frames_chunk) == num_frames_per_chunk:
            # Compute the average hash for the current chunk of frames
            chunk_average_hash = compute_average_hash(frames_chunk)
            
            # Append the average hash to the list
            average_hashes.append(chunk_average_hash)
            
            # Clear the frames chunk list for the next chunk
            frames_chunk = []
    
    # return np.stack(average_hashes)
    return average_hashes

def compute_mfcc_features(path2vid):

    vfclip = VideoFileClip(path2vid)

    fps = vfclip.fps
    duration = vfclip.duration
    total_frames = int(duration * fps)
    sr = vfclip.audio.fps

    print(f'Total frame count = {total_frames}')
    print(f'Video frame rate (fps) = {fps}')
    print(f'Audio sample rate (sr) = {sr}')

    mfcc_features = []
    
    for i, frame in tqdm(enumerate(vfclip.iter_frames()), total=total_frames, desc="Analyzing audio..."):
        start_time = i / fps
        end_time = (i + 1) / fps
        audio_segment_stereo = vfclip.audio.subclip(start_time, end_time)
        audio_segment_stereo = audio_segment_stereo.to_soundarray(fps=sr)
        audio_segment_mono = np.mean(audio_segment_stereo, axis=1) # amp within [0., 1.]
        mfcc = librosa.feature.mfcc(y=audio_segment_mono, sr=sr, n_mfcc=13)  # default 13 MFCCs
        mfcc_mean = np.mean(mfcc, axis=1) # each frame gets 1 averaged mfcc vector

        # >>> plot the features
        # plt.figure(figsize=(10, 4))
        # librosa.display.specshow(mfcc, sr=sr, x_axis='time', cmap='coolwarm')
        # plt.colorbar(format='%+2.0f dB')
        # plt.title('MFCC')
        # plt.tight_layout()
        # plt.show()
        # <<< plot the features

        mfcc_features.append(mfcc_mean)

    vfclip.reader.close()
    vfclip.audio.reader.close_proc()
    
    # mfcc_features = np.stack(mfcc_features)
    return mfcc_features


def get_video_metadata(path2vid):
    vfclip = VideoFileClip(path2vid)
    fps = vfclip.fps
    duration = vfclip.duration
    total_frames = int(duration * fps)
    sr = vfclip.audio.fps
    vfclip.reader.close()
    vfclip.audio.reader.close_proc()
    metadata = {
        'name': os.path.basename(path2vid),
        'fps': fps,
        'duration': duration,
        'nframes': total_frames,
        'sr': sr,
    }
    return metadata

class VideoIndexManager:

    def __init__(self, vid_dir, idx_dir, skip_sync=True):
        """
        video_dir: directory where all video files are stored, forming a video database
        index_dir: directory where all index (fingerprint) files are stored
        """
        self.vid_dir = vid_dir
        self.idx_dir = idx_dir
        if not skip_sync:
            self.sync_metadata()
        print('Video index manager initialized.')

    def get_video_names(self):
        vid_paths = sorted(glob(os.path.join(self.vid_dir, '*.mp4')))
        vid_names = [os.path.basename(path) for path in vid_paths]
        return vid_names
    
    def get_indexed_video_names(self):
        idx_paths = sorted(glob(os.path.join(self.idx_dir, '*.pkl')))
        indexed_vid_names = [os.path.splitext(os.path.basename(path))[0] for path in idx_paths]
        return indexed_vid_names      
    
    def remove_wild_index_files(self):
        vid_names = self.get_video_names()
        idx_paths = sorted(glob(os.path.join(self.idx_dir, '*.pkl')))
        idx_names = [os.path.basename(path) for path in idx_paths]
        # remove extra index files
        rm_cnt = 0
        for idx_name in idx_names:
            if os.path.splitext(idx_name)[0] not in vid_names:
                os.remove(os.path.join(self.idx_dir, idx_name))
                rm_cnt += 1
        print(f'Removed {rm_cnt} wild index files.')

    def load_index_data(self, vid_name):
        """
        Return none if there is no index file for this video.
        """
        idx_path = os.path.join(self.idx_dir, vid_name+'.pkl')
        if not os.path.exists(idx_path):
            return None
        else:
            with open(idx_path, 'rb') as f:
                index_data = pickle.load(f)
            return index_data
        
    def save_index_data(self, vid_name, data_dict):
        idx_path = os.path.join(self.idx_dir, vid_name+'.pkl')
        if not os.path.exists(idx_path):
            return False
        else:
            with open(idx_path, 'wb') as f:
                pickle.dump(data_dict, f)
            return True

    def sync_metadata(self):
        """
        Synchronize index files' metadata to all existing videos.
        Run this every time a new video is added or an existing video is deleted.
        """
        self.remove_wild_index_files()
        vid_names = self.get_video_names()
        # sync existing videos' metadata
        for i, vid_name in enumerate(vid_names):
            index_data = self.load_index_data(vid_name)
            if index_data is None:
                index_data = {}
            metadata = get_video_metadata(os.path.join(self.vid_dir, vid_name))
            index_data.update(metadata)
            self.save_index_data(vid_name, index_data)
        print('Metadata in all index files have been synchronized.')


    def fingerprint_mfcc(self, rerun=False):
        """
        Create MFCC fingerprints for all videos whose metadata have been synchronized.
        By default, this will only create new fingerprints for videos that don't have the type of fingerprint.
        If algorithm is modified, set `rerun` to do a complete rerun for all videos.
        """
        indexed_vid_names = self.get_indexed_video_names()
        for vid_name in indexed_vid_names:
            index_data = self.load_index_data(vid_name)
            if 'mfcc' not in index_data or rerun:
                print(f'Computing MFCC for "{vid_name}"...')
                mfcc = compute_mfcc_features(os.path.join(self.vid_dir, vid_name))
                index_data['mfcc'] = mfcc
                self.save_index_data(vid_name, index_data)


    def fingerprint_imagehash(self, rerun=False):
        """
        Create image hash fingerprints for all videos.
        By default, this will only create new fingerprints for videos that don't have the type of fingerprint.
        If algorithm is modified, set `rerun` to do a complete rerun for all videos.
        """

        """
        # Example usage:
        video_path = "./Videos/video15.mp4"
        average_hashesDB = get_average_hashes(video_path)
        for i, hash_value in enumerate(average_hashesDB):
            start_time = timedelta(seconds=i * 2)
            end_time = timedelta(seconds=(i + 1) * 2)
            print(f"Average Hash for {start_time} to {end_time}: {hash_value}")

        """
        indexed_vid_names = self.get_indexed_video_names()
        for vid_name in indexed_vid_names:
            index_data = self.load_index_data(vid_name)
            if 'imagehash' not in index_data or rerun:
                print(f'Computing ImageHash for "{vid_name}"...')
                imagehash = get_average_hashes(os.path.join(self.vid_dir, vid_name))
                index_data['imagehash'] = imagehash
                self.save_index_data(vid_name, index_data)
            

    def fingerprint_all(self, rerun=False):
        """
        Create all necessary fingerprints for all videos.
        By default, this will only create new fingerprints for videos that don't have a certain type of fingerprint.
        If algorithm is modified, set `rerun` to do a complete rerun for all videos.
        """
        self.fingerprint_mfcc(rerun=rerun)
        self.fingerprint_imagehash(rerun=rerun)

    def query(self, path2vid):

        algo_start_time = time.time()
        vfclip_q = VideoFileClip(path2vid)

        indexed_vid_names = self.get_indexed_video_names()
        
        fps_q = vfclip_q.fps
        duration_q = vfclip_q.duration
        total_frames_q = int(duration_q * fps_q)
        sr_q = vfclip_q.audio.fps
        print('Query video stats:')
        print(f'Total frame count = {total_frames_q}')
        print(f'Video frame rate (fps) = {fps_q}')
        print(f'Audio sample rate (sr) = {sr_q}')

        query_average_hashs = get_average_hashes(path2vid)

        average_hashesDB = {}
        for vid_name in indexed_vid_names:
            index_data = self.load_index_data(vid_name)
            average_hashesDB[vid_name] = index_data['imagehash']
        diffDB = {}
        for vid_name in indexed_vid_names:
            allDiff = []
            for qa_hash in query_average_hashs:
                temp = []
                for original_hash in average_hashesDB[vid_name]:
                    temp.append(abs(original_hash - qa_hash))
                allDiff.append(min(temp))
            diffDB[vid_name] = (allDiff)

        meanArr = {}
        for vid_name in indexed_vid_names:
            meanArr[vid_name] = statistics.mean(diffDB[vid_name])

        sorted_meanArr = sorted(meanArr.items(), key=lambda item: item[1])
        imagehash_candidates = sorted_meanArr[:FIRST_K_IMAGEHASH_CANDIDATES]
        print('ImageHash candidates:')
        print(imagehash_candidates)
        candidate_vid_names = [vid_name for vid_name, _ in imagehash_candidates]

        # compute query video's audio mfcc features
        mfcc_q = compute_mfcc_features(path2vid)
        # convert to ndarray
        mfcc_q = np.stack(mfcc_q)
        len_q = len(mfcc_q)

        len_w = min(len_q, MAX_MATCH_MFCC_WINDOW_LEN) # the actual length of window where similarity is computed
        print(f'Matching window size set to {len_w}')
        mfcc_qw = mfcc_q[:len_w]
        mfcc_qwf = mfcc_qw.flatten()

        good_threshold = 0.99
        fair_threshold = 0.90

        candidates = []

        for vid_name in candidate_vid_names:
            fingerprint = self.load_index_data(vid_name)
            mfcc_p = np.stack(fingerprint['mfcc'])
            fps_p = fingerprint['fps']
            len_p = len(mfcc_p)
            for start in range(len_p - len_q + 1):
                # print(f'i={start}')
                # Compute average cosine similarity across the window
                # similarities = [1 - cosine(mfcc_q[i], mfcc_p[start+i]) for i in range(len_w)]
                # score = np.mean(similarities)
                cos_dist = cosine(mfcc_qwf, mfcc_p[start:start+len_w].flatten())
                score = 1 - cos_dist
                t_match = start / fps_p
                if score >= good_threshold:
                    print(f'Good match found at frame {start} (approx. t = {str(timedelta(seconds=t_match)).split(".")[0]})')
                if score >= fair_threshold:
                    candidates.append({
                        'score': score,
                        'name': vid_name,
                        'fp': os.path.join(self.vid_dir, vid_name),
                        't': t_match,
                        'frame_no': start,
                        })
        candidates.sort(reverse=True, key=lambda x: x['score'])
        print(tabulate([(candidate['score'], os.path.basename(candidate['name']), candidate['frame_no'], str(timedelta(seconds=candidate['t'])).split(".")[0]) for candidate in candidates[:20]], headers=['Score', 'Name', 'Frame No.', 'Time'], tablefmt='grid'))

        algo_end_time = time.time()
        print(f"Query finished, elapsed time = {algo_end_time - algo_start_time:.2f}s")
        return candidates[0]

def main():
    vindex = VideoIndexManager('./data/videos/', './data/fingerprints/')
    # vindex.fingerprint_mfcc(rerun=True)
    # vindex.fingerprint_imagehash(rerun=True)
    # vindex.fingerprint_all()
    vindex.query('./data/queries/video_2_1_filtered.mp4')
    
if __name__ == '__main__':
    main()