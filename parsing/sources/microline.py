import asyncio
import json
import os
from datetime import datetime

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import save_harvest
from config import BROWSER_HEADERS, BASE_DIR
from models import Vendor
from parsing.browser import create_browser, open_page

this_file_name = os.path.basename(__file__).rsplit('.', 1)[0]
cookie_file = f"{BASE_DIR}/parsing/sources/{this_file_name}.json"


class FetchParse:
    def __init__(self,
                 progress_channel: str,
                 redis: Redis,
                 url: str,
                 vendor: Vendor,
                 session: AsyncSession):
        self.page, self.browser, self.playwright = None, None, None
        self.pages = list()
        self.category = str()
        self.progress_channel = progress_channel
        self.redis = redis
        self.url = url
        self.vendor = vendor
        self.session = session

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
        await self.redis.publish(self.progress_channel, f"Авторизируюсь")
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
        await self.redis.publish(self.progress_channel, f"Авторизция прошла успешно")

    async def run(self):
        self.playwright = await async_playwright().start()
        self.browser = await create_browser(self.playwright)
        await self.redis.publish(self.progress_channel, "data: COUNT=30")
        await self.redis.publish(self.progress_channel, f"Браузер запущен")
        context = await self.browser.new_context()
        await context.set_extra_http_headers(BROWSER_HEADERS)
        if not os.path.exists(cookie_file):
            self.page = await context.new_page()
            await self.redis.publish(self.progress_channel, f"Нет COOKIE файла")
            await self.authorization()
            await self.page.close()
        else:
            await self.redis.publish(self.progress_channel, f"COOKIE файл присутствует")
        with open(cookie_file, "r") as file:
            storage_state = json.load(file)
        await context.add_cookies(storage_state["cookies"])
        self.page = await context.new_page()
        await stealth_async(self.page)

    @staticmethod
    async def store_results(soup: BeautifulSoup, session: AsyncSession) -> list:
        result = list()
        content_list = soup.find_all("div", class_="ty-product-block ty-compact-list__content")
        for line in content_list:
            keys = ["origin", "title", "link", "shipment", "warranty", "input_price", "pic", "optional"]
            data_item = dict.fromkeys(keys, '')
            if (code_block := line.find("div", class_="code")) and (span_element := code_block.find("span")):
                origin = span_element.get_text()
                if origin.isdigit():
                    data_item["origin"] = int(origin) or None
            if code_block := line.find("div", class_="category-list-item__title ty-compact-list__title"):
                data_item["title"] = code_block.a.get_text().strip() or None
                data_item["link"] = code_block.a.get('href') or ''
            if code_block := line.find("p", class_="delivery"):
                data_item["shipment"] = code_block.get_text().strip() or ''
            if (code_block := line.find("div", class_="divisible-block")) and (span_element := code_block.find("span")):
                data_item["warranty"] = span_element.get_text().strip() or ''
            if code_block := line.find("span", class_="ty-price-num", id=lambda x: x and "sec_discounted_price" in x):
                data_item["input_price"] = float(code_block.get_text().replace("\xa0", "")) or 0
            if code_block := line.find("div", class_="swiper-slide"):
                data_item["pic"] = code_block.a.get('href') or ''
            if (code_block := line.find("div", class_="code")) and (sub_div := code_block.find_next_sibling("div")):
                data_item["optional"] = sub_div.get_text().strip() or ''
            result.append(data_item)
        await save_harvest(session=session, data=result)
        return result

    @staticmethod
    def actual_pagination(soup: BeautifulSoup) -> list:
        pagination = soup.find('ul', {'class': 'pagination'})
        pages = list()
        if not pagination:
            return pages
        for li in pagination.find_all('li'):
            link = li.find('a')
            if link and link.getText().strip() not in ["Предыдущая", "Следующая"] and "active" not in li.get("class",
                                                                                                             []):
                pages.append(li)
        return pages

    async def process(self) -> dict:
        opened_page = await open_page(page=self.page, url=self.url)
        self.pages = self.actual_pagination(opened_page['soup'])
        if code_block := opened_page['soup'].find("div",
                                                  class_="ty-breadcrumbs clearfix breadcrumb user-logged-margin"):
            span = code_block.find_all('span')
            self.category = span[-1].get_text().strip() or ''
        await self.redis.publish(self.progress_channel, f"{len(self.pages) - 1} страниц для сбора информации")
        if not await self.check_auth(text=opened_page['soup']):
            context = await self.browser.new_context()
            await self.redis.publish(self.progress_channel, "Авторизация не пройдена")
            await self.authorization()
            await self.page.close()
            with open(cookie_file, "r") as file:
                storage_state = json.load(file)
            await context.add_cookies(storage_state["cookies"])
            self.page = await context.new_page()
            await stealth_async(self.page)
            opened_page = await open_page(page=self.page, url=self.url)
        result = await self.store_results(soup=opened_page['soup'], session=self.session)
        await self.redis.publish(self.progress_channel, f"Страница 1 из {len(self.pages) + 1} сохранена")
        page_counter = 0
        while page_counter < len(self.pages):
            await self.redis.publish(self.progress_channel, f"data: COUNT={len(self.pages) + 5}")
            page_item = self.pages[page_counter]
            next_url = page_item.a.get('href')
            opened_page = await open_page(page=self.page, url=next_url)
            result += await self.store_results(soup=opened_page['soup'], session=self.session)
            page_counter += 1
            await self.redis.publish(self.progress_channel,
                                     f"Страница {page_counter} из {len(self.pages) + 1} сохранена")
            new_pages = self.actual_pagination(opened_page['soup'])
            if len(new_pages) > len(self.pages):
                self.pages = new_pages
                await self.redis.publish(self.progress_channel, f"data: COUNT={len(self.pages) + 5}")
        return {'category': self.category, 'datetime_now': datetime.now(), 'data': result}


async def parsing_logic(progress_channel: str, redis: Redis, url: str, vendor: Vendor, session: AsyncSession) -> dict:
    pars_obj = FetchParse(progress_channel, redis, url, vendor, session)
    await pars_obj.run()
    try:
        data: dict = await pars_obj.process()
    finally:
        await pars_obj.browser.close()
        await pars_obj.playwright.stop()
    return data
