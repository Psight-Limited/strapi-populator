import os
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, ValidationError

import strapi_object


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


class Media(BaseModel):
    id: int
    name: str
    alternativeText: Optional[str] = None
    caption: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    formats: Optional[Dict[str, Any]] = None
    hash: str
    ext: str
    mime: str
    size: float
    url: str
    previewUrl: Optional[str] = None
    provider: str
    provider_metadata: Optional[Dict[str, Any]] = None
    createdAt: str
    updatedAt: str

    def __init__(self, **data):
        super().__init__(**data)

    def serialize_to_post(self):
        return self.__dict__

    @classmethod
    def pre_process_field(cls, field: Any) -> Optional["Media"]:
        if not isinstance(field, dict):
            raise ValueError("Provided data is not a dictionary.")
        if "data" not in field:
            raise ValueError("'data' key not found in provided data.")
        data = field["data"]
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
        except ValidationError as e:
            raise ValueError(f"Invalid media data: {e.errors()}")

    @classmethod
    async def upload_file(cls, file_path: str):
        if not os.path.isfile(file_path):
            return None
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(60 * 60),
        ) as session:
            with open(file_path, "rb") as f:
                async with session.post(
                    url=f"{strapi_object.BASE_URL}/api/upload",
                    data={"files": f},
                ) as response:
                    if response.status != 200:
                        raise Exception(
                            f"{response.status} - {await response.text()}",
                        )
                    response_data = (await response.json())[0]
                    return cls(**response_data)


class Author(strapi_object.StrapiObject, BaseModel):
    id: int
    name: str
    _uri: ClassVar[str] = "/api/authors"

    def __init__(self, **data):
        super().__init__(**data)


class CoachingReplay(strapi_object.StrapiObject, BaseModel):
    id: int
    name: str
    coach: Optional[int] = None
    recording_date: Optional[Datetime] = None
    videofile: Optional[Media] = None
    type: Optional[str] = None
    octagram: Optional[str] = None
    _uri: ClassVar[str] = "/api/coaching-replays"

    def __init__(self, **data):
        super().__init__(**data)

    class Config:
        arbitrary_types_allowed = True


class Course(strapi_object.StrapiObject, BaseModel):
    id: int
    title: str
    course_categories: Optional[List[int]] = None
    _uri: ClassVar[str] = "/api/courses"

    def __init__(self, **data):
        super().__init__(**data)


class CourseCategory(strapi_object.StrapiObject, BaseModel):
    id: int
    name: str
    course: Optional[int] = None
    _uri: ClassVar[str] = "/api/course-categories"

    def __init__(self, **data):
        super().__init__(**data)


class CourseSubcategory(strapi_object.StrapiObject, BaseModel):
    id: int
    name: str
    course_category: Optional[int] = None
    post_youtube_videos: Optional[List[int]] = None
    post_course_videos: Optional[List[int]] = None
    _uri: ClassVar[str] = "/api/course-subcategories"

    def __init__(self, **data):
        super().__init__(**data)

    def serialize_to_filter(self):
        return "filters[course_subcategory][id][$eq]", self.id


class LiveTestYourself(strapi_object.StrapiObject, BaseModel):
    id: int
    prod_test_yourself: Optional[int] = None
    staging_test_yourself: Optional[int] = None

    def __init__(self, **data):
        super().__init__(**data)


class PostBlog(strapi_object.StrapiObject, BaseModel):
    id: int
    title: str
    blog_text: str
    thumbnail: Optional[List[Media]] = None
    seo: Optional[int] = None

    def __init__(self, **data):
        super().__init__(**data)


class PostCourseVideo(strapi_object.StrapiObject, BaseModel):
    id: Optional[int]
    title: str
    author: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    course_subcategory: Optional[int] = None
    video_file: Media
    audio_file: Optional[Media] = None
    thumbnail: Optional[Media] = None
    transcript: Optional[str] = None
    first_frame: Optional[Media] = None
    _uri: ClassVar[str] = "/api/post-course-videos"

    def __init__(self, **data):
        super().__init__(**data)


class PostYoutubeVideo(strapi_object.StrapiObject, BaseModel):
    id: int
    title: str
    author: Optional[int] = None
    youtube_channel: Optional[int] = None
    post_type: str
    season: Optional[int] = None
    episode: Optional[int] = None
    course_subcategory: Optional[int] = None
    url: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    video_file: Media
    audio_file: Optional[Media] = None
    thumbnail: Optional[Media] = None
    transcript: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)


class Season(strapi_object.StrapiObject, BaseModel):
    id: int
    display: str
    season_number: int
    season_part: Optional[int] = None
    post_youtube_videos: Optional[List[int]] = None
    post_course_videos: Optional[List[int]] = None

    def __init__(self, **data):
        super().__init__(**data)


class TestYourself(strapi_object.StrapiObject, BaseModel):
    id: int
    internal_alias: str
    questions: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)


class TestYourselfQuestion(strapi_object.StrapiObject, BaseModel):
    id: int
    choices: Optional[List[int]] = None
    name: str
    question_title: Optional[str] = None
    conditional: bool

    def __init__(self, **data):
        super().__init__(**data)


class Vector(strapi_object.StrapiObject, BaseModel):
    id: int
    name: str
    display: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[Media] = None

    def __init__(self, **data):
        super().__init__(**data)


class YoutubeChannel(strapi_object.StrapiObject, BaseModel):
    id: int
    name: str
    post_youtube_videos: Optional[List[int]] = None

    def __init__(self, **data):
        super().__init__(**data)


class FamousPeople(strapi_object.StrapiObject, BaseModel):
    id: int
    name: str
    octagram: Optional[str] = None
    picture: Optional[Media] = None
    typecode: str
    typecode_order: int
    _uri: ClassVar[str] = "/api/famous-people"

    def __init__(self, **data):
        super().__init__(**data)
