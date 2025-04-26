import logging
from starlette.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_service.aservice_views import service_router
from api_service.handlers import register_service_handlers
from api_users.routers import auth_api_router
from api_v2.routers import api_v2_router
from bot.bot_main import bot_setup_webhook, bot_fastapi_router, bot
from bot.crud_bot import get_option_value, add_bot_options
from config import settings
from engine import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_username = await bot_setup_webhook()
    async with db.tg_session() as session:
        already_add = await get_option_value(session=session, username=bot_username, field='username')
        if not already_add:
            await add_bot_options(session=session, **{'username': bot_username})
    try:
        yield
    finally:
        await bot.session.close()


# app = FastAPI(lifespan=lifespan, docs_url=settings.api.docs_url)
app = FastAPI(docs_url=settings.api.docs_url)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   allow_credentials=True)

app.include_router(api_v2_router, tags=["Api V2"])
app.include_router(bot_fastapi_router, tags=["TG Bot Router"])
app.include_router(router=auth_api_router)
app.include_router(service_router, tags=["Service"])
app.mount("/static", StaticFiles(directory="static"), name="static")

register_service_handlers(app)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    uvicorn.run("main:app", host='0.0.0.0', port=5000)
