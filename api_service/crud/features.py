from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas import HubLevelPath
from api_service.schemas.features import FeaturesDataSet, FeaturesElement
from api_service.schemas.product_schemas import BrandModel, TypeModel
from models import ProductFeaturesGlobal, ProductBrand, ProductType, HUbMenuLevel
from models.product_dependencies import ProductFeaturesHubMenuLevelLink


async def features_hub_level_link_fetch_db(session: AsyncSession) -> FeaturesDataSet:
    stmt = (select(ProductFeaturesGlobal.id.label("feature_id"),
                   ProductFeaturesGlobal.title.label("feature_title"),

                   ProductBrand.id.label("brand_id"),
                   ProductBrand.brand.label("brand_name"),

                   ProductType.id.label("type_id"),
                   ProductType.type.label("type_name"),

                   HUbMenuLevel.id.label("level_id"),
                   HUbMenuLevel.label.label("level_label"),
                   )
            .join(ProductBrand, ProductBrand.id == ProductFeaturesGlobal.brand_id)
            .join(ProductType, ProductType.id == ProductFeaturesGlobal.type_id)
            .outerjoin(
        ProductFeaturesHubMenuLevelLink,
        ProductFeaturesHubMenuLevelLink.feature_id == ProductFeaturesGlobal.id
    )
            .outerjoin(
        HUbMenuLevel,
        HUbMenuLevel.id == ProductFeaturesHubMenuLevelLink.hub_level_id
    )
            .order_by(ProductType.id, ProductBrand.brand, ProductFeaturesGlobal.title)
            )

    result = await session.execute(stmt)
    rows = result.mappings().all()

    features = list()

    for row in rows:
        hub_level = None
        if row["level_id"] is not None:
            hub_level = HubLevelPath(
                path_id=row["level_id"],
                label=row["level_label"]
            )

        features.append(
            FeaturesElement(
                id=row["feature_id"],
                title=row["feature_title"],
                brand=BrandModel(
                    id=row["brand_id"],
                    brand=row["brand_name"]
                ),
                type=TypeModel(
                    id=row["type_id"],
                    type=row["type_name"]
                ),
                hub_level=hub_level
            )
        )

    return FeaturesDataSet(features=features)
