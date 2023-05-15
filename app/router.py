from fastapi import APIRouter, Request, Depends
from starlette import status

from app.fastapi_limiter.depends import RateLimiter

router = APIRouter(
    # расскоментить для запуска лимитера
    # dependencies=[Depends(RateLimiter(times=10, seconds=1))]
)

# Решил отключить корневые роуты для красоты докс

# @router.get(
#     "/ping",
#     name='dev:ping',
#     status_code=status.HTTP_200_OK
# )
# async def ping():
#     return 'pong'
#
#
# @router.get("/")
# def hello():
#     return "Hello world! It's Shin!"
#
#
# @router.post(
#     "/hello",
#     name='dev:hello-username',
#     status_code=status.HTTP_200_OK
# )
# async def ping(request: Request):
#     request = await request.json()
#     username = request['username']
#     return f'Hello, {username}!'
