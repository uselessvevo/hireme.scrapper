import json
import typing

from database import DatabaseAsync


async def build_area_filter(areas: str) -> typing.Union[str, None]:
    areas = areas.strip().split(",")
    areas_str = ",".join(["'%s'" % i.strip() for i in areas])
    async with DatabaseAsync() as conn:
        query = await conn.fetch(
            """
            SELECT id FROM areas WHERE name in (%s)
            """ % areas_str
        )
    if len(areas) != len(query):
        return

    return "".join(["&area=%s" % i.get("id") for i in query])


async def build_salary_filter(salary: str) -> typing.Union[str, None]:
    if not all(i.isdigit() for i in salary):
        return

    return "salary=%s" % salary


async def get_user_resume_url(user_id: int) -> typing.Union[str, None]:
    async with DatabaseAsync() as conn:
        return await conn.fetchval(
            """
            SELECT resume_url FROM users WHERE id = $1
            """,
            user_id
        )


async def build_resume_url_filter(user_id: int) -> typing.Union[str, None]:
    return "resume=%s" % await get_user_resume_url(user_id)


async def build_resume_filter(resume: str) -> typing.Union[str, None]:
    return "resume=%s" % resume


async def build_text_filter(text: str) -> typing.Union[str, None]:
    return "text=%s" % text


async def build_result_filter(filters: list[str]) -> typing.Union[str, None]:
    return "&".join(filters)[1:]


async def build_filter_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=True)
