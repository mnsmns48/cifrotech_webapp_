import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from core.views import router as dir_router
from pages.router import pages_router

app = FastAPI(title="Салон мобильной связи Цифротех")
app.include_router(pages_router, prefix="/static", tags=["pages"])
app.include_router(dir_router, prefix="/dirs", tags=["dirs"])
app.mount("/static", StaticFiles(directory="static", html=True))

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
