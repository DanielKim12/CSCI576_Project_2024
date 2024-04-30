from flask import Flask, send_from_directory, request, abort, render_template
import webbrowser
import os
from threading import Thread

app = Flask(__name__)

@app.route('/')
def index():
    video_path = request.args.get('video', 'default_video.mp4')
    start_time = request.args.get('start', 0)
    frame_num = request.args.get('frame', 0)
    return render_template('video_player.html', video_path=video_path, start_time=start_time, frame_num=frame_num)

@app.route('/video/<path:filename>')
def video(filename):
    if not filename.startswith('/'):
        filename = '/' + filename 
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        abort(404)
    directory = os.path.dirname(filename)
    file_name = os.path.basename(filename)
    return send_from_directory(directory, file_name, as_attachment=True, mimetype='video/mp4')

def run_server():
    app.run(port=5000, debug=True, use_reloader=False)

def query_and_open_browser():
    from vindex import VideoIndexManager 
    
    vindex = VideoIndexManager('./data/videos/', './data/fingerprints/')
    while True:
        input_filepath = input("Please enter the relative filepath of the input video:\n").strip("'")
        result = vindex.query(input_filepath)
        print(result)

        video = result['fp']
        time = result['t']
        frame = result['frame_no']

        try:
            url = f"http://127.0.0.1:5000/?video={os.path.abspath(video)}&start={time}&frame={frame}"
            webbrowser.open_new_tab(url)
        except Exception as e:
            print("An error occurred:", e)

if __name__ == '__main__':
    # Run the Flask server in a separate thread
    Thread(target=run_server).start()
    
    # Run the video query and browser opening in the main thread
    query_and_open_browser()