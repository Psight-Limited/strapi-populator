import asyncio
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

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


@dataclass
class Person:
    name: str
    picture_url: Optional[str]
    typecode: str

    @classmethod
    def from_dict(cls, data: dict) -> "Person":
        return cls(
            name=data["name"],
            picture_url=data.get("picture_url"),
            typecode=data["typecode"],
        )


def load_file(file_path: str) -> str:
    with open(file_path) as f:
        return f.read()


def download_file(url: str, name: str) -> Optional[str]:
    if not url:
        return None
    curl_command = ["curl", url, "--output", f"./images/{name}.jpg"]
    subprocess.run(curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return name


async def download_file_async(
    url: str, name: str, executor: ThreadPoolExecutor
) -> Optional[str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, download_file, url, name)


async def post_famous_person(person: Person, semaphore: asyncio.Semaphore) -> None:
    if person.picture_url:
        image_path = f"./images/{person.name}.jpg"
        async with semaphore:
            file = await M.Media.upload_file(image_path)
            updates = {"picture": file}
            await M.FamousPeople(**{**person.__dict__, **updates}).post()


async def put_typecode_order(person: Person, semaphore: asyncio.Semaphore) -> None:
    print(f"Updating {person.name}")
    async with semaphore:
        typecode_order = types.index(person.typecode)
        updates = {"typecode_order": typecode_order}
        await M.FamousPeople(**{**person.__dict__, **updates}).put()
        print(f"Updated {person.name} with {typecode_order}")


def generate_type_list() -> dict:
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


async def generate_missing_images(
    person: Person, typelist: dict, semaphore: asyncio.Semaphore
) -> None:
    name = person.name
    typecode = person.typecode
    typecode_list = typelist[typecode]
    if name not in typecode_list:
        with open("./missing.txt", "a") as f:
            f.write(f"{name}\n")
        return
    typecode_index = typecode_list.index(name) + 1
    image_path = f"./Types/{typecode.upper()}/{typecode_index}.jpg"
    print(f"Uploading {name} from {image_path}")

    async with semaphore:
        file = await M.Media.upload_file(image_path)
        typecode_order = types.index(typecode)
        updates = {"picture": file, "typecode_order": typecode_order}
        await M.FamousPeople(**{**person.__dict__, **updates}).post()
        print(f"Uploaded {name} from {image_path}")


async def main():
    tasks = []
    typelist = generate_type_list()
    semaphore = asyncio.Semaphore(20)

    famous_people_data = json.loads(load_file("./filtered_famous.json"))
    famous_people = [Person.from_dict(person) for person in famous_people_data]

    for person in famous_people:
        tasks.append(generate_missing_images(person, typelist, semaphore))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
