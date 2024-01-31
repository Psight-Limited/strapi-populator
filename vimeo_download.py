import os

import requests
import vimeo
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip
from tqdm import tqdm

load_dotenv()

client = vimeo.VimeoClient(
    token=os.getenv("VIMEO_ACCESS_TOKEN"),
    key=os.getenv("VIMEO_CLIENT_ID"),
    secret=os.getenv("VIMEO_CLIENT_SECRET"),
)


def get_video_info(video_id):
    uri = f"https://api.vimeo.com/videos/{video_id}"
    response = client.get(uri)
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code} from Vimeo API.")
        return None, None
    data = response.json()
    best_file = max(
        data.get("download", []), key=lambda x: int(x.get("height", 0)), default=None
    )
    thumbnail_url = data.get("pictures", {}).get("sizes", [{}])[-1].get("link", None)
    if best_file is None:
        print("Error: No suitable video link found.")
        return None, None
    return best_file.get("link"), thumbnail_url


def download_from_url(url, download_path):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size, unit="iB", unit_scale=True)
    with open(download_path, "wb") as file:
        for chunk in response.iter_content(block_size):
            progress_bar.update(len(chunk))
            file.write(chunk)
    progress_bar.close()
    if total_size != 0 and progress_bar.n != total_size:
        print("Error: Downloaded file size does not match expected size.")
        return False
    return True


def download_video(video_id, download_path):
    video_url, thumbnail_url = get_video_info(video_id)
    if video_url is None:
        return None
    os.makedirs(os.path.dirname(download_path), exist_ok=True)
    print(f"Downloading video from {video_url} to {download_path}")
    if download_from_url(video_url, download_path):
        print(f"Video downloaded successfully to {download_path}")
        if thumbnail_url:
            thumbnail_path = os.path.splitext(download_path)[0] + ".jpg"
            print(f"Downloading thumbnail from {thumbnail_url} to {thumbnail_path}")
            if download_from_url(thumbnail_url, thumbnail_path):
                print(f"Thumbnail downloaded successfully to {thumbnail_path}")
        # Extract MP3
        audio_path = os.path.splitext(download_path)[0] + ".mp3"
        print(f"Extracting audio to {audio_path}")
        try:
            clip = VideoFileClip(download_path)
            clip.audio.write_audiofile(audio_path, fps=44100)
            print(f"Audio extracted successfully to {audio_path}")
        except Exception as e:
            print(f"Error extracting audio: {e}")
    else:
        print("Video download failed.")
