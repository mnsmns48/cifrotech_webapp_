from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Select, Button

from bot.user.state import UserMainMenu


async def on_menu_click(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    walk_history = manager.dialog_data.get("walk_history")
    if not walk_history:
        walk_history = [1]
    walk_history.append(int(item_id))
    manager.dialog_data["walk_history"] = walk_history
    manager.dialog_data["parent_id"] = int(item_id)

    await manager.switch_to(UserMainMenu.walking_dir, show_mode=ShowMode.EDIT)


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
