import asyncio

import strapi_models as M
from assembly_ai import transcribe


async def fetch_videos():
    videos = await M.PostCourseVideo.all()
    for video in videos:
        if video.id != 71:
            continue
        print(video.id)
        video_url = video.video_file.url
        print(video_url)
        print(video.transcript)
        if video.transcript is not None and video.transcript.strip() != "":
            return
        transcript = transcribe(video_url)
        updates = {"transcript": transcript}
        print(transcript)
        await M.PostCourseVideo(**{**video.__dict__, **updates}).put()
        return


if __name__ == "__main__":
    asyncio.run(fetch_videos())
