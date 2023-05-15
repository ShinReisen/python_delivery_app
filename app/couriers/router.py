from datetime import date, timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.models import couriers, delivery, orders, CourierCoefficients, orders_assignments
from app.couriers.schemas import CourierDto, CreateCourierRequest, CreateCouriersResponse, GetOrderAssignmentResponse
from app.couriers.schemas import GetCouriersResponse, GetCourierMetaInfoResponse
from app.database import get_async_session
from app.fastapi_limiter.depends import RateLimiter

router = APIRouter(
    prefix="/couriers",
    tags=["Couriers"],
    dependencies=[Depends(RateLimiter(times=10, seconds=1))]
)


def first_day_of_month(any_day):
    day_num = any_day.strftime("%d")
    return any_day - timedelta(days=int(day_num) - 1)


def last_day_of_month(any_day):
    next_month = any_day.replace(day=28) + timedelta(days=4)
    return next_month - timedelta(days=next_month.day)


# получение одного курьера
@router.get(
    "/{courier_id}",
    response_model=CourierDto
)
async def get_specific_courier(courier_id: int, session: AsyncSession = Depends(get_async_session)):
    try:
        query = select(couriers).filter(couriers.courier_id == courier_id)
        result = await session.execute(query)
        courier_row = result.fetchone()
        if courier_row is not None:
            return courier_row[0]
    except Exception:
        # Передать ошибку разработчикам
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "data": None,
            "details": None
        })


# получение списка курьеров
@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=GetCouriersResponse
)
async def get_couriers(session: AsyncSession = Depends(get_async_session), offset: int = 0, limit: int = 1):
    query = select(couriers).limit(limit).offset(offset)
    result = await session.execute(query)
    body_response = {"couriers": [r for r, in result], "limit": limit, "offset": offset}
    return body_response


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=CreateCouriersResponse
)
async def add_couriers(new_couriers: CreateCourierRequest, session: AsyncSession = Depends(get_async_session)):
    couriers_data = [couriers(**i.dict()) for i in new_couriers.couriers]
    session.add_all(couriers_data)
    await session.commit()
    return {"couriers": couriers_data}


# получение рейтинга курьера
@router.get(
    "/meta-info/{courier_id}",
    status_code=status.HTTP_200_OK,
    name="Couriers meta-info",
    response_model=GetCourierMetaInfoResponse
)
async def get_courier_meta_info(
        courier_id: int,
        start_date: date = first_day_of_month(date.today()),
        end_date: date = last_day_of_month(date.today()),
        session: AsyncSession = Depends(get_async_session)
):
    try:
        # query = select(func.sum(orders.cost).label("cost"), func.count(orders.order_id).label("count")). \
        #     filter(orders.completed_time.isnot(None)). \
        #     filter(orders.order_id.in_(select(delivery.order_id).filter(delivery.courier_id == courier_id). \
        #                                filter(delivery.delivery_date.between(start_date, end_date))
        #                                )
        #            )
        query = select(func.sum(orders.cost).label("cost"), func.count(orders.order_id).label("count")). \
            filter(orders.completed_time.isnot(None)). \
            filter(orders.order_id.in_(select(func.unnest(orders_assignments.orders)). \
                                       filter(orders_assignments.courier_id == courier_id)
                                       ))
        result = await session.execute(query)
        data_row = result.fetchone()
        if data_row[0] is not None:
            query = select(couriers.courier_type, couriers.working_hours).filter(couriers.courier_id == courier_id)
            result = await session.execute(query)
            courier_data_from_db = result.fetchone()

            courier_type_from_db, working_hours_from_db = (courier_data_from_db)
            coefficients = CourierCoefficients(courier_type_from_db)
            diff_days = (end_date - start_date).days
            diff_hours = get_working_hours_count(working_hours_from_db)
            hours_by_period = diff_hours * diff_days
            return {
                "start_date": start_date,
                "end_date": end_date,
                "courier_id": courier_id,
                "courier_type": courier_type_from_db,
                "orders_count": data_row.count,
                "orders_cost": data_row.cost,
                "hours_count": hours_by_period,
                "earnings": data_row.cost * coefficients.earnings_coeff,
                "rating": round((data_row.count / hours_by_period) * coefficients.rating_coeff, 4)
            }
        else:
            return {
                "start_date": start_date,
                "end_date": end_date,
                "courier_id": courier_id
            }
    except Exception:
        # Передать ошибку разработчикам
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "data": None,
            "details": "Нет данных"
        })


def get_working_hours_count(working_hours: list) -> int:
    result = 0
    for turn in working_hours:
        start_time = datetime.strptime(turn[:5], '%H:%M').time()
        end_time = datetime.strptime(turn[6:], '%H:%M').time()
        delta = end_time.hour - start_time.hour
        result += delta
    return result


# получение списка распределенных заказов
@router.get(
    "/assignments/",
    status_code=status.HTTP_200_OK,
    response_model=GetOrderAssignmentResponse
)
async def get_orders_assignment(session: AsyncSession = Depends(get_async_session), offset: int = 0, limit: int = 1):
    query = select(orders_assignments).limit(limit).offset(offset)
    result = await session.execute(query)
    body_response = {"orders_assignment": [r for r, in result], "limit": limit, "offset": offset}
    return body_response
