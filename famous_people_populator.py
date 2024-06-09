import asyncio
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import requests

import strapi_models as M


def load_file(file_path):
    with open(file_path) as f:
        return f.read()


def download_file(url, name):
    if not url:
        return
    curl_command = ["curl", url, "--output", f"./images/{name}.jpg"]
    subprocess.run(curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return name


async def download_file_async(url, name, executor):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, download_file, url, name)


async def main():
    famous = load_file("famous.json")
    famous = json.loads(famous)

    person = famous[0]
    name = person["name"]
    picture_url = person["picture_url"]
    if picture_url:
        image_path = f"./images/{name}.jpg"
        file = await M.Media.upload_file(image_path)
        updates = {"picture": file}
        await M.FamousPeople(**{**person, **updates}).post()

    # for person in famous:
    # file = await M.Media.upload_file(audio_path)
    # assert file is not None
    # updates = {"audio_file": file}
    # await M.PostCourseVideo(**{**video.__dict__, **updates}).put()
    # os.remove(audio_path)


if __name__ == "__main__":
    asyncio.run(main())
