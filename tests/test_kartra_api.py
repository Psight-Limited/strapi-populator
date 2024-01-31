import os
import shutil
import unittest

import kartra_api
from vimeo_download import download_video


class TestKartraRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = kartra_api.KartraClient()
        self.post_id = 1191

    async def test_get_users_memberships(self):
        r = await self.client.get_users_memberships("noahlykins@gmail.com")
        self.assertIsInstance(r, list)
        for i in r:
            self.assertIsInstance(i, str)

    async def test_get_tags(self):
        r = await self.client.get_tags()
        self.assertIsInstance(r, list)
        for i in r:
            self.assertIsInstance(i, str)

    async def test_get_post_info(self):
        r = await kartra_api.KartraPost.fetch_post_info(self.post_id)
        assert isinstance(r, kartra_api.KartraPost)
        assert r.post_name is not None
        assert r.subcategory_name is not None
        assert r.category_name is not None
        assert r.video_id is not None
        video_path = "./videos/test.mp4"
        download_video(r.video_id, video_path)
        shutil.rmtree(os.path.dirname(video_path))

    async def test_get_post_info_failure(self):
        r = await kartra_api.KartraPost.fetch_post_info(-999999)
        self.assertIs(r, None)
