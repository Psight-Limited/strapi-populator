import json
import os
from typing import Optional

import aiohttp
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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


print("creating driver")
cookies = json.loads(os.getenv("REQUEST_COOKIES", "{}"))
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-extensions")
driver = webdriver.Chrome(
    options=options,
    service=Service(ChromeDriverManager().install()),
)
print("created")
options.add_argument("--headless=new")


def fetch_html(url):
    print(f"getting {url}")
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


class SoupMonad:
    def __init__(self, value: Tag):
        self.value = value

    def find(self, *args, **kwargs):
        if isinstance(self.value, Tag):
            self.value = self.value.find(*args, **kwargs)
        return self

    def find_all(self, *args, **kwargs):
        if isinstance(self.value, Tag):
            self.value = self.value.find_all(*args, **kwargs)
        return self

    def contents(self):
        if isinstance(self.value, Tag):
            self.value = self.value.contents
        return self

    def get(self, *args, **kwargs):
        if isinstance(self.value, Tag):
            self.value = self.value.get(*args, **kwargs)
        return self

    def get_text(self, *args, **kwargs):
        if isinstance(self.value, Tag):
            self.value = self.value.get_text(*args, **kwargs).strip()
        return self

    def unwrap(self):
        assert self.value is not None
        return self.value


class KartraCourse(BaseModel):
    id: str

    @property
    def url(self) -> str:
        return f"{KARTRA_URL}/{self.id}"


class KartraCategory(BaseModel):
    name: str
    course: KartraCourse


class KartraSubcategory(BaseModel):
    id: int
    name: str
    course: KartraCourse
    category: KartraCategory

    @property
    def url(self) -> str:
        return f"{self.course.url}/subcategory/{self.id}"


class KartraPost(BaseModel):
    id: int
    name: str
    course: KartraCourse
    category: KartraCategory
    subcategory: KartraSubcategory
    vimeo_id: Optional[str] = None

    @property
    def url(self) -> str:
        return f"{self.course.url}/post/{self.id}"

    def fetch(self):
        if hasattr(self, "_fetched"):
            return self
        self._fetched = True
        html = fetch_html(self.url)
        assert html is not None
        soup = BeautifulSoup(html, "html.parser")
        body = SoupMonad(soup).find(class_="panel panel-kartra").unwrap()
        assert isinstance(body, Tag)
        try:
            vimeo_id = (
                SoupMonad(body)
                .find("div", {"data-video_source": "vimeo"})
                .get("data-video_source_id")
                .unwrap()
            )
            if isinstance(vimeo_id, str):
                self.vimeo_id = vimeo_id
        except Exception:
            pass
        return self


def parse_category(soup, course: KartraCourse):
    name = SoupMonad(soup).find("a").get_text().unwrap()
    assert isinstance(name, str)
    category = KartraCategory(name=name, course=course)
    subcategories = SoupMonad(soup).find("ul").contents().unwrap()
    return sum(
        [
            parse_subcategory(subcategory, category, course)
            for subcategory in subcategories
            if isinstance(subcategory, Tag)
        ],
        [],
    )


def parse_subcategory(soup, category: KartraCategory, course: KartraCourse):
    name = SoupMonad(soup).find(class_="dropdown_title").get_text().unwrap()
    url = SoupMonad(soup).find("a").get("href").unwrap()
    assert isinstance(url, str)
    assert isinstance(name, str)
    id = int(url.split("/")[-1])
    if "post" in url:
        return [
            KartraPost(
                id=id,
                name=name,
                course=course,
                category=category,
                subcategory=KartraSubcategory(
                    id=-1,
                    name=category.name,
                    course=course,
                    category=category,
                ),
            )
        ]
    subcategory = KartraSubcategory(
        id=id,
        name=name,
        course=course,
        category=category,
    )
    html = fetch_html(subcategory.url)
    assert html is not None
    soup = BeautifulSoup(html, "html.parser")
    posts = (
        SoupMonad(soup)
        .find(class_="panel panel-blank menu_box")
        .find(class_="panel-body")
        .find("ul")
        .find_all(class_="js_menu_item_navigation_element")
        .unwrap()
    )
    return [
        parse_post(post, subcategory, category, course)
        for post in posts
        if isinstance(post, Tag)
    ]


def parse_post(
    soup,
    subcategory: KartraSubcategory,
    category: KartraCategory,
    course: KartraCourse,
):
    id = SoupMonad(soup).get("data-item_id").unwrap()
    name = SoupMonad(soup).find("span").get_text().unwrap()
    assert isinstance(id, str)
    assert isinstance(name, str)
    id = int(id)
    return KartraPost(
        id=id,
        name=name,
        course=course,
        category=category,
        subcategory=subcategory,
    )


def fetch_all_posts(course_id):
    course = KartraCourse(id=course_id)
    html = fetch_html(course.url + "/index")
    assert html is not None
    soup = BeautifulSoup(html, "html.parser")
    categories = (
        SoupMonad(soup)
        .find(class_="nav list-unstyled")
        .find_all(class_="dropdown")
        .unwrap()
    )
    return sum(
        [
            parse_category(category, course)
            for category in categories
            if isinstance(category, Tag)
        ],
        [],
    )
