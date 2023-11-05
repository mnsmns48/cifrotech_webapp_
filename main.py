import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from core.views import dir_router
from page_views import pages_router

app = FastAPI()
app.include_router(pages_router, tags=["pages_views"])
app.include_router(dir_router, prefix="/dirs", tags=["swagger_views"])
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/photo", StaticFiles(directory="C:/Users/WP/YandexDisk/photo"), name="photo")

if __name__ == "__main__":
    uvicorn.run("main:app")
