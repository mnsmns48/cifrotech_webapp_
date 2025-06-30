import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import get_range_rewards_list, store_harvest, store_harvest_line, get_rr_obj_id
from api_service.schemas import ParsingRequest, HarvestLineIn
from config import BROWSER_HEADERS, BASE_DIR
from models import Vendor
from parsing.browser import create_browser, open_page
from parsing.utils import cost_value_update

this_file_name = os.path.basename(__file__).rsplit('.', 1)[0]
cookie_file = f"{BASE_DIR}/parsing/sources/{this_file_name}.json"


class BaseParser:
    def __init__(self,
                 redis: Redis,
                 data: ParsingRequest,
                 vendor: Vendor,
                 session: AsyncSession):
        self.page, self.browser, self.playwright = None, None, None
        self.pages = list()
        self.redis = redis
        self.data = data
        self.vendor = vendor
        self.session = session
        self.range_id = int()

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
        await self.redis.publish(self.data.progress, f"Авторизируюсь")
        await self.page.fill("#login_main_login", self.vendor.login)
        await self.page.fill("#psw_main_login", self.vendor.password)
        await self.page.check("#remember_me_main_login")
        buttons = await self.page.locator('button[name="dispatch[auth.login]"]').all()
        await buttons[1].click()
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.goto(self.data.vsl_url + '&sort_by=price&sort_order=asc&items_per_page=120')
        storage_state = await self.page.context.storage_state()
        with open(f"{BASE_DIR}/parsing/sources/{this_file_name}.json", "w") as file:
            json.dump(storage_state, file)
        await self.redis.publish(self.data.progress, f"Авторизция прошла успешно")

    async def run(self):
        self.playwright = await async_playwright().start()
        self.browser = await create_browser(self.playwright)
        await self.redis.publish(self.data.progress, "data: COUNT=30")
        await self.redis.publish(self.data.progress, f"Браузер запущен")
        context = await self.browser.new_context()
        await context.set_extra_http_headers(BROWSER_HEADERS)
        if not os.path.exists(cookie_file):
            self.page = await context.new_page()
            await self.redis.publish(self.data.progress, f"Нет COOKIE файла")
            await self.authorization()
            await self.page.close()
        else:
            await self.redis.publish(self.data.progress, f"COOKIE файл присутствует")
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
    async def store_results(soup: BeautifulSoup, session: AsyncSession, harvest_id: int, range_id: int) -> list:
        parsing_lines_result = list()
        content_list = soup.find_all("div", class_="ty-product-block ty-compact-list__content")
        for line in content_list:
            keys = ["origin", "title", "link", "shipment", "warranty", "input_price", "pics", "preview", "optional",
                    "harvest_id"]
            data_item = dict.fromkeys(keys, '')
            if (code_block := line.find("div", class_="code")) and (span_element := code_block.find("span")):
                data_item["origin"] = span_element.get_text().strip() or None
            if code_block := line.find("div", class_="category-list-item__title ty-compact-list__title"):
                data_item["title"] = code_block.a.get_text().strip() or None
                data_item["link"] = code_block.a.get('href') or ''
            if code_block := line.find("p", class_="delivery"):
                data_item["shipment"] = code_block.get_text().strip() or ''
            if (code_block := line.find("div", class_="divisible-block")) and (span_element := code_block.find("span")):
                data_item["warranty"] = span_element.get_text().strip() or ''
            if code_block := line.find("span", class_="ty-price-num", id=lambda x: x and "sec_discounted_price" in x):
                data_item["input_price"] = float(code_block.get_text().replace("\xa0", "")) or 0
            if code_block := line.find("div", class_="swiper-wrapper"):
                data_item["pics"] = await BaseParser.extract_pic(code_block)
                data_item["preview"] = code_block.find('a').get('href')
            if (code_block := line.find("div", class_="code")) and (sub_div := code_block.find_next_sibling("div")):
                data_item["optional"] = sub_div.get_text().strip() or ''
            data_item["harvest_id"] = harvest_id
            parsing_lines_result.append(data_item)
        ranges = await get_range_rewards_list(session=session, range_id=range_id)
        raw_items = cost_value_update(parsing_lines_result, list(ranges))
        items = [HarvestLineIn.model_validate(d) for d in raw_items]
        parsing_lines_result = await store_harvest_line(session=session, items=items)
        return parsing_lines_result

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
        opened_page = await open_page(page=self.page, url=self.data.vsl_url)
        self.pages = self.actual_pagination(opened_page['soup'])
        category = ['Категория не определена']
        if code_block := (opened_page['soup']
                .find("div", class_="ty-breadcrumbs clearfix breadcrumb user-logged-margin")):
            span = code_block.find_all('span')
            category.clear()
            category = [s.get_text().strip() for s in span[1:] if s.find('a')]
        self.range_id: int = await get_rr_obj_id(session=self.session)
        harvest_data = {'vendor_search_line_id': self.data.vsl_id, 'category': category, 'range_id': self.range_id}
        harvest_id = await store_harvest(data=harvest_data, session=self.session)
        await self.redis.publish(self.data.progress, f"Данные о парсинге сохранены")
        await self.redis.publish(self.data.progress, f"{len(self.pages) - 1} страниц для сбора информации")
        if not await self.check_auth(text=opened_page['soup']):
            context = await self.browser.new_context()
            await self.redis.publish(self.data.progress, "Авторизация не пройдена")
            await self.authorization()
            await self.page.close()
            with open(cookie_file, "r") as file:
                storage_state = json.load(file)
            await context.add_cookies(storage_state["cookies"])
            self.page = await context.new_page()
            await stealth_async(self.page)
            opened_page = await open_page(page=self.page, url=self.data.vsl_url)
        result = await self.store_results(soup=opened_page['soup'],
                                          session=self.session,
                                          harvest_id=harvest_id,
                                          range_id=self.range_id)
        await self.redis.publish(self.data.progress, f"Страница 1 из {len(self.pages) + 1} сохранена")
        page_counter = 0
        while page_counter < len(self.pages):
            await self.redis.publish(self.data.progress, f"data: COUNT={len(self.pages) + 5}")
            page_item = self.pages[page_counter]
            next_url = page_item.a.get('href')
            opened_page = await open_page(page=self.page, url=next_url)
            result += await self.store_results(soup=opened_page['soup'],
                                               session=self.session,
                                               harvest_id=harvest_id,
                                               range_id=self.range_id)
            page_counter += 1
            await self.redis.publish(self.data.progress,
                                     f"Страница {page_counter} из {len(self.pages) + 1} сохранена")
            new_pages = self.actual_pagination(opened_page['soup'])
            if len(new_pages) > len(self.pages):
                self.pages = new_pages
                await self.redis.publish(self.data.progress, f"data: COUNT={len(self.pages) + 5}")
        return {'category': category, 'datestamp': datetime.now(), 'data': result, 'range_id': self.range_id}
                                                #нужно range отдавать как словарь из id и названия
