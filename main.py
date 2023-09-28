import uvicorn
from fastapi import FastAPI
from items_views import router as items_router
from core.crud import router as dir_router


app = FastAPI()
app.include_router(items_router, tags=["items"])
app.include_router(dir_router, tags=["dirs"])

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
