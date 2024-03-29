import asyncio
import os
import re
from datetime import datetime, time

import pytz
from dateutil.parser import ParserError, parse

import strapi_models as M
import vimeo_download
from vimeo_download import get_videos_from_folder


def get_unique_filename(file_name):
    counter = 0 base, extension = os.path.splitext(file_name)
    while True:
        if not os.path.exists(file_name):
            return file_name
        counter += 1
        file_name = f"{base} ({counter}){extension}"


class Video:
    def __init__(self, data: dict) -> None:
        self.data = data

    @property
    def name(self):
        return self.data.get("video", {}).get("name")

    @property
    def uri(self):
        return self.data.get("video", {}).get("uri")

    @property
    def id(self):
        return int(re.search(r"\d+", self.uri).group(0))

    @property
    def file_path(self):
        if hasattr(self, "_file_path"):
            return self._file_path
        folder_path = "./downloads"
        file_name = f"{self.name}.mp4"
        full_path = os.path.join(folder_path, file_name)
        full_path = get_unique_filename(full_path)
        return full_path

    def download(self):
        fp = self.file_path
        vimeo_download.download_video(
            self.id,
            fp,
            audio=False,
            thumbnail=False,
        )
        self._file_path = fp


def get_videos(folder_id: int):
    video_ids = [Video(v) for v in get_videos_from_folder(folder_id)]
    video_ids = list(sorted(video_ids, key=lambda v: v.name))
    return video_ids


async def migrate_videos():
    run = False
    # folder_id = 6005005 # Chase
    folder_id = 6005007 # Jay
    videos = get_videos(folder_id)
    for video in videos:
        if not run:
            print(video.name)
            if video.name == "":
                run = True
            continue
        print(video.name, video.id, video.uri, video.file_path)
        video.download()
        await M.CoachingReplay(
            name=os.path.splitext(os.path.split(video.file_path)[1])[0],
            coach=7,
            recording_date=datetime.utcnow(),
            videofile=await M.Media.upload_file(video.file_path),
        ).post()
        print("done uploading\n\n")


def extract_and_remove_date(input_str: str):
    words = input_str.split()
    max_length = 0
    best_fit = None
    best_dt = None
    for i in range(len(words)):
        for j in range(i + 1, len(words) + 1):
            potential_date = " ".join(words[i:j])
            try:
                dt = parse(
                    potential_date,
                    fuzzy=False,
                )
            except ParserError:
                continue
            length = len(potential_date)
            if length > max_length:
                max_length = length
                best_fit = potential_date
                best_dt = dt
    if not best_fit:
        return input_str, None
    input_str = input_str.replace(best_fit, "").strip()
    input_str = re.sub(" +", " ", input_str)
    return input_str, best_dt


def extract_type_and_octagram(input_str: str):
    type_pattern = r"\s*((?:E|I)(?:N|S)(?:T|F)(?:P|J))\s*"
    octagram_pattern = r"\s*((?:S|U)D)\s*\|?\s*((?:S|U)F)\s*"
    type_ = None
    octagram = None
    words = input_str.strip().split()
    bad_indexes = []
    for i, word in enumerate(words):
        type_match = re.match(type_pattern, word, flags=re.I)
        if not type_match:
            continue
        if type_ is not None:
            bad_indexes = []
            type_ = None
            break
        type_ = type_match.group(1)
        bad_indexes.append(i)
        assert isinstance(type_, str)
        type_ = type_.upper()
        break
    words = [x for i, x in enumerate(words) if i not in bad_indexes]
    bad_indexes = []
    for i, word in enumerate(words):
        octagram_match = re.match(octagram_pattern, word, flags=re.I)
        if not octagram_match:
            continue
        if octagram is not None:
            bad_indexes = []
            octagram = None
            break
        octagram = octagram_match.group(1) + octagram_match.group(2)
        bad_indexes.append(i)
        assert isinstance(octagram, str)
        octagram = octagram.upper()
        break
    words = [x for i, x in enumerate(words) if i not in bad_indexes]
    input_str = " ".join(words)
    return input_str, type_, octagram


def extract_name(name_str):
    name_str, type, octagram = extract_type_and_octagram(name_str)
    name_str, date_obj = extract_and_remove_date(name_str)
    return name_str, type, octagram, date_obj


async def parse_titles():
    for video in await M.CoachingReplay.all():
        if video.coach != 7:
            continue
        name, type, octagram, recording_date = extract_name(video.name)
        print()
        print(video.name)
        print(name)
        pst = pytz.timezone("America/Los_Angeles")
        if recording_date:
            recording_date = pst.localize(recording_date)
            recording_date = M.Datetime.from_datetime(recording_date)
        updates = {"name": name}
        if type:
            updates["type"] = type
        if octagram:
            updates["octagram"] = octagram
        if video.recording_date is not None and video.recording_date > pst.localize(
            datetime(2024, 3, 28)
        ):
            updates["recording_date"] = None
        if recording_date:
            updates["recording_date"] = recording_date
        video = M.CoachingReplay(**{**video.__dict__, **updates})
        print(video.recording_date)
        await video.put()


async def main():
    await migrate_videos()
    await parse_titles()


if __name__ == "__main__":
    asyncio.run(main())
