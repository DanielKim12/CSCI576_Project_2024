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
import h5py
from packaging import version
from PIL import Image
import imagehash
from datetime import timedelta

VERSION = '1.0'

class VideoIndexManager:

    def __init__(self, video_dir):
        """
        video_dir: directory where all video files are stored, forming a video database
        """
        self.video_dir = video_dir
        self.db_path = os.path.join(self.video_dir, 'db.h5')
        print(f'Initializing DB version {VERSION} under "{self.video_dir}"...')
        with h5py.File(self.db_path, 'a') as f:
            if 'version' in f.attrs:
                old_version = f.attrs['version']
                if version.parse(old_version) == version.parse(VERSION):
                    print(f'Found existing DB.')
                    return # version is matched, do nothing
            # no database or version is no match, re-build the whole database
            print('New DB file created.')
            for key in f.keys():
                del f[key] # clean everything existing
            # re-sync metadata
            self.sync_metadata()
            f.attrs['version'] = VERSION


    def sync_metadata(self):
        """
        Sync DB groups and metadata to all existing videos under `self.vdir`.
        Run this every time a new video is added into DB, or an existing video is deleted.
        """
        video_paths = sorted(glob(os.path.join(self.video_dir, '*.mp4')))
        video_names = [os.path.basename(path) for path in video_paths]
        print(f"Start synchronizing {len(video_names)} videos' metadata...")
        with h5py.File(self.db_path, mode='a') as f:
            # remove any group that's no longer in video_dir
            for video_name in f.keys():
                if video_name not in video_names:
                    del f[video_name]
            # sync existing videos' metadata
            for i, video_name in enumerate(video_names):
                vfclip = VideoFileClip(os.path.join(self.video_dir, video_name))
                fps = vfclip.fps
                duration = vfclip.duration
                total_frames = int(duration * fps)
                sr = vfclip.audio.fps
                vfclip.reader.close()
                vfclip.audio.reader.close_proc()
                fingerprint = {
                    'fps': fps,
                    'duration': duration,
                    'nframes': total_frames,
                    'sr': sr,
                }
                if video_name not in f:
                    f.create_group(video_name)
                for k, v in fingerprint.items():
                    if k in f[video_name]:
                        del f[video_name][k]
                    f[video_name].create_dataset(k, data=v)
        print(f"{len(video_names)} videos' metadata synchronized.")


    def fingerprint_mfcc(self, rerun=False):
        """
        Create MFCC fingerprints for all videos.
        By default, this will only create new fingerprints for videos that don't have the type of fingerprint.
        If algorithm is modified, set `rerun` to do a complete rerun for all videos.
        """
        with h5py.File(self.db_path, mode='a') as f:
            if rerun:
                video_names = f.keys()
            else:
                video_names = [n for n in f.keys() if 'mfcc' not in f[n]]
            for i, video_name in enumerate(video_names):
                print(f"Fingerprinting MFCC for video {i+1}/{len(video_names)}: {video_name}")

                vfclip = VideoFileClip(os.path.join(self.video_dir, video_name))
            
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
                
                mfcc_features = np.stack(mfcc_features)
                
                if 'mfcc' in f[video_name]:
                    del f[video_name]['mfcc']
                f[video_name].create_dataset('mfcc', data=mfcc_features)
                
                print(f"MFCC fingerprint of shape {mfcc_features.shape} has been generated.")

    def fingerprint_imagehash(self, rerun=False):
        """
        Create image hash fingerprints for all videos.
        By default, this will only create new fingerprints for videos that don't have the type of fingerprint.
        If algorithm is modified, set `rerun` to do a complete rerun for all videos.
        """
        AVG_WINDOW_T = 2

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
            num_frames_per_chunk = int(frame_rate * AVG_WINDOW_T)

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
            
            return np.stack(average_hashes)

        def get_lowest_five_indices(array):
            # Use argsort to get the indices that would sort the array
            sorted_indices = np.argsort(array)
            
            # Return the first five indices, which correspond to the lowest values
            return sorted_indices[:5]


        """
        # Example usage:
        video_path = "./Videos/video15.mp4"
        average_hashesDB = get_average_hashes(video_path)
        for i, hash_value in enumerate(average_hashesDB):
            start_time = timedelta(seconds=i * 2)
            end_time = timedelta(seconds=(i + 1) * 2)
            print(f"Average Hash for {start_time} to {end_time}: {hash_value}")

        """

        with h5py.File(self.db_path, mode='a') as f:
            if rerun:
                video_names = f.keys()
            else:
                video_names = [n for n in f.keys() if 'imagehash' not in f[n]]
            for i, video_name in enumerate(video_names):
                video_path = os.path.join(self.video_dir, video_name)
                temp_average_hashes = get_average_hashes(video_path)
                print(f"Imagehash fingerprint of shape {temp_average_hashes.shape} has been generated.")
            

    def fingerprint_all(self):
        """
        Create all necessary fingerprints for all videos.
        By default, this will only create new fingerprints for videos that don't have a certain type of fingerprint.
        If algorithm is modified, set `rerun` to do a complete rerun for all videos.
        """
        self.fingerprint_mfcc()
        self.fingerprint_imagehash()

def main():
    vindex = VideoIndexManager('./data/videos')
    # vindex.fingerprint_mfcc(rerun=True)
    vindex.fingerprint_imagehash(rerun=True)
    vindex.fingerprint_all()
    
if __name__ == '__main__':
    main()