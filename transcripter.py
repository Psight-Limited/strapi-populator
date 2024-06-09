import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import strapi_models as M
from assembly_ai import transcribe as _transcribe

assemblyai_concurent_limit = asyncio.Semaphore(5)


async def transcribe(video_url: str) -> str:
    async with assemblyai_concurent_limit:
        transcript = await _transcribe(video_url)
    return transcript


def sed(command, input_string):
    sed_command = ["sed", "s/" + command]
    process = subprocess.Popen(
        sed_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    output, errors = process.communicate(input=input_string)
    if process.returncode != 0:
        raise Exception(f"Error applying sed command: {errors}")
    return output


with open("./transcripter_dict.txt", "r") as f:
    replacements = [line.strip() for line in f.readlines()]


def post_process(input_text: str):
    input_text = deepcopy(input_text)
    for cmd in replacements:
        output_text = sed(cmd, input_text)
        if input_text != output_text:
            print("applied:", cmd)
        input_text = output_text
    return input_text


async def per_video(video: M.PostCourseVideo, executor):
    video_url = video.video_file.url
    id = video.id
    assert id is not None
    transcript_on_strapi = deepcopy(video.transcript) or ""
    if transcript_on_strapi.strip() != "":
        transcript_generated = deepcopy(transcript_on_strapi)
    else:
        transcript_generated = await transcribe(video_url)
    transcript_generated = await asyncio.get_event_loop().run_in_executor(
        executor, post_process, transcript_generated
    )
    if transcript_on_strapi == transcript_generated:
        return
    updates = {"transcript": transcript_generated}
    await M.PostCourseVideo(**{**video.__dict__, **updates}).put()


async def fetch_videos():
    videos = await M.PostCourseVideo.all()
    videos = [i for i in videos if i.video_file]
    print(f"got {len(videos)} videos")
    with ThreadPoolExecutor() as executor:
        await asyncio.gather(*(per_video(video, executor) for video in videos))


if __name__ == "__main__":
    asyncio.run(fetch_videos())
