from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Select

from bot.user.state import UserMainMenu


async def on_menu_click(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str) -> None:
    manager.dialog_data["selected_level_id"] = int(item_id)
    await manager.start(UserMainMenu.start,
                        data={"parent_id": int(item_id), "session": manager.start_data["session"]},
                        mode=StartMode.NORMAL)
