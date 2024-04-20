import os
import time
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import numpy as np
import cv2
from numpy.fft import fft
import librosa
from matplotlib import pyplot as plt
from glob import glob
from tqdm import tqdm
import pickle
from scipy.spatial.distance import cosine
from datetime import timedelta
from tabulate import tabulate

MAX_MATCH_WINDOW_LEN = 600

def main():

    algo_start_time = time.time()

    # query_video = './dataset/Queries/video_6_1_filtered.mp4'
    query_video = './dataset/Queries/video16_filtered_2.mp4'
    vfclip_q = VideoFileClip(query_video)
    
    fps_q = vfclip_q.fps
    duration_q = vfclip_q.duration
    total_frames_q = int(duration_q * fps_q)
    sr_q = vfclip_q.audio.fps

    print(f'Total frame count = {total_frames_q}')
    print(f'Video frame rate (fps) = {fps_q}')
    print(f'Audio sample rate (sr) = {sr_q}')

    mfcc_q = []
    
    for i, frame in tqdm(enumerate(vfclip_q.iter_frames()), total=total_frames_q, desc="Framing..."):
        start_time = i / fps_q
        end_time = (i + 1) / fps_q
        audio_segment_stereo = vfclip_q.audio.subclip(start_time, end_time)
        audio_segment_stereo = audio_segment_stereo.to_soundarray(fps=sr_q)
        audio_segment_mono = np.mean(audio_segment_stereo, axis=1) # amp within [0., 1.]
        mfcc = librosa.feature.mfcc(y=audio_segment_mono, sr=sr_q, n_mfcc=13)  # default 13 MFCCs
        mfcc_mean = np.mean(mfcc, axis=1) # each frame gets 1 averaged mfcc vector
        mfcc_q.append(mfcc_mean)
    
    # convert to ndarray
    mfcc_q = np.stack(mfcc_q)
    len_q = len(mfcc_q)

    len_w = min(len_q, MAX_MATCH_WINDOW_LEN) # the actual length of window where similarity is computed
    print(f'Matching window size set to {len_w}')
    mfcc_qw = mfcc_q[:len_w]
    mfcc_qwf = mfcc_qw.flatten()

    good_threshold = 0.98
    fair_threshold = 0.90

    candidates = []

    fingerprint_dir = './dataset/Fingerprints/'
    fingerprint_list = glob(os.path.join(fingerprint_dir, '*.pkl'))
    for fingerprint_file in fingerprint_list:
        print(f'Searching in {fingerprint_file}')
        with open(fingerprint_file, 'rb') as f:
            fingerprint = pickle.load(f)
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
                    'file': fingerprint_file,
                    't': t_match,
                    'frame_no': start,
                    })
    candidates.sort(reverse=True, key=lambda x: x['score'])
    print(tabulate([(candidate['score'], os.path.basename(candidate['file']), candidate['frame_no'], str(timedelta(seconds=candidate['t'])).split(".")[0]) for candidate in candidates[:20]], headers=['Score', 'File', 'Frame No.', 'Time'], tablefmt='grid'))

    algo_end_time = time.time()
    print(f"Query finished, elapsed time = {algo_end_time - algo_start_time:.2f}s")


if __name__ == '__main__':
    main()