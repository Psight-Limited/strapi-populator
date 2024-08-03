import os
import urllib
from dataclasses import dataclass, fields
from typing import (Any, Optional, Type, TypeVar, Union, get_args,
                    get_type_hints)

import aiohttp

BASE_URL = os.getenv("STRAPI_URL")
assert BASE_URL is not None
print(f"Using {BASE_URL=}")
T = TypeVar("T")


def is_optional_type(type_hint: Type) -> bool:
    return get_origin(type_hint) is Union and type(None) in get_args(type_hint)


def get_origin(type_hint: Type) -> Type:
    return getattr(type_hint, "__origin__", None)


def unwrap_dict_with_data(obj):
    if not isinstance(obj, dict) or "data" not in obj:
        return obj
    return obj["data"]


def pre_process_field(field: Any, expected_type: Type) -> Any:
    field = unwrap_dict_with_data(field)
    if hasattr(expected_type, "pre_process_field"):
        return expected_type.pre_process_field(field)
    if is_optional_type(expected_type):
        if field is None:
            return None
        return pre_process_field(field, get_args(expected_type)[0])
    if get_origin(expected_type) is list:
        if field is None:
            return None
        inner_type = get_args(expected_type)[0]
        return [pre_process_field(item, inner_type) for item in field]
    if type(field) is expected_type:
        return field
    return field


def serialize_to_post(obj):
    if isinstance(obj, dict):
        return {k: serialize_to_post(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return type(obj)(serialize_to_post(v) for v in obj)

    if hasattr(obj, "serialize_to_post"):
        return obj.serialize_to_post()
    return obj


class StrapiMeta(type):
    def __call__(cls, *args, **kwargs):
        if "attributes" in kwargs:
            attributes = kwargs.pop("attributes")
            kwargs.update(attributes)
        return super().__call__(*args, **kwargs)


@dataclass(init=False, repr=False)
class StrapiObject(metaclass=StrapiMeta):
    id: Optional[int] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    publishedAt: Optional[str] = None

    def __init__(self, **data):
        for key, value in data.items():
            if key == "transcript":
                continue
            expected_type = get_type_hints(self.__class__).get(key)
            if expected_type:
                value = pre_process_field(value, expected_type)
            setattr(self, key, value)

    @classmethod
    def pre_process_field(cls, obj):
        if obj is None:
            return None
        return cls(**{"id": obj.get("id"), **obj.get("attributes", {})})

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        res = f"{self.__class__.__name__}("
        for field_info in fields(self):
            k = field_info.name
            v = getattr(self, k)
            res += f"\n    {k}={v.__repr__()}"
        res += "\n)"
        return res

    @classmethod
    async def all(cls):
        url = f"{BASE_URL}{cls._uri}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=url,
                timeout=10,
                params={
                    "populate": "deep",
                    "pagination[limit]": "-1",
                    "publicationState": "preview",
                },
            ) as response:
                if response.status != 200:
                    raise Exception(
                        f"{response.status} - {await response.text()}",
                    )
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
        url = f"{BASE_URL}{cls._uri}?{query_string}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=url,
                params={"populate": "deep"},
            ) as response:
                if response.status != 200:
                    print(url)
                    raise Exception(response.status)
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
        data.pop("id", None)  # Remove id if it exists
        data = {k: serialize_to_post(v) for k, v in data.items()}
        data = {"data": data}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=f"{BASE_URL}{self._uri}",
                json=data,
            ) as response:
                assert response.status == 200, await response.text()
                response_data = await response.json()
                new_data = response_data.get("data")
                if new_data:
                    self.id = new_data["id"]  # Update the id of the object
                    attributes = new_data.get("attributes", {})
                    for key, value in attributes.items():
                        expected_type = get_type_hints(self.__class__).get(key)
                        if expected_type:
                            value = pre_process_field(value, expected_type)
                        setattr(self, key, value)
                return self

    async def delete(self):
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                url=f"{BASE_URL}{self._uri}/{self.id}",
            ) as response:
                assert response.status == 200

    async def put(self):
        data = {k: serialize_to_post(v) for k, v in self.__dict__.items() if k != "id"}
        data = {"data": data}
        async with aiohttp.ClientSession() as session:
            async with session.put(
                url=f"{BASE_URL}{self._uri}/{self.id}",
                json=data,
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to update: {await response.text()}")
                response_data = await response.json()
                updated_data = response_data.get("data")
                if "attributes" in updated_data:
                    updated_data = updated_data.get("attributes", {})
                for key, value in updated_data.items():
                    expected_type = get_type_hints(self.__class__).get(key)
                    if expected_type:
                        value = pre_process_field(value, expected_type)
                    self.__dict__[key] = value
                return self

    def serialize_to_post(self) -> Any:
        return self.id
