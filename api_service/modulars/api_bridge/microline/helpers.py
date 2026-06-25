from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select, delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.schemas import RewardRangeLineSchema
from models import ProductBrand, ProductOrigin, RewardRange, ParsingLine, VendorSearchLine
from parsing.utils import cost_process


def normalize_product_brands(products):
    for product in products:
        if product.brand:
            product.brand = product.brand.lower().strip()


def build_vsl_brands_map(linked_vsl):
    result = dict()

    for vsl in linked_vsl:
        if not vsl.brands:
            result[vsl.id] = None
            continue

        brands = [b.brand.lower().strip() for b in vsl.brands if b.brand]
        result[vsl.id] = brands or None

    return result


async def sync_product_brands(session: AsyncSession, raw_products, vsl_brands_map, linked_vsl):
    need_insert = any(vsl_brands_map[vsl.id] is None for vsl in linked_vsl)

    if not need_insert:
        return

    raw_brands = {p.brand.lower().strip() for p in raw_products if p.brand}

    if not raw_brands:
        return

    existing = (await session.execute(select(ProductBrand.brand))).scalars().all()
    existing_set = {b.lower() for b in existing}

    new_brands = [{"brand": brand} for brand in raw_brands if brand not in existing_set]

    if new_brands:
        await session.execute(insert(ProductBrand), new_brands)


def build_vsl_products(raw_products, linked_vsl, vsl_brands_map):
    result = defaultdict(list)

    for vsl in linked_vsl:
        allowed = vsl_brands_map[vsl.id]
        if allowed is None:
            result[vsl.id].extend(raw_products)
            continue
        allowed_set = set(allowed)

        for product in raw_products:
            brand = product.brand

            if brand is None:
                result[vsl.id].append(product)
                continue

            if brand in allowed_set:
                result[vsl.id].append(product)

    return result


def collect_needed_origins(vsl_products):
    origins = set()

    for products in vsl_products.values():
        for product in products:
            if not product.productCode:
                continue

            origins.add(int(product.productCode))

    return origins


async def sync_product_origins(session: AsyncSession, needed_origins: set[int], raw_products):
    existing = (
        await session.execute(select(ProductOrigin).where(ProductOrigin.origin.in_(needed_origins)))).scalars().all()

    existing_map = {o.origin: o for o in existing}

    missing = list()
    deleted = set()

    for origin in needed_origins:
        obj = existing_map.get(origin)

        if obj is None:
            missing.append(origin)
        elif obj.is_deleted:
            deleted.add(origin)

    if missing:
        name_map = {int(p.productCode): p.name for p in raw_products if p.productCode}

        rows = [{"origin": origin,
                 "title": name_map.get(origin),
                 "link": None,
                 "pics": None,
                 "preview": None,
                 "is_deleted": False} for origin in missing]

        await session.execute(insert(ProductOrigin), rows)

    return deleted


async def get_default_reward_lines(session):
    reward_range = (
        await session.execute(select(RewardRange).where(RewardRange.is_default.is_(True))
        .options(
            selectinload(RewardRange.lines)))).scalar_one()

    reward_lines = [RewardRangeLineSchema.model_validate(line) for line in reward_range.lines]
    return reward_lines, reward_range.id


async def rebuild_parsing_lines(session, linked_vsl, vsl_products, deleted_origins, reward_lines, reward_range_id):
    total_inserted = 0

    for vsl in linked_vsl:

        await session.execute(delete(ParsingLine).where(ParsingLine.vsl_id == vsl.id))

        rows = build_parsing_rows(products=vsl_products[vsl.id], vsl_id=vsl.id,
                                  deleted_origins=deleted_origins, reward_lines=reward_lines,
                                  reward_range_id=reward_range_id)

        if rows:
            await session.execute(insert(ParsingLine), rows)
            total_inserted += len(rows)

        await session.execute(update(VendorSearchLine).where(VendorSearchLine.id == vsl.id)
                              .values(dt_parsed=datetime.now(timezone.utc)))

    return total_inserted


def build_parsing_rows(products, vsl_id, deleted_origins, reward_lines, reward_range_id):
    rows = list()
    seen_origins = set()

    for product in products:

        if not product.productCode:
            continue

        origin = int(product.productCode)

        if origin in deleted_origins:
            continue

        if origin in seen_origins:
            continue

        seen_origins.add(origin)

        rows.append({"vsl_id": vsl_id,
                     "origin": origin,
                     "shipment": product.delivery,
                     "warranty": None,
                     "input_price": product.price,
                     "output_price": cost_process(product.price, reward_lines),
                     "optional": f"{int(product.amount)} шт",
                     "profit_range_id": reward_range_id})

    return rows
