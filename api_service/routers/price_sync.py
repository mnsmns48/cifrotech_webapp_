from typing import List

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.price_sync.service import PriceSync
from api_service.s3_helper import get_s3_client
from api_service.schemas import PriceSyncPickedPath, PathIdRequest, SyncPathWOrigins, UpdateMarketSettingsRequest, \
    StockHubItemResult
from api_service.schemas.price_sync_schemas import SyncPathWModels, SyncPathWMarket, HubStockUpdateSyncPathItem

from engine import db

price_sync_router = APIRouter(tags=['Price Sync'])


@price_sync_router.post("/start_price_sync_process", response_model=List[PriceSyncPickedPath])
async def start_price_sync_process(payload: PathIdRequest,
                                   session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await PriceSync.start_sync_process(payload, session)


@price_sync_router.post("/fetch_raw_origins", response_model=List[SyncPathWOrigins])
async def fetch_raw_origins(payload: List[PriceSyncPickedPath],
                            session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await PriceSync.fetch_raw_origins(payload, session)


@price_sync_router.post("/resolve_models_for_sync", response_model=List[SyncPathWModels])
async def resolve_models_for_sync(payload: List[PriceSyncPickedPath],
                                  session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await PriceSync.resolve_models_sync(payload, session)


@price_sync_router.post("/approve_origins_for_update", response_model=List[SyncPathWMarket])
async def approve_origins_for_update(payload: List[SyncPathWModels],
                                     s3_client=Depends(get_s3_client),
                                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await PriceSync.approve_origins_for_update(payload, session, s3_client)


@price_sync_router.post("/update_market_param", response_model=List[SyncPathWMarket])
async def update_market_param(payload: UpdateMarketSettingsRequest,
                              session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await PriceSync.update_market_param(payload, session)


@price_sync_router.post("/update_origins_in_hubstock", response_model=List[StockHubItemResult])
async def update_origins_in_hubstock(payload: List[HubStockUpdateSyncPathItem],
                                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await PriceSync.update_origins_in_hubstock(payload, session)
