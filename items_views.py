from fastapi import APIRouter

router = APIRouter(prefix="/items")


@router.get("/")
def hello_index():
    return {"message": "start project"}


@router.get("/items")
def hello_index():
    return {"message": [1, 2, 3]}


@router.get("/items/{item_id}")
def get_item_by_id(item_id: int):
    return {"item": {"id": item_id}}
