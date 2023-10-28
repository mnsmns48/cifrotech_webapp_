from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

pages_router = APIRouter()
static = Jinja2Templates(directory='static')


@pages_router.get("/")
async def get_page(request: Request):
    return static.TemplateResponse('index.html', {"request": request})

# @router.get("/")
# async def get_main(request: Request, session: AsyncSession = Depends(pg_engine.session_dependency)):
#     response = await get_directory(session=session, parent=0)
#     print(response)
#     return templates.TemplateResponse("index.html", {"request": request})
