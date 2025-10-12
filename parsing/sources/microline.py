import asyncio
import json
import os
import re
from typing import List, Set, Tuple, Optional, Dict

from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from playwright_stealth import stealth_async
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from api_service.schemas import ParsingLinesIn
from app_utils import safe_int, normalize_pages_list, compute_html_hash, count_message

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
        cookie_note = self.page.locator("#cookie_note")
        if await cookie_note.is_visible():
            accept_button = cookie_note.locator("button.cookie_accept")
            if await accept_button.is_visible():
                await accept_button.click()
                await self.redis.publish(self.progress, "Нажали 'Принять' в cookie-уведомлении")
        await asyncio.sleep(0.5)
        await self.redis.publish(self.progress, f"Авторизируюсь")
        await self.page.fill("#login_main_login", self.vendor.login)
        await self.page.fill("#psw_main_login", self.vendor.password)
        await self.page.locator(".ty-login__remember-me input[type='checkbox']").nth(1).check()
        await self.page.locator(".cm-field-container.ty-clear-both input[type='checkbox']").nth(1).check()
        await asyncio.sleep(0.5)
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
        await self.redis.publish(self.progress, "data: COUNT=50")
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
    def collect_pagination_candidates(
            soup: BeautifulSoup,
            current_number: Optional[int],
            visited: Set[int],
            skip_btn_class: str = "ty-pagination__btn"
    ) -> Tuple[List[Tuple[int, str]], int]:

        pagination = soup.find("ul", class_="pagination")
        if pagination is None:
            return [], 0

        next_candidates: List[Tuple[int, str]] = []
        dom_max = 0

        anchors = pagination.find_all("a", attrs={"data-ca-page": True})
        for a in anchors:
            classes = a.get("class")
            if classes is None:
                classes = []

            skip = False
            for cls in classes:
                if skip_btn_class in cls:
                    skip = True
                    break
            if skip:
                continue

            page_val = a.get("data-ca-page")
            page_num = safe_int(page_val)

            if page_num is None:
                try:
                    text = a.get_text(strip=True)
                    match = re.search(r"(\d+)", text)
                    if match is not None:
                        page_num = safe_int(match.group(1))
                except (AttributeError, TypeError, ValueError):
                    page_num = None

            if page_num is None:
                continue

            if page_num > dom_max:
                dom_max = page_num

            if current_number is not None and page_num == current_number:
                continue

            if page_num in visited:
                continue

            href = a.get("href")
            next_candidates.append((page_num, href))

        seen: Dict[int, str] = {}
        filtered: List[Tuple[int, str]] = []

        for pair in next_candidates:
            page, href = pair
            if page not in seen:
                seen[page] = href
                if href is None:
                    href = ""
                filtered.append((page, href))

        return filtered, dom_max

    @staticmethod
    def actual_pagination(soup: BeautifulSoup) -> List[int]:
        pages: List[int] = []
        pagination = soup.find("ul", class_="pagination")
        if not pagination:
            return pages
        for li in pagination.find_all("li"):
            a = li.find("a", attrs={"data-ca-page": True})
            if a:
                val = a.get("data-ca-page") or a.get_text()
            else:
                span = li.find("span")
                val = span.get_text() if span else li.get_text()
            if not val:
                continue

            s = str(val).strip()
            m = re.search(r"(\d+)", s)
            if not m:
                continue
            try:
                num = int(m.group(1))
                if num > 0:
                    pages.append(num)
            except ValueError:
                continue

        pages = sorted(set(pages))
        return pages

    @staticmethod
    def determine_current_number_from_soup(soup: BeautifulSoup) -> Optional[int]:
        li = soup.find("li", class_="ty-pagination__selected")
        if li:
            text = li.get_text(strip=True)
            return safe_int(text)
        li2 = soup.find("li", class_="active")
        if li2:
            text = li2.get_text(strip=True)
            return safe_int(text)
        return None

    @staticmethod
    def determine_current_number_from_url(url: str) -> Optional[int]:
        if not url:
            return None
        m = re.search(r"(?:page[-=])(\d+)", url)
        if m:
            return safe_int(m.group(1))
        return None

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

                parsing_lines_result.append(ParsingLinesIn(
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
                    in_hub=origin in hubstock_origins)
                )
            except (AttributeError, ValueError, TypeError, IndexError, ValidationError):
                continue

        return parsing_lines_result

    async def authorize_and_restore_page(self) -> BeautifulSoup:
        await self.redis.publish(self.progress, "Авторизация не пройдена, начинаю восстановление сессии")
        await self.authorization()
        await self.page.close()
        context = await self.browser.new_context()
        try:
            with open(cookie_file, "r") as file:
                storage_state = json.load(file)
            await context.add_cookies(storage_state["cookies"])
        except Exception as cookie_error:
            await self.redis.publish(self.progress, f"Ошибка загрузки cookies: {str(cookie_error)}")
        self.page = await context.new_page()
        await stealth_async(self.page)
        await self.redis.publish(self.progress, "Сессия восстановлена, продолжаю парсинг")
        opened_page = await open_page(page=self.page, url=self.url)
        return opened_page['soup']

    async def get_parsed_lines(self) -> List[ParsingLinesIn]:
        result_lines: List[ParsingLinesIn] = []
        visited_pages: Set[int] = set()
        visited_hashes: Set[str] = set()
        safety_iter_limit = 150

        opened_page = await open_page(page=self.page, url=self.url)
        soup = opened_page["soup"]

        if not await self.check_auth(text=soup):
            soup = await self.authorize_and_restore_page()

        raw_pages = self.actual_pagination(soup)
        normalized_pages = normalize_pages_list(raw_pages)
        known_max_page = max(normalized_pages) if normalized_pages else 1
        await self.redis.publish(self.progress, count_message(known_max_page))
        self.pages = normalized_pages

        try:
            await self.page.goto(self.url, wait_until="domcontentloaded")
            await stealth_async(self.page)
        except PlaywrightError as e:
            await self.redis.publish(self.progress, f"Ошибка навигации на стартовый URL: {type(e).__name__}")
            return result_lines

        counter = 0

        while True:
            counter += 1
            if counter > safety_iter_limit:
                await self.redis.publish(self.progress, "Достигнут safety лимит итераций, остановка")
                break
            try:
                html = await self.page.locator("xpath=//body").inner_html()
                html_hash = compute_html_hash(html)
                if html_hash in visited_hashes:
                    await self.redis.publish(self.progress, "Повторяющийся контент обнаружен, завершение")
                    break
                soup = BeautifulSoup(html, "lxml")

                current_number: Optional[int] = self.determine_current_number_from_soup(soup)
                if current_number is None:
                    current_number = self.determine_current_number_from_url(self.page.url or "")
                if current_number is None:
                    current_number = max(visited_pages) if visited_pages else 0
                    await self.redis.publish(self.progress,
                                             f"Не найден li.active и page в URL, "
                                             f"используем опорный номер: {current_number}")

                if current_number in visited_pages:
                    await self.redis.publish(self.progress, f"Страница {current_number} уже посещена! STOP!")
                    break
                try:
                    lines = await self.page_data_separation(soup=soup, session=self.session)
                    result_lines.extend(lines)
                except (SQLAlchemyError, ConnectionError, TimeoutError, RuntimeError, TypeError, AttributeError) as e:
                    await self.redis.publish(self.progress, f"Ошибка при парсинге данных: {type(e).__name__}")
                    await asyncio.sleep(0.5)

                visited_pages.add(current_number)
                visited_hashes.add(html_hash)

                next_candidates, dom_max = self.collect_pagination_candidates(
                    soup=soup, current_number=current_number, visited=visited_pages
                )

                if dom_max > known_max_page:
                    known_max_page = dom_max
                    await self.redis.publish(self.progress, count_message(known_max_page))

                if not next_candidates:
                    await self.redis.publish(self.progress, "Нет новых страниц для перехода, "
                                                            "останавливаем парсер")
                    break

                forward_candidates = list()
                for pair in next_candidates:
                    page_num, href = pair
                    if page_num > current_number:
                        forward_candidates.append((page_num, href))

                if len(forward_candidates) == 0:
                    await self.redis.publish(self.progress, "Нет страниц с номером больше текущего, завершение")
                    break

                min_page = forward_candidates[0]
                for candidate in forward_candidates:
                    if candidate[0] < min_page[0]:
                        min_page = candidate

                next_page_num, next_href = min_page

                await self.redis.publish(self.progress, f"Текущий URL: {self.page.url}")

                locator = self.page.locator(f"ul.pagination a[data-ca-page='{next_page_num}']")
                count = await locator.count()

                if count == 0:
                    await self.redis.publish(self.progress,
                                             f"Элемент для перехода на страницу {next_page_num} "
                                             f"внутри pagination не найден")
                    await asyncio.sleep(0.5)
                    break

                click_success = False
                click_attempts = 0
                while click_attempts < 3 and not click_success:
                    try:
                        await locator.nth(0).click(timeout=9000)
                        try:
                            await self.page.wait_for_function(
                                """(prev) => {
                                    const el = document.querySelector('ul.pagination li.active span') || document.querySelector('ul.pagination li.active');
                                    if (!el) return false;
                                    return el.textContent.trim() !== String(prev);
                                }""",
                                arg=current_number or "",
                                timeout=8000
                            )
                            click_success = True

                        except PlaywrightTimeoutError:
                            new_html = await self.page.locator("xpath=//body").inner_html()
                            new_hash = compute_html_hash(new_html)
                            if new_hash not in visited_hashes:
                                click_success = True
                            else:
                                click_attempts += 1
                                await self.redis.publish(self.progress,
                                                         f"Переход не подтвердился, попытка {click_attempts}")
                                await asyncio.sleep(1 + click_attempts * 2)
                    except PlaywrightError as click_err:
                        click_attempts += 1
                        await self.redis.publish(self.progress,
                                                 f"Ошибка клика (попытка {click_attempts}): {type(click_err).__name__}")
                        await asyncio.sleep(1 + click_attempts * 2)

                if not click_success:
                    await self.redis.publish(self.progress,
                                             f"Не удалось перейти на страницу {next_page_num}, завершение")
                    break

            except PlaywrightError as unexpected_error:
                await self.redis.publish(self.progress,
                                         f"Непредвиденная ошибка Playwright: {type(unexpected_error).__name__}")
                await asyncio.sleep(1)
                break

        return result_lines

    # async def get_parsed_lines(self) -> List[ParsingLinesIn]:
    #     opened_page = await open_page(page=self.page, url=self.url)
    #     soup = opened_page['soup']
    #     self.pages = self.actual_pagination(soup)
    #     await self.redis.publish(self.progress, f"{len(self.pages) + 1} страниц для сбора информации")
    #     if not await self.check_auth(text=soup):
    #         await self.redis.publish(self.progress, "Авторизация не пройдена")
    #         await self.authorization()
    #         await self.page.close()
    #         context = await self.browser.new_context()
    #         with open(cookie_file, "r") as file:
    #             storage_state = json.load(file)
    #         await context.add_cookies(storage_state["cookies"])
    #         self.page = await context.new_page()
    #         await stealth_async(self.page)
    #         opened_page = await open_page(page=self.page, url=self.url)
    #         soup = opened_page['soup']
    #         self.pages = self.actual_pagination(soup)
    #
    #     visited_urls = set()
    #     urls_to_visit = [self.url] + [page.a.get("href") for page in self.pages if page.a]
    #
    #     result_lines: List[ParsingLinesIn] = list()
    #     page_counter = 1
    #
    #     while urls_to_visit:
    #         url = urls_to_visit.pop(0)
    #         if url in visited_urls:
    #             continue
    #         visited_urls.add(url)
    #
    #         opened_page = await open_page(page=self.page, url=url)
    #         soup = opened_page['soup']
    #         lines = await self.page_data_separation(soup=soup, session=self.session)
    #         result_lines.extend(lines)
    #
    #         await self.redis.publish(self.progress, f"Страница {page_counter} сохранена")
    #         page_counter += 1
    #
    #         new_pages = self.actual_pagination(soup)
    #         for page in new_pages:
    #             href = page.a.get("href") if page.a else None
    #             if href and href not in visited_urls and href not in urls_to_visit:
    #                 urls_to_visit.append(href)
    #
    #     return result_lines
