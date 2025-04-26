from fastapi import FastAPI, HTTPException
from starlette.requests import Request

from api_service.routers import templates
from utils import all_css


async def authorization_handler(request: Request, exc: HTTPException):
    context = {"request": request, "message": exc.detail}
    context.update(all_css)
    return templates.TemplateResponse("login.html", context, status_code=exc.status_code)


def register_service_handlers(app: FastAPI):
    app.exception_handler(401)(authorization_handler)
