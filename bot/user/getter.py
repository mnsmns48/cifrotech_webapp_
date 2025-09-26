from aiogram_dialog import DialogManager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.crud_bot import get_menu_levels, get_labels_by_ids, get_hubstock_items


def make_breadcrumb(id_to_label: dict[int, str], walk_history: list) -> str:
    return "  >  ".join([id_to_label.get(i, f"[{i}]") for i in walk_history])


async def main_menu_getter(dialog_manager: DialogManager, session: AsyncSession, **kwargs):
    if "walk_history" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["walk_history"] = [1]
        dialog_manager.dialog_data["parent_id"] = 1
    main = await get_menu_levels(session, 1)

    return {"main": main, 'last_path_level': False, 'back': False}


async def walking_dirs_getter(dialog_manager: DialogManager, session: AsyncSession, **kwargs):
    parent_id = dialog_manager.dialog_data["parent_id"]
    walk_history = dialog_manager.dialog_data.get("walk_history", [1])
    levels = await get_menu_levels(session, int(parent_id))
    if levels:
        id_to_label = await get_labels_by_ids(session, walk_history)
        breadcrumb = make_breadcrumb(id_to_label, walk_history)
        return {"levels": levels, "breadcrumb": breadcrumb, "back": True}

    return None


async def hub_items_getter(dialog_manager: DialogManager, session: AsyncSession, **kwargs):
    parent_id = dialog_manager.dialog_data["parent_id"]
    walk_history = dialog_manager.dialog_data.get("walk_history", [1])
    hubstock_data = await get_hubstock_items(session, parent_id)
    id_to_label = await get_labels_by_ids(session, walk_history)
    breadcrumb = make_breadcrumb(id_to_label, walk_history)

    items_text = "\n".join(
        f"{item.title}:  {int(item.price)} ₽" for item in hubstock_data.items
    ) if hubstock_data.items else "Нет доступных элементов."

    updated = f"Обновлено {hubstock_data.most_common_updated_at}\n\n" if hubstock_data.most_common_updated_at else ' '

    return {
        "items_text": items_text,
        "updated": updated,
        "breadcrumb": breadcrumb,
        "back": True
    }
