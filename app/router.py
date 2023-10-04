from fastapi import APIRouter, Request, Depends
from starlette import status

from app.fastapi_limiter.depends import RateLimiter

router = APIRouter(
    dependencies=[Depends(RateLimiter(times=10, seconds=1))]
)
