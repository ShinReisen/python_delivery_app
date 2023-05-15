import redis.asyncio as redisac
from app.fastapi_limiter import FastAPILimiter
from app.router import router
from app.couriers.router import router as router_courier
from app.orders.router import router as router_order
from fastapi import FastAPI
from app.config import REDIS_HOST


# инициализируем приложение
app = FastAPI(title="Yandex Lavka")

# подключим основные/корневые эндпоинты
app.include_router(router)

# подключим эндпоинты по курьерам
app.include_router(router_courier)

# подключим эндпоинты по заказам
app.include_router(router_order)



@app.on_event("startup")
async def startup():
   redis = redisac.from_url(f"redis://{REDIS_HOST}", encoding="utf-8", decode_responses=True)
   await FastAPILimiter.init(redis)