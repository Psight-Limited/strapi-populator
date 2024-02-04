import asyncio
import os
import shutil

import strapi_models as M
from kartra_api import KartraPost, fetch_all_posts
from vimeo_download import download_video


async def kartra_to_strapi(post_info: KartraPost):
    print(post_info.id, post_info.name, "starting post")
    video_path = f"./videos/{post_info.id}.mp4"
    audio_path = f"./videos/{post_info.id}.mp3"
    thumbnail_path = f"./videos/{post_info.id}.jpg"
    folder_path = os.path.dirname(video_path)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    course, _ = await M.Course.get_or_create(title=post_info.course.id)
    category, _ = await M.CourseCategory.get_or_create(
        name=post_info.category.name,
        course=course,
    )
    subcategory, _ = await M.CourseSubcategory.get_or_create(
        name=post_info.subcategory.name,
        course_category=category,
    )
    post = await M.PostCourseVideo.get(
        title=post_info.name,
        course_subcategory=subcategory,
    )
    if post is not None:
        print(post_info.id, post_info.name, "already exists?")
        return
    video_id = post_info.fetch().vimeo_id
    if video_id is None:
        print(post_info.id, post_info.name, "no kartra video found")
        return
    if not download_video(video_id, video_path):
        print(post_info.id, post_info.name, "download failed!!")
        return
    await M.PostCourseVideo(
        title=post_info.name,
        video_file=await M.Media.upload_file(video_path),
        audio_file=await M.Media.upload_file(audio_path),
        thumbnail=await M.Media.upload_file(thumbnail_path),
        course_subcategory=subcategory,
    ).post()
    print(post_info.id, post_info.name, "sucess")


async def main():
    print("starting")
    course_ids = [
        # "joS402GfMsrK",  # EBT
        # "IvMmhsbBLqYf",  # Journeyman
        # "howtotypeyourself",
        # "7oUXLSciuEYf",  # EYF
        # "rmEnfb8YRlrK",  # UMF
        "BC7bO1RDMuZa",  # Acolyte
    ]
    for course_id in course_ids:
        print(f"starting course {course_id}")
        for post in fetch_all_posts(course_id):
            await kartra_to_strapi(post)


if __name__ == "__main__":
    asyncio.run(main())
