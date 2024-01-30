import os

import requests
import vimeo
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
client = vimeo.VimeoClient(
    token=os.getenv("VIMEO_ACCESS_TOKEN"),
    key=os.getenv("VIMEO_CLIENT_ID"),
    secret=os.getenv("VIMEO_CLIENT_SECRET"),
)


def get_video_download_link(video_id):
    uri = f"https://api.vimeo.com/videos/{video_id}"
    response = client.get(uri)
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code} from Vimeo API.")
        return None
    data = response.json()
    best_file = max(
        data.get("download", []), key=lambda x: int(x.get("height", 0)), default=None
    )
    if best_file is None:
        print("Error: No suitable video link found.")
        return None
    return best_file.get("link")


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
    video_url = get_video_download_link(video_id)
    if video_url is None:
        return None
    print(f"Downloading video from {video_url} to {download_path}")
    os.makedirs(os.path.dirname(download_path), exist_ok=True)
    if download_from_url(video_url, download_path):
        return download_path
    else:
        return None


if __name__ == "__main__":
    video_id = "862577733"
    download_path = "./downloaded_video.mp4"
    downloaded_path = download_video(video_id, download_path)
    if downloaded_path:
        print(f"Video downloaded successfully to {downloaded_path}")
    else:
        print("Video download failed.")
