from aiogram_dialog import DialogManager
from sqlalchemy.ext.asyncio import AsyncSession
from bot.crud_bot import get_menu_levels, get_labels_by_ids, get_hubstock_items


def make_breadcrumb(id_to_label: dict[int, str], walk_history: list) -> str:
    return " ➡️📁 ".join([id_to_label.get(i, f"[{i}]") for i in walk_history])


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
    MAX_MESSAGE_LENGTH = 3800
    page = dialog_manager.dialog_data.get("page", 0)

    parent_id = dialog_manager.dialog_data["parent_id"]
    walk_history = dialog_manager.dialog_data.get("walk_history", [1])
    hubstock_data = await get_hubstock_items(session, parent_id)
    id_to_label = await get_labels_by_ids(session, walk_history)
    breadcrumb = make_breadcrumb(id_to_label, walk_history)

    if hubstock_data and hubstock_data.groups:
        sorted_groups = sorted(hubstock_data.groups, key=lambda g: g.sort_order)

        group_blocks = []
        for group in sorted_groups:
            items_block = "\n".join(
                f"🔹{item.title}: <b><u>{int(item.price)}</u></b> ₽"
                for item in group.items
            )
            group_blocks.append(items_block)

        items_text = "\n\n".join(group_blocks)
        updated = (
            f"<blockquote>Обновлено {hubstock_data.most_common_updated_at}</blockquote>\n"
            if hubstock_data.most_common_updated_at else ""
        )
    else:
        items_text = "Тут пока пусто ➛ скоро всё появится"
        updated = ''

    if len(items_text) >= MAX_MESSAGE_LENGTH:
        text_bulk = []
        current_chunk = ""

        for part in items_text.split("🔹"):
            if len(current_chunk) + len(part) + 2 > MAX_MESSAGE_LENGTH:
                text_bulk.append(current_chunk.strip())
                current_chunk = ""
            current_chunk += ("🔹" + part)

        if current_chunk.strip():
            text_bulk.append(current_chunk.strip())

        dialog_manager.dialog_data["pages_total"] = len(text_bulk)

        return {
            "breadcrumb": breadcrumb,
            "updated": updated,
            "page_text": text_bulk[page],
            "page": page,
            "pages_total": len(text_bulk),
            "back": True,
            "long_msg": True
        }

    return {
        "items_text": items_text,
        "updated": updated,
        "breadcrumb": breadcrumb,
        "back": True
    }
