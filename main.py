import logging

from starlette.staticfiles import StaticFiles
from api_v1.cifrotech_views import cifrotech_router
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api_v2.api_v2_views import api_v2_router
from bot.bot_main import bot_setup_webhook, bot_fastapi_router, bot
from bot.core import get_option_value, add_bot_options
from cfg import settings
from engine import pg_engine
from models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_username = await bot_setup_webhook()
    async with pg_engine.engine.begin() as async_connect:
        await async_connect.run_sync(Base.metadata.create_all)
    async with pg_engine.tg_session() as session:
        already_add = await get_option_value(session=session, username=bot_username, field='username')
        if not already_add:
            await add_bot_options(session=session, **{'username': bot_username})
    try:
        yield
    finally:
        await bot.session.close()



app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware,
                   allow_origins=settings.cors,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   allow_credentials=True)

app.include_router(api_v2_router, tags=["Api_v2"])
app.include_router(bot_fastapi_router, tags=["TG Bot Router"])
# app.include_router(cifrotech_router, tags=["Api_v1"])
# app.mount("/static", StaticFiles(directory="static"), name="static")
# app.mount("/photo", StaticFiles(directory=settings.photo_path), name="photo")
# app.mount("/s/photo", StaticFiles(directory=settings.photo_path), name="photo")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    uvicorn.run("main:app", host='0.0.0.0', port=5000)
