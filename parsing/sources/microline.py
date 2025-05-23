import asyncio
import json
import os

from bs4 import BeautifulSoup
from playwright.async_api import Browser, Page
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import save_harvest
from config import BASE_DIR
from models import Vendor
from parsing.browser import open_page

this_file_name = os.path.basename(__file__).rsplit('.', 1)[0]


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


async def registration(page: Page, vendor: Vendor, url: str):
    await page.goto('https://technosuccess.ru/login')
    await page.fill("#login_main_login", vendor.login)
    await page.fill("#psw_main_login", vendor.password)
    await page.check("#remember_me_main_login")
    buttons = await page.locator('button[name="dispatch[auth.login]"]').all()
    await buttons[1].click()
    await page.wait_for_load_state("domcontentloaded")
    await page.goto(url + '&sort_by=price&sort_order=asc&items_per_page=120')
    storage_state = await page.context.storage_state()
    with open(f"{BASE_DIR}/parsing/sources/{this_file_name}.json", "w") as file:
        json.dump(storage_state, file)
    return True


async def processing_page(page: Page, url, vendor_id: int, redis: Redis, progress_channel: str, session: AsyncSession):
    content = list()
    html_body = await open_page(page=page, url=url)
    soup = BeautifulSoup(markup=html_body['response'], features='lxml')
    pagination = soup.find('ul', {'class': 'pagination'})
    pages = pagination.find_all('li')
    current_page = 1
    content_list = soup.find_all("div", class_="ty-product-block ty-compact-list__content")
    page_data = await search_content(content_list, vendor_id)
    content = page_data
    await redis.publish(progress_channel, f"data: Обработана {current_page} из {len(pages)} страниц")
    if len(pages) > 1:
        for i in pages[1:]:
            await page.goto(i.find('a').get('href'))
            page_data = await search_content(content_list, vendor_id)
            content += page_data
            await redis.publish(progress_channel, f"data: Обработана {current_page} из {len(pages)} страниц")
            await asyncio.sleep(1)
            current_page += 1
    await save_harvest(session=session, data=content)


async def search_content(content_list: list, vendor_id: int) -> list:
    content = list()
    for line in content_list:
        keys = ["origin", "vendor_id", "title", "link", "shipment", "warranty", "input_price", "pic", "optional"]
        data_item = dict.fromkeys(keys, '')
        data_item["vendor_id"] = vendor_id
        if (code_block := line.find("div", class_="code")) and (span_element := code_block.find("span")):
            origin = span_element.get_text()
            if origin.isdigit():
                data_item["origin"] = int(origin) or None
        if code_block := line.find("div", class_="category-list-item__title ty-compact-list__title"):
            data_item["title"] = code_block.a.get_text() or None
            data_item["link"] = code_block.a.get('href') or ''
        if code_block := line.find("p", class_="delivery"):
            data_item["shipment"] = code_block.get_text() or ''
        if (code_block := line.find("div", class_="divisible-block")) and (span_element := code_block.find("span")):
            data_item["warranty"] = span_element.get_text() or ''
        if code_block := line.find("span", class_="ty-price-num", id=lambda x: x and "sec_discounted_price" in x):
            data_item["input_price"] = float(code_block.get_text().replace("\xa0", "")) or 0
        if code_block := line.find("div", class_="swiper-slide"):
            data_item["pic"] = code_block.a.get('href') or ''
        if (code_block := line.find("div", class_="code")) and (sub_div := code_block.find_next_sibling("div")):
            data_item["optional"] = sub_div.get_text().strip() or ''
        content.append(data_item)
    return content


async def main_parsing(browser: Browser,
                       page: Page,
                       progress_channel: str,
                       redis: Redis,
                       url: str,
                       vendor: Vendor,
                       session: AsyncSession):
    cookie_file = f"{BASE_DIR}/parsing/sources/{this_file_name}.json"
    html_body = await open_page(page=page, url=url)
    await redis.publish(progress_channel, "data: COUNT=15")
    await redis.publish(progress_channel, "data: Открываю страницу")
    if html_body.get('is_ok'):
        soup = BeautifulSoup(markup=html_body['response'], features='lxml')
        check = await check_auth(text=soup)
        await redis.publish(progress_channel, "data: Проверяю авторизацию")
        if not check:
            if not os.path.exists(cookie_file):
                await redis.publish(progress_channel, "data: Файл COOKIE отсутствует")
                await registration(page, vendor, url)
                await redis.publish(progress_channel, "data: Ввожу логин и пароль")
    with open(cookie_file, "r") as file:
        storage_state = json.load(file)
    await page.close()
    context = await browser.new_context()
    await context.add_cookies(storage_state["cookies"])
    await redis.publish(progress_channel, "data: Добавил куки в браузер")
    await redis.publish(progress_channel, "data: Авторизировался")
    page = await context.new_page()
    await processing_page(page=page,
                          url=url,
                          vendor_id=vendor.id,
                          redis=redis,
                          progress_channel=progress_channel,
                          session=session)
