import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from cifrotech_views import cifrotech_router
from cfg import settings

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(cifrotech_router, tags=["pages_views"])
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/photo", StaticFiles(directory=settings.photo_path), name="photo")
app.mount("/s/photo", StaticFiles(directory=settings.photo_path), name="photo")

if __name__ == "__main__":
    uvicorn.run("main:app", port=5000
                )

