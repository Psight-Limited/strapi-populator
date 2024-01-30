from typing import Any, Optional, Type, get_args, get_origin, get_type_hints

import aiohttp

BASE_URL = "http://localhost:1337"


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


class StrapiObject:
    def __init__(self, **data):
        data = {
            "id": data.get("id"),
            **data.get("attributes", {}),
        }
        processed_data = {}
        for key, value in data.items():
            expected_type = get_type_hints(self.__class__).get(key)
            if expected_type:
                processed_value = pre_process_field(value, expected_type)
                processed_data[key] = processed_value
            else:
                processed_data[key] = value
        self.__dict__.update(processed_data)

    @classmethod
    async def all(cls):
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                url=f"{BASE_URL}/api/post-course-videos",
                params={"populate": "deep"},
            )
        response_data = await response.json()
        data = response_data.get("data")
        return [cls(**item) for item in data]

    @classmethod
    async def get(cls, id):
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                url=f"{BASE_URL}/api/post-course-videos/{id}",
                params={"populate": "deep"},
            )
        data = await response.json()
        data = data.get("data")
        return cls(**data)
