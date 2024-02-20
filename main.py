import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from page_views import pages_router
from cfg import settings

app = FastAPI()
app.include_router(pages_router, tags=["pages_views"])
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/photo", StaticFiles(directory=settings.photo_path), name="photo")
app.mount("/s/photo", StaticFiles(directory=settings.photo_path), name="photo")

if __name__ == "__main__":
    uvicorn.run("main:app")

