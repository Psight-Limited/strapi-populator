import asyncio
import os
import subprocess

import aiofiles
import cv2
from aiohttp import ClientSession

import strapi_models as M


def extract_first_frame(video_url):
    output_path = "./temp.jpg"
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i",
        video_url,
        "-ss",
        "00:00:00",
        "-frames:v",
        "1",
        output_path,
    ]
    subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path


async def main():
    all_videos = await M.PostCourseVideo.all()
    all_videos = [i for i in all_videos if not i.first_frame and i.video_file]
    for video in all_videos:
        print(video.id)
        frame_path = extract_first_frame(video.video_file.url)
        thumbnail = await M.Media.upload_file(frame_path)
        assert thumbnail is not None
        updates = {"first_frame": thumbnail}
        await M.PostCourseVideo(**{**video.__dict__, **updates}).put()
        os.remove(frame_path)


if __name__ == "__main__":
    asyncio.run(main())
