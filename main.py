import logging

from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError
from aiogram_dialog import setup_dialogs
from fastapi_cache import FastAPICache, JsonCoder

from fastapi_cache.backends.redis import RedisBackend
from starlette.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_common.routers import general_router
from api_miniapp.routers import miniapp_router
from api_service.routers import service_router
from api_users.routers import auth_api_router
from api_v2.routers import api_v2_router
from bot.bot_main import bot_setup_webhook, bot_fastapi_router, bot, dp
from bot.crud_bot import get_option_value, add_bot_options
from config import settings, redis_session
from engine import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_dialogs(dp)
    try:
        redis = redis_session()
        FastAPICache.init(RedisBackend(redis), prefix="cache")
        logging.info("FastAPICache initialized")
        bot_username = await bot_setup_webhook()
        async with db.tg_session() as session:
            already_add = await get_option_value(session=session, username=bot_username, field='username')
            if not already_add:
                await add_bot_options(session=session, **{'username': bot_username})
        yield
    except (TelegramNetworkError, TelegramRetryAfter) as e:
        logging.error(f"Lifespan startup failed: {e}")
        yield
    finally:
        await bot.session.close()


app = FastAPI(lifespan=lifespan, docs_url=settings.api.docs_url)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   allow_credentials=True)

app.include_router(miniapp_router, tags=['Telegram Mini App'])
app.include_router(api_v2_router, tags=["Api V2"])
app.include_router(bot_fastapi_router, tags=["TG Bot Router"])
app.include_router(router=auth_api_router)
app.include_router(service_router)
app.include_router(general_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("aiobotocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)
    logging.getLogger("aiogram_dialog").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    uvicorn.run("main:app", host='0.0.0.0', port=5000)
