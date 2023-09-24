import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get('/')
def hello_index():
    return {
        'message': 'start project'
    }


@app.get('/items')
def hello_index():
    return {
        'message': [1, 2, 3]
    }


@app.get('/items/{item_id}')
def get_item_by_id(item_id: int):
    return {
        'item': {
            'id': item_id
        }
    }


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
