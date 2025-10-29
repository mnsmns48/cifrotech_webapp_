from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Column, Select, Button
from aiogram_dialog.widgets.text import Const, Format

from bot.user.callback import on_menu_click, on_back_click, go_to_prev_page, go_to_next_page
from bot.user.getter import main_menu_getter, walking_dirs_getter, hub_items_getter
from bot.user.state import UserMainMenu

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
