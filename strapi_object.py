import os
import urllib.parse
from typing import Any, Optional, Type, get_args, get_origin, get_type_hints

import aiohttp

BASE_URL = os.getenv("STRAPI_URL", "http://localhost:1337")


def pre_process_field(field: Any, expected_type: Type) -> Any:
    if get_origin(expected_type) is Optional:
        if field is None:
            return None
        actual_type = get_args(expected_type)[0]
        return pre_process_field(field, actual_type)
    if type(field) is expected_type:
        return field
    if hasattr(expected_type, "pre_process_field"):
        return expected_type.pre_process_field(field)
    if not isinstance(field, dict) or "data" not in field:
        return field
    data = field["data"]
    if isinstance(data, dict):
        return data.get("id")
    return None


def serialize_to_post(obj):
    if hasattr(obj, "serialize_to_post"):
        return obj.serialize_to_post()
    return obj


class StrapiObject:
    def __init__(self, **data):
        id = data.get("id")
        if "attributes" in data:
            data = data.get("attributes", {})
        if data:
            data = {"id": id, **data}
        for key, value in data.items():
            expected_type = get_type_hints(self.__class__).get(key)
            if expected_type:
                value = pre_process_field(value, expected_type)
            self.__dict__[key] = value

    @classmethod
    async def all(cls):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=f"{BASE_URL}{cls._uri}",
                params={"populate": "deep"},
            ) as response:
                assert response.status == 200
                response_data = await response.json()
                data = response_data.get("data")
                return [cls(**item) for item in data]

    @classmethod
    async def get(cls, **kwargs):
        filters = {}
        for key, value in kwargs.items():
            if hasattr(value, "serialize_to_filter"):
                key, value = value.serialize_to_filter()
                filters[key] = value
                continue
            if (
                hasattr(value, "serialize_to_post")
                and value != value.serialize_to_post()
            ):
                continue
            filters[f"filters[{key}][$eq]"] = value
        query_string = urllib.parse.urlencode(filters)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=f"{BASE_URL}{cls._uri}?{query_string}",
                params={"populate": "deep"},
            ) as response:
                assert response.status == 200
                response_data = await response.json()
                data = response_data.get("data")
                if len(data) == 1:
                    return cls(**data[0])
                else:
                    return None

    @classmethod
    async def get_or_create(cls, **attributes):
        existing_object = await cls.get(**attributes)
        if existing_object:
            return (existing_object, False)
        new_object = cls(**attributes)
        await new_object.post()
        return new_object, True

    async def post(self):
        data = self.__dict__
        data.pop("id")
        data = {k: serialize_to_post(v) for k, v in data.items()}
        data = {"data": data}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=f"{BASE_URL}{self._uri}",
                json=data,
            ) as response:
                assert response.status == 200
                data = await response.json()
                data = data.get("data")
                res = await self.get(id=data["id"])
                assert res is not None
                self.__dict__.update(res.__dict__)
                return self

    async def delete(self):
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                url=f"{BASE_URL}{self._uri}/{self.id}",
            ) as response:
                assert response.status == 200

    def serialize_to_post(self):
        return self.__dict__
