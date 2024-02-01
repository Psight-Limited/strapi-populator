import asyncio
import os
import shutil

import strapi_models as M
from kartra_api import KartraPost, fetch_all_post_ids
from vimeo_download import download_video


async def kartra_to_strapi(post_id, course_id):
    video_path = f"./videos/{post_id}.mp4"
    audio_path = f"./videos/{post_id}.mp3"
    thumbnail_path = f"./videos/{post_id}.jpg"
    folder_path = os.path.dirname(video_path)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    post_info = await KartraPost.fetch_post_info(post_id, course_id)
    if post_info is None:
        print(post_id, "404")
        return
    if post_info.video_id is None:
        print(post_id, "no kartra video found")
        return
    course, _ = await M.Course.get_or_create(
        title=course_id,
    )
    category, _ = await M.CourseCategory.get_or_create(
        name=post_info.category_name,
        course=course,
    )
    subcategory, _ = await M.CourseSubcategory.get_or_create(
        name=post_info.subcategory_name,
        course_category=category,
    )
    post = await M.PostCourseVideo.get(
        title=post_info.post_name, course_subcategory=subcategory
    )
    if post is not None:
        print(post_id, "already exists?")
        return
    download_video(post_info.video_id, video_path)
    await M.PostCourseVideo(
        title=post_info.post_name,
        video_file=await M.Media.upload_file(video_path),
        audio_file=await M.Media.upload_file(audio_path),
        thumbnail=await M.Media.upload_file(thumbnail_path),
        course_subcategory=subcategory,
    ).post()
    print(post_id, "sucess")


async def main():
    course_ids = [
        "joS402GfMsrK",  # EBT
        "IvMmhsbBLqYf",  # Journeyman
    ]
    for course_id in course_ids:
        for post_id in fetch_all_post_ids(course_id):
            await kartra_to_strapi(post_id, course_id)


if __name__ == "__main__":
    asyncio.run(main())
