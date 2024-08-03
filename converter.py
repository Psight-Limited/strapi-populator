import asyncio
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import List

import aiofiles
import aiohttp
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

timeout = aiohttp.ClientTimeout(
    total=0,
    connect=0,
    sock_connect=0,
    sock_read=0
)

def get_video_info(video_path: str, retries=10, delay=5) -> VideoInfo:
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
            video_path,
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


async def download_video(url: str, output_path: str):
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
        async with session.get(url, timeout=timeout) as response:
            response.raise_for_status()
            pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading")
            async with aiofiles.open(output_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024):
                    await f.write(chunk)
                    pbar.update(len(chunk))
            pbar.close()


def convert_mov_to_mp4(input_path: str, output_path: str = "./temp.mp4"):
    video_info = get_video_info(input_path)
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
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
            if time_str != 'N/A':
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
    print(f"got {len(all_videos)} videos")
    all_videos = [
        i
        for i in all_videos
        if i.video_file and i.video_file.url.lower().endswith(".mov")
    ]
    print(f"{len(all_videos)} videos are .mov")
    for video in all_videos:
        video_path = f"./temp_{video.id}.mov"
        await download_video(video.video_file.url, video_path)
        video_info = get_video_info(video_path)
        video_needs_conversion = any(
            stream.codec_name != "h264"
            for stream in video_info.streams
            if stream.codec_type == "video"
        )
        if video_needs_conversion:
            print(f"Converting video {video.id}")
            converted_video_path = convert_mov_to_mp4(video_path)
            print("Video converted")
            file = await M.Media.upload_file(converted_video_path)
            assert file is not None
            video.video_file = file
            print("Video uploaded")
            await video.put()
            os.remove(converted_video_path)
        else:
            print(f"Skipping conversion for video {video.id}, already h264.")
        os.remove(video_path)


if __name__ == "__main__":
    asyncio.run(main())
