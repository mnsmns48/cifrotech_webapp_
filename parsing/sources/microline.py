import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from openpyxl.utils.formulas import validate
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import get_range_rewards_list, store_harvest_line, get_rr_obj, SourceContext
from api_service.schemas import HarvestLineIn
from config import BROWSER_HEADERS, BASE_DIR
from parsing.browser import create_browser, open_page
from parsing.utils import cost_value_update

this_file_name = os.path.basename(__file__).rsplit('.', 1)[0]
cookie_file = f"{BASE_DIR}/parsing/sources/{this_file_name}.json"


class BaseParser:
    def __init__(self, redis: Redis, progress: str, context: SourceContext, session: AsyncSession):
        self.page, self.browser, self.playwright = None, None, None
        self.pages = list()
        self.progress= progress
        self.vsl = context.vsl
        self.vendor = context.vendor
        self.session = session
        self.redis = redis
        self.range_reward = dict()

    @staticmethod
    async def check_auth(text: BeautifulSoup) -> bool:
        result = bool()
        table = text.find_all('a', {'class': ['sm-buy-in-bulk-button', 'logout-buy-opt']})
        register_line = text.find('div', {'class': 'sm-pricing-info'})
        if register_line:
            link = register_line.find('a')
            if link.getText() == 'Регистрация':
                result = False
        if table and table[0].getText() == "Купить оптом" or result:
            return False
        return True

    async def authorization(self):
        await self.page.goto('https://technosuccess.ru/login')
        await self.redis.publish(self.progress, f"Авторизируюсь")
        await self.page.fill("#login_main_login", self.vendor.login)
        await self.page.fill("#psw_main_login", self.vendor.password)
        await self.page.check("#remember_me_main_login")
        buttons = await self.page.locator('button[name="dispatch[auth.login]"]').all()
        await buttons[1].click()
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.goto(self.vsl.url + '&sort_by=price&sort_order=asc&items_per_page=120')
        storage_state = await self.page.context.storage_state()
        with open(f"{BASE_DIR}/parsing/sources/{this_file_name}.json", "w") as file:
            json.dump(storage_state, file)
        await self.redis.publish(self.progress, f"Авторизция прошла успешно")

    async def run(self):
        self.playwright = await async_playwright().start()
        self.browser = await create_browser(self.playwright)
        await self.redis.publish(self.progress, "data: COUNT=30")
        await self.redis.publish(self.progress, f"Браузер запущен")
        context = await self.browser.new_context()
        await context.set_extra_http_headers(BROWSER_HEADERS)
        if not os.path.exists(cookie_file):
            self.page = await context.new_page()
            await self.redis.publish(self.progress, f"Нет COOKIE файла")
            await self.authorization()
            await self.page.close()
        else:
            await self.redis.publish(self.progress, f"COOKIE файл присутствует")
        with open(cookie_file, "r") as file:
            storage_state = json.load(file)
        await context.add_cookies(storage_state["cookies"])
        self.page = await context.new_page()
        await stealth_async(self.page)

    @staticmethod
    async def extract_pic(swiper_wrapper: BeautifulSoup) -> list | None:
        carousel = swiper_wrapper.find_all('div')
        pics = list()
        for item in carousel:
            if 'data-ca-image-width' in item.a.attrs and 'data-ca-image-height' in item.a.attrs:
                width = item.a.attrs['data-ca-image-width']
                height = item.a.attrs['data-ca-image-height']
                image = item.a.get('href')
                if image:
                    pics.append(
                        f'https://technosuccess.ru/images/thumbnails/'
                        f'{width}/{height}/detailed{image.rsplit("detailed", 1)[1]}')
            else:
                pics.append(item.a.get('href'))
        return pics

    @staticmethod
    async def store_results(soup: BeautifulSoup, session: AsyncSession, vsl_id: int, range_reward_id: int) -> list:
        parsing_lines_result = list()
        content_list = soup.find_all("div", class_="ty-product-block ty-compact-list__content")
        for line in content_list:
            try:
                origin_block = line.find("div", class_="code")
                origin_span = origin_block.find("span") if origin_block else None
                origin_text = origin_span.get_text().strip() if origin_span else None
                origin = int(origin_text) if origin_text and origin_text.isdigit() else 0

                # title & link
                title_block = line.find("div", class_="category-list-item__title ty-compact-list__title")
                title = title_block.a.get_text().strip() if title_block and title_block.a else ""
                link = title_block.a.get("href") if title_block and title_block.a else None

                # shipment
                shipment_block = line.find("p", class_="delivery")
                shipment = shipment_block.get_text().strip() if shipment_block else None

                # warranty
                warranty_block = line.find("div", class_="divisible-block")
                warranty_span = warranty_block.find("span") if warranty_block else None
                warranty = warranty_span.get_text().strip() if warranty_span else None

                # input_price
                price_block = line.find("span", class_="ty-price-num", id=lambda x: x and "sec_discounted_price" in x)
                if not price_block:
                    continue
                price_text = price_block.get_text().strip().replace("\xa0", "")
                input_price = float(price_text) if price_text.replace(".", "").isdigit() else None
                if input_price is None:
                    continue

                # pics & preview
                pics_block = line.find("div", class_="swiper-wrapper")
                pics = await BaseParser.extract_pic(pics_block) if pics_block else None
                preview = pics_block.find("a").get("href") if pics_block and pics_block.find("a") else None

                # optional
                optional_block = origin_block.find_next_sibling("div") if origin_block else None
                optional = optional_block.get_text().strip() if optional_block else None

                item = HarvestLineIn(
                    origin=origin,
                    title=title,
                    link=link,
                    shipment=shipment,
                    warranty=warranty,
                    input_price=input_price,
                    pics=pics,
                    preview=preview,
                    optional=optional,
                    vsl_id=vsl_id
                )
                parsing_lines_result.append(item)

            except (AttributeError, ValueError, TypeError, IndexError, ValidationError):
                continue

        ranges = await get_range_rewards_list(session=session, range_id=range_reward_id)
        validate_items = cost_value_update(parsing_lines_result, list(ranges))
        stored_items = await store_harvest_line(session=session, items=validate_items)
        return stored_items

    @staticmethod
    def actual_pagination(soup: BeautifulSoup) -> list:
        pagination = soup.find('ul', {'class': 'pagination'})
        pages = list()
        if not pagination:
            return pages
        for li in pagination.find_all('li'):
            link = li.find('a')
            if (link and link.getText().strip() not in
                    ["Предыдущая", "Следующая"] and "active" not in li.get("class", [])):
                pages.append(li)
        return pages

    async def process(self) -> dict:
        opened_page = await open_page(page=self.page, url=self.vsl.url)
        self.pages = self.actual_pagination(opened_page['soup'])
        self.range_reward: dict = await get_rr_obj(session=self.session)

        await self.redis.publish(self.progress, f"{len(self.pages) - 1} страниц для сбора информации")
        if not await self.check_auth(text=opened_page['soup']):
            context = await self.browser.new_context()
            await self.redis.publish(self.progress, "Авторизация не пройдена")
            await self.authorization()
            await self.page.close()
            with open(cookie_file, "r") as file:
                storage_state = json.load(file)
            await context.add_cookies(storage_state["cookies"])
            self.page = await context.new_page()
            await stealth_async(self.page)
            opened_page = await open_page(page=self.page, url=self.vsl.url)
        result = await self.store_results(soup=opened_page['soup'], session=self.session, vsl_id=self.vsl.id,
                                          range_reward_id=self.range_reward.get('id'))
        await self.redis.publish(self.progress, f"Страница 1 из {len(self.pages) + 1} сохранена")
        page_counter = 0
        while page_counter < len(self.pages):
            await self.redis.publish(self.progress, f"data: COUNT={len(self.pages) + 5}")
            page_item = self.pages[page_counter]
            next_url = page_item.a.get('href')
            opened_page = await open_page(page=self.page, url=next_url)
            result += await self.store_results(soup=opened_page['soup'],
                                               session=self.session,
                                               vsl_id=self.vsl.id,
                                               range_reward_id=self.range_reward.get('id'))
            page_counter += 1
            await self.redis.publish(self.progress,
                                     f"Страница {page_counter} из {len(self.pages) + 1} сохранена")
            new_pages = self.actual_pagination(opened_page['soup'])
            if len(new_pages) > len(self.pages):
                self.pages = new_pages
                await self.redis.publish(self.progress, f"data: COUNT={len(self.pages) + 5}")
        return {'dt_parsed': datetime.now(),
                'range_reward': self.range_reward,
                'parsing_result': result}
