import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

import aiohttp

import strapi_object
from famous_people_populator import type_to_typeorder
from strapi_object import StrapiObject


class Datetime(datetime):
    @classmethod
    def from_datetime(cls, datetime_obj: datetime):
        return cls.fromisoformat(datetime_obj.isoformat())

    @classmethod
    def pre_process_field(cls, obj):
        if isinstance(obj, datetime):
            return cls.from_datetime(obj)
        if isinstance(obj, str):
            return cls.fromisoformat(obj.replace("Z", "+00:00"))
        raise NotImplemented

    def serialize_to_post(self):
        return self.isoformat()


@dataclass
class Media:
    id: int
    name: str
    hash: str
    ext: str
    mime: str
    size: float
    url: str
    provider: str
    createdAt: str
    updatedAt: str
    alternativeText: Optional[str] = None
    caption: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    formats: Optional[Dict[str, Any]] = None
    previewUrl: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = None

    def serialize_to_post(self):
        return self.__dict__

    @classmethod
    def pre_process_field(cls, data: Any) -> Optional["Media"]:
        if data is None:
            return None
        if isinstance(data, list):
            return cls.pre_process_field({"data": data[0]})
        if not isinstance(data, dict):
            raise ValueError("The 'data' field must be a dictionary.")
        if "id" not in data or "attributes" not in data:
            raise ValueError(
                "The 'data' dictionary must contain 'id' and 'attributes' keys."
            )
        media_data = {"id": data["id"], **data["attributes"]}
        try:
            return cls(**media_data)
        except TypeError as e:
            raise ValueError(f"Invalid media data: {str(e)}")

    @classmethod
    async def upload_file(cls, file_path: str):
        if not os.path.isfile(file_path):
            return None
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(60 * 60)
        ) as session:
            with open(file_path, "rb") as f:
                async with session.post(
                    url=f"{strapi_object.BASE_URL}/api/upload",
                    data={"files": f},
                ) as response:
                    if response.status != 200:
                        raise Exception(f"{response.status} - {await response.text()}")
                    response_data = (await response.json())[0]
                    return cls(**response_data)


@dataclass(init=False, repr=False)
class Author(StrapiObject):
    name: str
    _uri: ClassVar[str] = "/api/authors"


@dataclass(init=False, repr=False)
class CoachingReplay(StrapiObject):
    name: str
    coach: Optional[Author] = None
    recording_date: Optional[Datetime] = None
    videofile: Optional[Media] = None
    type: Optional[str] = None
    octagram: Optional[str] = None
    _uri: ClassVar[str] = "/api/coaching-replays"


@dataclass(init=False, repr=False)
class Course(StrapiObject):
    title: str
    course_categories: Optional[List["CourseCategory"]] = (
        None  # Forward reference as a string
    )
    _uri: ClassVar[str] = "/api/courses"


@dataclass(init=False, repr=False)
class CourseCategory(StrapiObject):
    name: str
    course: Optional[Course] = None
    _uri: ClassVar[str] = "/api/course-categories"


@dataclass(init=False, repr=False)
class CourseSubcategory(StrapiObject):
    name: str
    course_category: Optional[CourseCategory] = None
    post_youtube_videos: Optional[List["PostYoutubeVideo"]] = (
        None  # Forward reference as a string
    )
    post_course_videos: Optional[List["PostCourseVideo"]] = (
        None  # Forward reference as a string
    )
    _uri: ClassVar[str] = "/api/course-subcategories"

    def serialize_to_filter(self):
        return "filters[course_subcategory][id][$eq]", self.id


@dataclass(init=False, repr=False)
class LiveTestYourself(StrapiObject):
    prod_test_yourself: Optional[int] = None
    staging_test_yourself: Optional[int] = None


@dataclass(init=False, repr=False)
class PostBlog(StrapiObject):
    title: str
    blog_text: str
    thumbnail: Optional[List[Media]] = None
    seo: Optional[int] = None


@dataclass(init=False, repr=False)
class PostCourseVideo(StrapiObject):
    title: str
    video_file: Media
    season: Optional["Season"] = None  # Forward reference as a string
    episode: Optional[int] = None
    course: Optional[Course] = None
    course_category: Optional[CourseCategory] = None
    course_subcategory: Optional[CourseSubcategory] = None
    audio_file: Optional[Media] = None
    thumbnail: Optional[Media] = None
    misc_files: Optional[List[Media]] = None
    transcript: Optional[str] = None
    first_frame: Optional[Media] = None
    full_title: Optional[str] = None
    authors: Optional[List[Author]] = None
    _uri: ClassVar[str] = "/api/post-course-videos"


@dataclass(init=False, repr=False)
class PostYoutubeVideo(StrapiObject):
    title: str
    post_type: str
    video_file: Media
    tags: Optional[str] = None
    author: Optional[Author] = None
    youtube_channel: Optional["YoutubeChannel"] = None  # Forward reference as a string
    season: Optional["Season"] = None  # Forward reference as a string
    episode: Optional[int] = None
    course_subcategory: Optional[CourseSubcategory] = None
    url: Optional[str] = None
    description: Optional[str] = None
    audio_file: Optional[Media] = None
    thumbnail: Optional[Media] = None
    transcript: Optional[str] = None


@dataclass(init=False, repr=False)
class Season(StrapiObject):
    display: str
    season_number: int
    season_part: Optional[int] = None
    post_youtube_videos: Optional[List[PostYoutubeVideo]] = None
    post_course_videos: Optional[List[PostCourseVideo]] = None


@dataclass(init=False, repr=False)
class TestYourself(StrapiObject):
    internal_alias: str
    questions: Optional[str] = None


@dataclass(init=False, repr=False)
class TestYourselfQuestion(StrapiObject):
    name: str
    conditional: bool
    choices: Optional[List[int]] = None
    question_title: Optional[str] = None


@dataclass(init=False, repr=False)
class Vector(StrapiObject):
    name: str
    display: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[Media] = None


@dataclass(init=False, repr=False)
class YoutubeChannel(StrapiObject):
    name: str
    post_youtube_videos: Optional[List[PostYoutubeVideo]] = None


@dataclass(init=False, repr=False)
class FamousPeople(StrapiObject):
    name: str
    typecode: str
    typecode_order: int
    octagram: Optional[str] = None
    picture: Optional[Media] = None
    picture_url: Optional[str] = None
    _uri: ClassVar[str] = "/api/famous-people"

    @classmethod
    def from_csv(cls, row: list) -> "FamousPeople":
        return cls(
            name=row[0],
            typecode=row[1],
            typecode_order=type_to_typeorder(row[1]),
            octagram=row[2] if len(row) > 2 else None,
        )

    @classmethod
    def from_json(cls, data: dict) -> "FamousPeople":
        return cls(
            name=data["name"],
            typecode=data["typecode"],
            typecode_order=type_to_typeorder(data["typecode"]),
            octagram=data["octagram"] if "octagram" in data else None,
            picture_url=data["picture_url"] if  data["picture_url"] else None,
        )

