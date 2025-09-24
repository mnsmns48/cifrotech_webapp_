from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Column, Select, Back, Button
from aiogram_dialog.widgets.text import Const, Format

from bot.user.callback import on_menu_click, on_back_click, on_hub_item_click
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
        Format("{breadcrumb}\nОбновлено {updated}\n\n{items_text}"),
        Column(
            Button(
                Const("← Назад"),
                id="custom_back",
                on_click=on_back_click,
                when="back"
            )
        ),
        state=UserMainMenu.hub_items,
        getter=hub_items_getter
    )
)
