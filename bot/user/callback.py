from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Select, Button

from bot.crud_bot import get_menu_levels
from bot.user.state import UserMainMenu


async def on_menu_click(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    walk_history = manager.dialog_data.get("walk_history", [1])
    walk_history.append(int(item_id))
    manager.dialog_data["walk_history"] = walk_history
    manager.dialog_data["parent_id"] = int(item_id)

    session = manager.middleware_data["session"]
    levels = await get_menu_levels(session, int(item_id))

    if levels:
        await manager.switch_to(UserMainMenu.walking_dir, show_mode=ShowMode.EDIT)
    else:
        await manager.switch_to(UserMainMenu.hub_items, show_mode=ShowMode.EDIT)


async def on_back_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    walk_history = manager.dialog_data.get("walk_history", [])
    if len(walk_history) > 1:
        walk_history.pop()
        parent_id = walk_history[-1]
        manager.dialog_data["walk_history"] = walk_history
        manager.dialog_data["parent_id"] = parent_id
        if parent_id == 1:
            await manager.switch_to(UserMainMenu.start, show_mode=ShowMode.EDIT)
        else:
            await manager.switch_to(UserMainMenu.walking_dir, show_mode=ShowMode.EDIT)
    else:
        manager.dialog_data["walk_history"] = [1]
        manager.dialog_data["parent_id"] = 1
        await manager.switch_to(UserMainMenu.start, show_mode=ShowMode.EDIT)


async def on_hub_item_click(callback: CallbackQuery, widget, manager: DialogManager, item_id: str):
    title, price = item_id.split(":", 1)
    await callback.answer(f"Вы выбрали: {title} — {price} ₽", show_alert=True)


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
