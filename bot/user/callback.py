from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Select, Button

from bot.user.state import UserMainMenu


async def on_menu_click(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    manager.dialog_data["history"] = [int(item_id)]
    manager.dialog_data["parent_id"] = int(item_id)
    await manager.switch_to(UserMainMenu.start, show_mode=ShowMode.EDIT)


async def on_back_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    manager.dialog_data["parent_id"] = 1
    await manager.switch_to(UserMainMenu.start, show_mode=ShowMode.EDIT)
