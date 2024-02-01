import json
import os
import re
from typing import Any, Optional

import aiohttp
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, validator
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

KARTRA_URL = "https://csjoseph.kartra.com/portal"


class KartraClient:
    def __init__(self):
        self.boiler_data = {
            "api_key": os.getenv("KARTRA_API_KEY"),
            "api_password": os.getenv("KARTRA_API_PASSWORD"),
            "app_id": os.getenv("KARTRA_APP_ID"),
        }
        self.base_url = "https://app.kartra.com/api"
        self.rate_limit = 13
        self.limiter = AsyncLimiter(self.rate_limit, 1)

    async def flood_limit(self):
        for _ in range(self.rate_limit):
            await self.limiter.acquire()

    async def _make_request(self, data: dict) -> dict:
        data = {**self.boiler_data, **data}
        async with aiohttp.ClientSession() as session:
            await self.limiter.acquire()
            async with session.post(url=self.base_url, data=data) as response:
                return json.loads(await response.text())

    async def get_users_memberships(self, email: str):
        result = await self._make_request(
            {"get_lead[email]": email},
        )
        memberships = result["lead_details"]["memberships"]
        return [
            f"{i['name']} | {i['level_name']}"
            for i in memberships
            if i["active"] == "1"
        ]

    async def get_tags(self) -> list[str]:
        response = await self._make_request(
            {"actions[0][cmd]": "retrieve_account_tags"},
        )
        return response["account_tags"]


def load_cookies_from_env():
    return json.loads(
        os.getenv("REQUEST_COOKIES", "{}"),
    )


cookies = load_cookies_from_env()
print(cookies)
print("creating driver")
options = Options()
options.add_argument("--headless")
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("start-maximized")
options.add_argument("disable-infobars")
options.add_argument("--disable-extensions")
driver = webdriver.Firefox(
    options=options,
    service=Service(GeckoDriverManager().install()),
)
print("created")


options.add_argument("--headless=new")


def fetch_html(url):
    driver.get(url)
    for name, value in cookies.items():
        driver.add_cookie({"name": name, "value": value})
    driver.get(url)
    is_404 = driver.execute_script(
        "return document.title.includes('404')"
        " || document.body.innerText.includes('404 Not Found');"
    )
    if is_404:
        return None
    return driver.page_source


def fetch_subcategory_urls(html: str, course_id):
    matches = re.findall(
        re.compile(rf"{KARTRA_URL}/{course_id}/subcategory/\d+"),
        html,
    )
    return list(set(matches))


def has_data_post_id_but_not_empty(tag):
    return tag.has_attr("data-post_id") and tag["data-post_id"].strip() != ""


def fetch_post_urls(html: str):
    soup = BeautifulSoup(html, "html.parser")
    elements_with_post_id = soup.find_all(has_data_post_id_but_not_empty)
    post_ids = [int(element["data-post_id"]) for element in elements_with_post_id]
    return post_ids


def fetch_all_post_ids(course_id):
    url = f"{KARTRA_URL}/{course_id}/index"
    print("getting index..")
    html = fetch_html(url)
    assert isinstance(html, str)
    final = []
    final.extend(fetch_post_urls(html))
    for subcat in fetch_subcategory_urls(html, course_id):
        print(f"looking for posts in {subcat}...")
        subcat_html = fetch_html(subcat)
        if subcat_html is None:
            continue
        final.extend(fetch_post_urls(subcat_html))
    final = list(set(final))
    return final


class SoupMonad:
    def __init__(self, value):
        self.value = value

    def find(self, *args, **kwargs):
        if isinstance(self.value, Tag):
            self.value = self.value.find(*args, **kwargs)
        return self

    def get_text(self, *args, **kwargs):
        if isinstance(self.value, Tag):
            return self.value.get_text(*args, **kwargs)


class KartraPost(BaseModel):
    id: int
    post_name: Optional[str]
    subcategory_name: Optional[str]
    category_name: Optional[str]
    body: Optional[Tag]

    class Config:
        arbitrary_types_allowed = True

    @validator("body", pre=True, allow_reuse=True)
    def validate_body(cls, v: Any):
        if not isinstance(v, Tag):
            raise ValueError("body must be a BeautifulSoup Tag object")
        return v

    @property
    def video_id(self):
        if self.body is None:
            return
        vimeo_div = self.body.find("div", {"data-video_source": "vimeo"})
        if not isinstance(vimeo_div, Tag):
            return None
        res = vimeo_div.get("data-video_source_id")
        assert isinstance(res, str)
        return res

    @classmethod
    async def fetch_post_info(cls, id, course_id):
        url = f"{KARTRA_URL}/{course_id}/post/{id}"
        html = fetch_html(url)

        if html is None:
            return None
        soup = BeautifulSoup(html, "html.parser")
        post_name = (
            SoupMonad(soup.find("div", class_="panel panel-kartra"))
            .find("div", class_="panel-heading")
            .find("h1")
            .get_text(strip=True)
        )
        subcategory_name = (
            SoupMonad(soup.find("div", class_="panel panel-blank menu_box"))
            .find("div", class_="panel-heading")
            .find("h2")
            .get_text(strip=True)
        )
        category_name = (
            SoupMonad(soup.find("ul", class_="nav list-unstyled"))
            .find("li", class_="dropdown active")
            .find("a")
            .get_text(strip=True)
        )
        body = (
            SoupMonad(soup.find("div", class_="panel panel-kartra"))
            .find("div", class_="panel-body")
            .value
        )
        assert isinstance(body, Tag) or body is None
        return cls(
            id=id,
            post_name=post_name,
            subcategory_name=subcategory_name,
            category_name=category_name,
            body=body,
        )
