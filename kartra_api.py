import json
import os

import aiohttp
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager


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


def load_cookies_from_json(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
        cookies = data.get("Request Cookies", {})
    return cookies


def fetch_post_html(id, cookie_file="cookie.json"):
    url = f"https://csjoseph.kartra.com/portal/joS402GfMsrK/post/{id}"
    options = Options()
    options.headless = True
    service = Service(GeckoDriverManager().install())
    with webdriver.Firefox(options=options, service=service) as driver:
        driver.get(url)
        cookies = load_cookies_from_json(cookie_file)
        for name, value in cookies.items():
            cookie_dict = {"name": name, "value": value}
            driver.add_cookie(cookie_dict)
        driver.get(url)
        return driver.page_source


class KartraPost(BaseModel):
    id: int
    post_name: str
    subcategory_name: str
    category_name: str
    body: str

    @classmethod
    async def fetch_post_info(cls, id):
        soup = BeautifulSoup(fetch_post_html(id), "html.parser")
        return cls(
            id=id,
            post_name=(
                soup.find("div", class_="panel panel-kartra")
                .find("div", class_="panel-heading")
                .find("h1")
                .get_text(strip=True)
            ),
            subcategory_name=(
                soup.find("div", class_="panel panel-blank menu_box")
                .find("div", class_="panel-heading")
                .find("h2")
                .get_text(strip=True)
            ),
            category_name=(
                soup.find("ul", class_="nav list-unstyled")
                .find("li", class_="dropdown active")
                .find("a")
                .get_text(strip=True)
            ),
            body=(
                soup.find("div", class_="panel panel-kartra")
                .find("div", class_="panel-body")
                .decode_contents()
            ),
        )
