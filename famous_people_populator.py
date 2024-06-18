import asyncio
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import requests

import strapi_models as M

types = [
    "ESTJ",
    "ESTP",
    "ENTJ",
    "ENFJ",
    "ESFJ",
    "ESFP",
    "ENTP",
    "ENFP",
    "ISTJ",
    "ISTP",
    "INTJ",
    "INFJ",
    "ISFJ",
    "ISFP",
    "INTP",
    "INFP",
]


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


async def postFamousPerson(person, semaphore):
    name = person["name"]
    picture_url = person["picture_url"]
    if picture_url:
        image_path = f"./images/{name}.jpg"
        async with semaphore:
            file = await M.Media.upload_file(image_path)
            updates = {"picture": file}
            await M.FamousPeople(**{**person, **updates}).post()


async def putTypecodeOrder(person, semaphore):
    print(f"Updating {person.name}")
    async with semaphore:
        typecode = person.typecode
        typecode_order = types.index(typecode)
        updates = {"typecode_order": typecode_order}
        await M.FamousPeople(**{**person.__dict__, **updates}).put()
        print(f"Updated {person.name} with {typecode_order}")


def generateTypeList():
    typelist_files = [f"./Types/{type}/{type}.txt" for type in types]
    typelist = {}
    for file in typelist_files:
        type = file.split("/")[-1].split(".")[0]
        typeDict = []
        with open(file) as f:
            for line in f:
                typeDict.append(line.strip())

        typelist[type] = typeDict

    return typelist


async def generateMissingImages(person, typelist, semaphore):
    name = person["name"]
    typecode = person["typecode"]
    typecodeList = typelist[typecode]
    if name not in typecodeList:
        with open("./missing.txt", "a") as f:
            f.write(f"{name}\n")
        return
    typecodeIndex = typecodeList.index(name) + 1
    image_path = f"./Types/{typecode.upper()}/{typecodeIndex}.jpg"
    print(f"Uploading {name} from {image_path}")

    async with semaphore:
        file = await M.Media.upload_file(image_path)
        typecode_order = types.index(typecode)
        updates = {"picture": file, "typecode_order": typecode_order}
        await M.FamousPeople(**{**person, **updates}).post()
        print(f"Uploaded {name} from {image_path}")


async def main():
    tasks = []
    typelist = generateTypeList()
    semaphore = asyncio.Semaphore(20)

    famous_people = json.loads(load_file("./filtered_famous.json"))
    for person in famous_people:
        tasks.append(generateMissingImages(person, typelist, semaphore))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
