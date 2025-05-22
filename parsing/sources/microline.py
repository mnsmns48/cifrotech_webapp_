import asyncio
import json
import os

from bs4 import BeautifulSoup
from playwright.async_api import Browser, Page
from redis.asyncio import Redis

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


async def search_content(page: Page, url):
    html_body = await open_page(page=page, url=url)



async def main_parsing(browser: Browser, page: Page, progress_channel: str, redis: Redis, url: str, vendor: Vendor):
    cookie_file = f"{BASE_DIR}/parsing/sources/{this_file_name}.json"
    html_body = await open_page(page=page, url=url)
    await redis.publish(progress_channel, "data: COUNT=60")
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
    await search_content(page=page, url=url)