from aiogram.types import Update
from fastapi import APIRouter, Request

from bot.bot_main import bot, dp

bot_fastapi_router = APIRouter()


@bot_fastapi_router.post("/webhook")
async def webhook(request: Request) -> None:
    print('update')
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
