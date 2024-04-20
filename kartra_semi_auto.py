import asyncio
import json
import os
import re
import traceback

import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import strapi_models as M
from crypto import encrypt

path_to_chromedriver = "./chromedriver"
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
service = Service(executable_path=path_to_chromedriver)
d = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(d, 10)


def outerHTML(obj) -> str:
    return obj.get_attribute("outerHTML")


try:
    with open("cookies.json", "r") as file:
        cookies = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    cookies = None

d.get("https://app.kartra.com")
if cookies:
    for cookie in cookies:
        d.add_cookie(cookie)
else:
    input("Press Enter once you have logged in, and I will save your cookies.")
    cookies = d.get_cookies()
    with open("cookies.json", "w") as file:
        json.dump(cookies, file)
d.get("https://app.kartra.com")
if d.current_url != "https://app.kartra.com/dashboard":
    raise Exception("Bad Cookies")


async def go_to_journeyman():
    d.get("https://app.kartra.com/membership/edit/29")
    wait.until(EC.element_to_be_clickable((By.ID, "save-tab-0"))).click()
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Launch builder"))).click()
    wait.until(
        EC.invisibility_of_element(
            (By.CSS_SELECTOR, "div.overlay_inner ring-loader_new")
        )
    )
    d.execute_script(
        "arguments[0].click();",
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sideblock_handle"))),
    )


videos = None


async def get_videos():
    global videos
    if videos is None:
        videos = await M.PostCourseVideo.all()
    return videos


async def find_video(hash):
    for video in await get_videos():
        if hash == video.video_file.hash:
            assert video.id is not None
            return video
    raise


def escape_curly_braces(html_content):
    # Escapes all curly braces that do not match the pattern {digit}
    escaped_content = re.sub(r"(?<!{){(?![0-9]})", "{{", html_content)
    escaped_content = re.sub(r"(?<!{[0-9])}(?!})", "}}", escaped_content)
    return escaped_content


async def run():
    page = d.find_element(By.CSS_SELECTOR, "div.membership_page")
    code = outerHTML(page.find_element(By.CSS_SELECTOR, "[td_type='code']"))
    pattern = r"https:\/\/csj-cdn.sfo3.cdn.digitaloceanspaces.com\/([a-zA-z0-9]+).mp4"
    mp4_video_hash = re.findall(pattern, code)[0]
    video = await find_video(mp4_video_hash)
    id = encrypt(str(video.id))
    with open("./kartra_video_post_template.html", "r") as f:
        res = f.read()
    res = escape_curly_braces(res)
    res = res.format(video.title, id)
    return res


def get_current_title():
    try:
        return d.find_element(By.CSS_SELECTOR, ".js_post_content_header_name").text
    except Exception:
        return "none"


async def monitor_changes():
    last_url = get_current_title()
    while True:
        await asyncio.sleep(0.05)
        if get_current_title() != last_url:
            last_url = get_current_title()
            os.system("clear")
            try:
                result = await run()
                print(f"{result}\n\n")
                pyperclip.copy(result)
            except Exception:
                print(f"No result\n\n")
                traceback.print_exc()


async def main():
    await asyncio.gather(go_to_journeyman(), get_videos())
    await monitor_changes()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
