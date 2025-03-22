import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from api_v1.cifrotech_views import cifrotech_router
from api_v2.api_v2_views import api_v2_router
from cfg import settings

app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=settings.cors,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   allow_credentials=True)
app.include_router(cifrotech_router, tags=["Api_v1"])
app.include_router(api_v2_router, tags=["Api_v2"])
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/photo", StaticFiles(directory=settings.photo_path), name="photo")
app.mount("/s/photo", StaticFiles(directory=settings.photo_path), name="photo")

if __name__ == "__main__":
    uvicorn.run("main:app", host='0.0.0.0',port=5000)
