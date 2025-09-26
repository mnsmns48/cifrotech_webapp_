import json
import os
from typing import List

from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api_service.schemas import ParsingLinesIn

from config import BROWSER_HEADERS, BASE_DIR
from models import Vendor, HUbStock
from parsing.browser import create_browser, open_page

this_file_name = os.path.basename(__file__).rsplit('.', 1)[0]
cookie_file = f"{BASE_DIR}/parsing/sources/{this_file_name}.json"


class BaseParser:
    def __init__(self, redis: Redis, progress: str, vendor: Vendor, url: str, session: AsyncSession):
        self.page, self.browser, self.playwright = None, None, None
        self.pages = list()
        self.progress = progress
        self.url = url
        self.vendor = vendor
        self.session = session
        self.redis = redis

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
        await self.page.goto(self.url + '&sort_by=price&sort_order=asc&items_per_page=120')
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
    async def extract_pic(swiper_wrapper: Tag) -> list | None:
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

    @staticmethod
    async def page_data_separation(soup: BeautifulSoup, session: AsyncSession) -> List[ParsingLinesIn]:
        def extract_text(block, selector=None):
            if not block:
                return None
            target = block.find(selector) if selector else block
            return target.get_text().strip() if target else None

        content_list = soup.find_all("div", class_="ty-product-block ty-compact-list__content")
        origin_map = dict()
        for line in content_list:
            origin_block = line.find("div", class_="code")
            origin_text = extract_text(origin_block, "span")
            if origin_text and origin_text.isdigit():
                origin = int(origin_text)
                origin_map[origin] = line

        if not origin_map:
            return []

        stmt = select(HUbStock.origin).where(HUbStock.origin.in_(origin_map.keys()))
        result = await session.execute(stmt)
        hubstock_origins = set(row.origin for row in result)

        parsing_lines_result = list()
        for origin, line in origin_map.items():
            try:
                title_block = line.find("div", class_="category-list-item__title ty-compact-list__title")
                title = extract_text(title_block, "a") or ""
                link = title_block.a.get("href") if title_block and title_block.a else None

                shipment = extract_text(line.find("p", class_="delivery"))
                warranty = extract_text(line.find("div", class_="divisible-block"), "span")

                price_block = line.find("span", class_="ty-price-num", id=lambda x: x and "sec_discounted_price" in x)
                if not price_block:
                    continue
                price_text = price_block.get_text().strip().replace("\xa0", "")
                input_price = float(price_text) if price_text.replace(".", "").isdigit() else None
                if input_price is None:
                    continue

                pics_block = line.find("div", class_="swiper-wrapper")
                pics = await BaseParser.extract_pic(pics_block) if pics_block else None
                preview = pics_block.find("a").get("href") if pics_block and pics_block.find("a") else None

                optional_block = line.find("div", class_="code")
                optional = extract_text(optional_block.find_next_sibling("div")) if optional_block else None

                parsing_lines_result.append(
                    ParsingLinesIn(
                        origin=origin,
                        title=title,
                        link=link,
                        shipment=shipment,
                        warranty=warranty,
                        input_price=input_price,
                        output_price=None,
                        pics=pics,
                        preview=preview,
                        optional=optional,
                        features_title=None,
                        profit_range=None,
                        in_hub=origin in hubstock_origins
                    )
                )
            except (AttributeError, ValueError, TypeError, IndexError, ValidationError):
                continue

        return parsing_lines_result

    async def get_parsed_lines(self) -> List[ParsingLinesIn]:
        opened_page = await open_page(page=self.page, url=self.url)
        soup = opened_page['soup']
        self.pages = self.actual_pagination(soup)
        await self.redis.publish(self.progress, f"{len(self.pages) + 1} страниц для сбора информации")
        if not await self.check_auth(text=soup):
            await self.redis.publish(self.progress, "Авторизация не пройдена")
            await self.authorization()
            await self.page.close()
            context = await self.browser.new_context()
            with open(cookie_file, "r") as file:
                storage_state = json.load(file)
            await context.add_cookies(storage_state["cookies"])
            self.page = await context.new_page()
            await stealth_async(self.page)
            opened_page = await open_page(page=self.page, url=self.url)
            soup = opened_page['soup']
            self.pages = self.actual_pagination(soup)

        visited_urls = set()
        urls_to_visit = [self.url] + [page.a.get("href") for page in self.pages if page.a]

        result_lines: List[ParsingLinesIn] = list()
        page_counter = 1

        while urls_to_visit:
            url = urls_to_visit.pop(0)
            if url in visited_urls:
                continue
            visited_urls.add(url)

            opened_page = await open_page(page=self.page, url=url)
            soup = opened_page['soup']
            lines = await self.page_data_separation(soup=soup, session=self.session)
            result_lines.extend(lines)

            await self.redis.publish(self.progress, f"Страница {page_counter} сохранена")
            page_counter += 1

            new_pages = self.actual_pagination(soup)
            for page in new_pages:
                href = page.a.get("href") if page.a else None
                if href and href not in visited_urls and href not in urls_to_visit:
                    urls_to_visit.append(href)

        return result_lines
