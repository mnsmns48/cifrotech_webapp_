import uvicorn
from fastapi import FastAPI
from core.views import router as dir_router

app = FastAPI()
app.include_router(dir_router, tags=["dirs"])

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
