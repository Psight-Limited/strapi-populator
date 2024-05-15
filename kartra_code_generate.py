import asyncio
import re
from dotenv import load_dotenv

import pyperclip
import strapi_models as M
from crypto import encrypt

# Load environment variables
load_dotenv()

async def run(id: int):
    video = await M.PostCourseVideo.get(id=id)
    assert video is not None, "Video not found"
    id_encrypted: str = encrypt(str(video.id))
    with open("./kartra_video_post_template.html", "r") as f:
        template = f.read()
    template = escape_curly_braces(template)
    formatted_html = template.format(video.title, id_encrypted)
    return formatted_html

def escape_curly_braces(html_content):
    # Escapes all curly braces that do not match the pattern {digit}
    escaped_content = re.sub(r"(?<!{){(?![0-9]})", "{{", html_content)
    escaped_content = re.sub(r"(?<!{[0-9])}(?!})", "}}", escaped_content)
    return escaped_content

async def main():
    while True:
        id_input = input("Enter a Strapi video id: ")
        try:
            video_id = int(id_input)
            result = await run(video_id)
            pyperclip.copy(result)
            print("Success!")
            print("Result copied to clipboard.")
        except ValueError:
            print("Invalid input. Please enter a valid integer.")
        except AssertionError as e:
            print(e)

if __name__ == "__main__":
    asyncio.run(main())
