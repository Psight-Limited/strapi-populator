import asyncio
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import List

from tqdm import tqdm

import strapi_models as M


@dataclass
class StreamInfo:
    codec_name: str
    codec_type: str


@dataclass
class VideoInfo:
    duration: float
    streams: List[StreamInfo] = field(default_factory=list)


def get_video_info(video_url: str, retries=10, delay=5) -> VideoInfo:
    """Get detailed information and duration of the video with retry logic."""
    for attempt in range(retries):
        probe_command = [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_entries",
            "format=duration:stream=codec_name,codec_type",
            video_url,
        ]
        result = subprocess.run(
            probe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = float(data["format"]["duration"])
            streams = [
                StreamInfo(stream["codec_name"], stream["codec_type"])
                for stream in data["streams"]
            ]
            return VideoInfo(duration, streams)
        else:
            print(f"Attempt {attempt + 1} failed: {result.stderr}")
            time.sleep(delay)  # Wait before retrying

    raise Exception(f"ffprobe error after {retries} attempts: {result.stderr}")


def convert_mov_to_mp4(video_url: str, output_path: str = "./temp.mp4"):
    video_info = get_video_info(video_url)
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i",
        video_url,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-c:a",
        "copy",
        output_path,
    ]
    process = subprocess.Popen(
        ffmpeg_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
    )
    pbar = tqdm(total=video_info.duration, desc="Converting")
    for line in process.stdout:
        if "time=" in line:
            time_str = line.split("time=")[1].split(" ")[0]
            hours, minutes, seconds = map(float, time_str.split(":"))
            current_time = hours * 3600 + minutes * 60 + seconds
            pbar.n = current_time
            pbar.refresh()
    pbar.close()
    if process.poll() != 0:
        raise RuntimeError("FFmpeg did not exit cleanly")
    return output_path


async def main():
    all_videos = await M.PostCourseVideo.all()
    all_videos = [
        i
        for i in all_videos
        if i.video_file and i.video_file.url.lower().endswith(".mov")
    ]
    for video in all_videos:
        video_info = get_video_info(video.video_file.url)
        video_needs_conversion = any(
            stream.codec_name != "h264"
            for stream in video_info.streams
            if stream.codec_type == "video"
        )
        if video_needs_conversion:
            print(f"Converting video {video.id}")
            video_path = convert_mov_to_mp4(video.video_file.url)
            print("Video converted")
            file = await M.Media.upload_file(video_path)
            assert file is not None
            print("Video uploaded")
            updates = {"video_file": file}
            await M.PostCourseVideo(**{**video.__dict__, **updates}).put()
            os.remove(video_path)
        else:
            print(f"Skipping conversion for video {video.id}, already h264.")


if __name__ == "__main__":
    asyncio.run(main())
