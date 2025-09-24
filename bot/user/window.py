from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Select, Back, Column
from aiogram_dialog.widgets.text import Const, Format

from bot.user.callback import on_menu_click, on_back_click
from bot.user.getter import menu_getter
from bot.user.state import UserMainMenu

user_hubstock_window = Window(
    Const("-"),
    Column(
        Select(
            id="menu_select",
            items="levels",
            item_id_getter=lambda item: str(item.id),
            text=Format("{item.label}"),
            on_click=on_menu_click,
        ),
        Back(Const("← Назад"), on_click=on_back_click)
    ),
    state=UserMainMenu.start,
    getter=menu_getter,
)
