import os
import shutil

import strapi_models as M
from kartra_api import KartraPost
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
        return
    if post_info.video_id is None:
        return
    download_video(post_info.video_id, video_path)
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
    await M.PostCourseVideo(
        title=post_info.post_name,
        video_file=await M.Media.upload_file(video_path),
        audio_file=await M.Media.upload_file(audio_path),
        thumbnail=await M.Media.upload_file(thumbnail_path),
        course_subcategory=subcategory,
    ).post()
