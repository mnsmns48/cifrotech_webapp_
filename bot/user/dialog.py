from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Column, Select, Button
from aiogram_dialog.widgets.text import Const, Format

from bot.user.callback import on_menu_click, on_back_click
from bot.user.getter import main_menu_getter, walking_dirs_getter, hub_items_getter
from bot.user.state import UserMainMenu


async def go_to_prev_page(c: CallbackQuery, widget: Any, dialog_manager: DialogManager):
    page = dialog_manager.dialog_data.get("page", 0)
    if page > 0:
        dialog_manager.dialog_data["page"] = page - 1
        await dialog_manager.update({})


async def go_to_next_page(c: CallbackQuery, widget: Any, dialog_manager: DialogManager):
    page = dialog_manager.dialog_data.get("page", 0)
    total = dialog_manager.dialog_data.get("pages_total", 1)
    if page < total - 1:
        dialog_manager.dialog_data["page"] = page + 1
        await dialog_manager.update({})


main_hubstock_dialog = Dialog(
    Window(
        Const("Главная страница"),
        Column(
            Select(
                id="main_menu",
                items="main",
                item_id_getter=lambda item: str(item.id),
                text=Format("{item.label}"),
                on_click=on_menu_click,
            ),
        ),
        state=UserMainMenu.start,
        parse_mode="HTML",
        getter=main_menu_getter
    ),
    Window(
        Format("{breadcrumb}"),
        Column(
            Select(
                id="menu",
                items="levels",
                item_id_getter=lambda item: str(item.id),
                text=Format("{item.label}"),
                on_click=on_menu_click,
                when='levels'
            ),
            Button(
                Const("← Назад"),
                id="custom_back",
                on_click=on_back_click,
                when="back"
            )
        ),
        state=UserMainMenu.walking_dir,
        getter=walking_dirs_getter
    ),
    Window(
        Format("{breadcrumb}\n"),
        Format("{updated}"),
        Format("{items_text}", when="items_text"),
        Format("{page_text}", when="long_msg"),
        Column(
            Button(Format("Предыдущие ◀"), id="page_prev", on_click=go_to_prev_page, when="long_msg"),
            Button(Format("Ещё ▶"), id="page_next", on_click=go_to_next_page, when="long_msg"),
            Button(Const("← Назад к меню"), id="custom_back", on_click=on_back_click, when="back"),
        ),
        state=UserMainMenu.hub_items,
        parse_mode="HTML",
        getter=hub_items_getter
    )
)
