# CSCI576_Project_2024

Team members: Dingyi Nie, Daniel Kim, Younwoo Roh, Timothy Lin

## Searching and Indexing Video with Input Clip
This repository hosts our final project for CSCI 576: Multimedia Design. The project is designed to take an input video clip along with its audio and identify which video from a database it originates from. Additionally, the program will determine the exact starting point of the clip within the original video.

## Setup
In the root directory of this repository, run the following:

```bash
python3 -m venv env
source env/bin/activate
python3 -m pip install -r requirements.txt
```

## Usage
main.py : Main file used to run program. Prompts user for input query video filepath via terminal.<br />
<br />
Queries/ : Contains input query videos.<br />
Videos/ : Contains database of videos we are searching through.<br />
VideoStats/ : Contains CSVs about each video with information about framestats and scenes. Also contains code used to calculate these CSVs.<br />
QueryVideo.py : Helper class to contain information about and calculate each query.<br />
UI.py: Helper class to display results of query (original video at correct timestamp)<br />
