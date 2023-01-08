import traceback
from pyppeteer.page import Page

from scrapper.structs import User
from scrapper.loader import logger
from core.database import DatabaseAsync


class EmptyContentError(ValueError):
    pass


async def parse_chat_request(data: dict, user: User) -> None:
    def build_values_query(v: dict):
        return "(%s, '%s')" % (v.get("vid"), v.get("state"))

    vids: list[dict] = []
    topics: dict = data["resources"]["negotiation_topics"]

    for topic in topics.values():
        vids.append({"vid": topic["vacancyId"], "state": topic["applicantState"]})

    update_vids = ",".join(build_values_query(v) for v in vids)
    if not update_vids:
        raise EmptyContentError

    query = (
        """
        UPDATE vacancies SET 
          status = upd.status
        FROM (VALUES
            %s
        ) AS upd (
            vacancy_id, status
        )
        WHERE 
            vacancies.vacancy_id = upd.vacancy_id
        """ % update_vids
    )

    async with DatabaseAsync() as conn:
        await conn.execute(query)


async def open_chat_page(page: Page, user: User) -> None:
    await page.goto("https://hh.ru/?hhtmFrom=account_login", {"timeout": 10000})

    for page_number in range(0, 9999):
        try:
            new_page = await page.goto(
                "https://chatik.hh.ru/api/"
                "chats?filterUnread=false"
                "&filterHasTextMessage=true"
                "&do_not_track_session_events=true"
                "&page=%s" % page_number,
                {"timeout": 10000}
            )
            await parse_chat_request(await new_page.json(), user)

        except EmptyContentError:
            logger.info("Done parsing on page#%s" % page_number)
            break

        except Exception as e:
            logger.critical("Can't parse chat data %s" % traceback.print_exception(e))
