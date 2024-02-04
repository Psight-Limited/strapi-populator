import unittest

import strapi_models as M


class TestFullPush(unittest.IsolatedAsyncioTestCase):
    async def test_full(self):
        try:
            course, _ = await M.Course.get_or_create(
                title="a",
            )
            assert isinstance(course, M.Course)
            category, _ = await M.CourseCategory.get_or_create(
                name="b",
                course=course,
            )
            assert isinstance(category, M.CourseCategory)
            subcategory, _ = await M.CourseSubcategory.get_or_create(
                name="c",
                course_category=category,
            )
            assert isinstance(subcategory, M.CourseSubcategory)
            post = await M.PostCourseVideo(
                title="hello world",
                video_file=await M.Media.upload_file(
                    "../pineapple-back/videos/yt_BSfpoSrCGsQ.mp4"
                ),
                course_subcategory=subcategory,
            ).post()
            assert isinstance(post, M.PostCourseVideo)
        except:
            raise
        await course.delete()
        await category.delete()
        await subcategory.delete()
        await post.delete()


class TestMedia(unittest.IsolatedAsyncioTestCase):
    async def test_upload_file(self):
        file_path = "../pineapple-back/videos/yt_BSfpoSrCGsQ.mp4"
        self.assertIsInstance(
            await M.Media.upload_file(file_path),
            M.Media,
        )


class TestSubCategory(unittest.IsolatedAsyncioTestCase):
    async def test_get_or_create_already_exists(self):
        obj, created = await M.CourseSubcategory.get_or_create(
            name="c",
        )
        assert isinstance(obj, M.CourseSubcategory)
        assert not created

    async def test_get_or_create_already_notexists(self):
        obj, created = await M.CourseSubcategory.get_or_create(
            name="fdasfs",
        )
        assert isinstance(obj, M.CourseSubcategory)
        assert created
        assert isinstance(obj.id, int)
        await obj.delete()
        r = await M.CourseSubcategory.get(name=obj.name)
        assert r is None


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
        obj = M.PostCourseVideo(**self.data)
        self.assertEqual(obj.title, self.data["attributes"]["title"])
        self.assertEqual(obj.id, self.data["id"])
        obj = M.PostCourseVideo(**self.data)
        self.assertEqual(obj.title, self.data["attributes"]["title"])
        self.assertEqual(obj.id, self.data["id"])

    async def test_object_media(self):
        obj = M.PostCourseVideo(**self.data)
        self.assertEqual(
            obj.video_file.url,
            self.data["attributes"]["video_file"]["data"]["attributes"]["url"],
        )

    async def test_get_all(self):
        objs = await M.PostCourseVideo.all()
        self.assertIsInstance(
            objs,
            list,
            f"expected list[CourseVideo], got {type(objs).__name__}",
        )
        for obj in objs:
            self.assertIsInstance(
                obj,
                M.PostCourseVideo,
                f"expected list[CourseVideo], got list[{type(obj).__name__}]",
            )

    async def test_get_one(self):
        obj = await M.PostCourseVideo.get(id=self.data["id"])
        assert isinstance(obj, M.PostCourseVideo)
        self.assertEqual(obj.title, self.data["attributes"]["title"])
        self.assertEqual(obj.id, self.data["id"])

    async def test_get_one_nonexistant(self):
        obj = await M.PostCourseVideo.get(id=-99999)
        assert obj is None

    async def test_push_new(self):
        title = "ghdauighipiaudghiusd"
        video_file = await M.Media.upload_file(
            "../pineapple-back/videos/yt_BSfpoSrCGsQ.mp4"
        )
        obj = M.PostCourseVideo(title=title, video_file=video_file)
        r = await obj.post()
        assert isinstance(r, M.PostCourseVideo)
        assert r.title == title
        assert r.video_file == video_file
