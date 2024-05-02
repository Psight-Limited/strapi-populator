import asyncio
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import strapi_models as M

lock = asyncio.Semaphore(50)


def extract_first_frame(video_url, video_id):
    output_path = f"./thumbnails/temp-{video_id}.jpg"
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-ss",
        "00:00:50",
        "-i",
        video_url,
        "-frames:v",
        "1",
        output_path,
    ]
    subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path


async def process_video(video, executor):
    loop = asyncio.get_running_loop()
    print(video.id)
    frame_path = await loop.run_in_executor(
        executor, extract_first_frame, video.video_file.url, video.id
    )

    thumbnail = await M.Media.upload_file(frame_path)
    updates = {"first_frame": thumbnail}
    print("UPDATE", video.id)
    await M.PostCourseVideo(**{**video.__dict__, **updates}).put()
    os.remove(frame_path)
    print(f"Processed video {video.id}")


async def main():
    print("Start processing videos")
    all_videos = await M.PostCourseVideo.all()
    all_videos = [
        i for i in all_videos if i.first_frame and i.first_frame.name == "temp.jpg"
    ]
    print("ALL VIDEOS DONE")

    with ThreadPoolExecutor() as executor:
        tasks = [process_video(video, executor) for video in all_videos]
        print("TASKS")
        await asyncio.gather(*tasks)

    print("Finished processing all videos")


if __name__ == "__main__":
    asyncio.run(main())
