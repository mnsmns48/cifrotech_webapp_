from contextlib import asynccontextmanager
from starlette.staticfiles import StaticFiles
from api_v1.cifrotech_views import cifrotech_router
from typing import AsyncGenerator
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api_v2.api_v2_views import api_v2_router
from bot.bot_settings import bot_config, dp, bot
from bot.api import bot_fastapi_router
from cfg import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    current_webhook = await bot.get_webhook_info()
    expected_url = f"{bot_config.WEBHOOK_URL.get_secret_value()}/webhook"
    if current_webhook.url != expected_url:
        await bot.set_webhook(
            url=expected_url,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
    yield


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
    uvicorn.run("main:app", host='0.0.0.0', port=5000)
