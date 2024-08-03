import asyncio
import os
import subprocess

import strapi_models as M


def extract_audio(video_url):
    output_path = "./temp.mp3"
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i",
        video_url,
        output_path,
    ]
    subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path


async def main():
    all_videos = await M.PostCourseVideo.all()
    print(f"got {len(all_videos)} videos")
    all_videos = [i for i in all_videos if not i.audio_file and i.video_file]
    print(f"{len(all_videos)} videos are missing audio")
    for video in all_videos:
        print(video.id)
        audio_path = extract_audio(video.video_file.url)
        video.audio_file = await M.Media.upload_file(audio_path)
        await video.put()
        os.remove(audio_path)


if __name__ == "__main__":
    asyncio.run(main())
