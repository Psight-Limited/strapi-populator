import unittest

from strapi_models import Media, PostCourseVideo


class TestMedia(unittest.IsolatedAsyncioTestCase):
    async def test_upload_file(self):
        file_path = "../pineapple-back/videos/yt_BSfpoSrCGsQ.mp4"
        self.assertIsInstance(
            await Media.upload_file(file_path),
            Media,
        )


class TestCourseVideo(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.data = {
            "id": 3,
            "attributes": {
                "title": "test",
                "createdAt": "2024-01-28T12:40:44.736Z",
                "updatedAt": "2024-01-28T12:40:55.889Z",
                "publishedAt": "2024-01-28T12:40:55.886Z",
                "transcript": None,
                "season": {"data": None},
                "episode": None,
                "author": {"data": None},
                "course_subcategory": {
                    "data": {
                        "id": 1,
                        "attributes": {
                            "name": "c",
                            "createdAt": "2024-01-28T12:34:40.088Z",
                            "updatedAt": "2024-01-28T12:34:40.602Z",
                            "publishedAt": "2024-01-28T12:34:40.600Z",
                            "course_category": {
                                "data": {
                                    "id": 1,
                                    "attributes": {
                                        "name": "b",
                                        "createdAt": "2024-01-28T12:34:31.566Z",
                                        "updatedAt": "2024-01-28T12:34:32.012Z",
                                        "publishedAt": "2024-01-28T12:34:32.010Z",
                                    },
                                }
                            },
                            "post_youtube_videos": {"data": []},
                        },
                    }
                },
                "video_file": {
                    "data": {
                        "id": 1,
                        "attributes": {
                            "name": "yt_BSfpoSrCGsQ.mp4",
                            "alternativeText": None,
                            "caption": None,
                            "width": None,
                            "height": None,
                            "formats": None,
                            "hash": "yt_B_Sfpo_Sr_C_Gs_Q_5c2b0208c1",
                            "ext": ".mp4",
                            "mime": "video/mp4",
                            "size": 1063.89,
                            "url": "/uploads/yt_B_Sfpo_Sr_C_Gs_Q_5c2b0208c1.mp4",
                            "previewUrl": None,
                            "provider": "local",
                            "provider_metadata": None,
                            "createdAt": "2024-01-26T07:08:04.284Z",
                            "updatedAt": "2024-01-28T05:12:37.606Z",
                        },
                    }
                },
                "audio_file": {"data": None},
                "thumbnail": {"data": None},
            },
        }

    async def test_object_creation(self):
        obj = PostCourseVideo(**self.data)
        self.assertEqual(obj.title, self.data["attributes"]["title"])
        self.assertEqual(obj.id, self.data["id"])
        obj = PostCourseVideo(**self.data)
        self.assertEqual(obj.title, self.data["attributes"]["title"])
        self.assertEqual(obj.id, self.data["id"])

    async def test_object_media(self):
        obj = PostCourseVideo(**self.data)
        self.assertEqual(
            obj.video_file.url,
            self.data["attributes"]["video_file"]["data"]["attributes"]["url"],
        )

    async def test_get_all(self):
        objs = await PostCourseVideo.all()
        self.assertIsInstance(
            objs,
            list,
            f"expected list[CourseVideo], got {type(objs).__name__}",
        )
        for obj in objs:
            self.assertIsInstance(
                obj,
                PostCourseVideo,
                f"expected list[CourseVideo], got list[{type(obj).__name__}]",
            )

    async def test_get_one(self):
        obj = await PostCourseVideo.get(self.data["id"])
        self.assertEqual(obj.title, self.data["attributes"]["title"])
        self.assertEqual(obj.id, self.data["id"])
