from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.fastapi_limiter.depends import RateLimiter
from app.models import orders, delivery, couriers, CourierLoad, OrderAssign, orders_assignments
from app.orders.schemas import CreateOrderRequest, CompleteOrderRequestDto, OrderAssignmentRequest, \
    OrderAssignmentRequestDev, OrderAssignmentResponse, CreateOrdersResponse
from app.orders.schemas import OrderDTO
from starlette import status

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    dependencies=[Depends(RateLimiter(times=10, seconds=1))]
)


# получение одного заказа
@router.get(
    "/{order_id}",
    response_model=OrderDTO
)
async def get_specific_order(order_id: int, session: AsyncSession = Depends(get_async_session)):
    try:
        query = select(orders).filter(orders.order_id == order_id)
        result = await session.execute(query)
        order_row = result.fetchone()
        if order_row is not None:
            return order_row[0]
    except Exception:
        # Передать ошибку разработчикам
        raise HTTPException(status_code=500, detail={
            "status": "error",
            "data": None,
            "details": None
        })

# получение списка заказов
@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=List[OrderDTO]
)
async def get_orders(session: AsyncSession = Depends(get_async_session), offset: int = 0, limit: int = 1):
    query = select(orders).limit(limit).offset(offset)
    result = await session.execute(query)
    return [r for r, in result]


# загрузка списка заказов
@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=CreateOrdersResponse
)
async def add_orders(new_orders: CreateOrderRequest, session: AsyncSession = Depends(get_async_session)):
    orders_data = [orders(**i.dict()) for i in new_orders.orders]
    session.add_all(orders_data)
    await session.commit()
    return {"orders": orders_data}


# отметить выполнение заказа
@router.post(
    "/complete",
    status_code=status.HTTP_200_OK
)
async def complete_order(request: CompleteOrderRequestDto, session: AsyncSession = Depends(get_async_session)):
    result = []
    for each in request.complete_info:
        # старый код выборки
        # query = select(orders).filter(
        #     orders.order_id == select(delivery.order_id).filter(delivery.courier_id == each.courier_id,
        #                                                         delivery.order_id == each.order_id).as_scalar()
        # )

        query = select(orders).filter(orders.completed_time == None, orders.order_id == each.order_id). \
            filter(orders.order_id.in_(select(func.unnest(orders_assignments.orders)). \
                                       filter(orders_assignments.courier_id == each.courier_id)
                                          ))

        query_result = await session.execute(query)
        order_row = query_result.fetchone()
        if order_row is not None:
            order_row[0].completed_time = str(each.complete_time)
            result.append((each.order_id, status.HTTP_200_OK))
        else:
            raise HTTPException(status_code=400, detail={
            "status": "error",
            "data": {"order_id": each.order_id, "courier_id": each.courier_id},
            "details": "Неверные данные. Заказ не назначен на указанного курьера или уже выполнен"
        })

    await session.commit()
    return result

# Старый метод использовался при выполнении 1го задания
# @router.post(
#     "/assign",
# )
# async def assign_order(request: OrderAssignmentRequest, session: AsyncSession = Depends(get_async_session)):
#     delivery_data = delivery(**request.dict())
#     session.add(delivery_data)
#     await session.commit()
#     return {"status": "success", "order_id": delivery_data.order_id,
#             "courier_id": delivery_data.courier_id, "delivery_date": delivery_data.delivery_date}


@router.post(
    "/assign",
    response_model=list[OrderAssignmentResponse],
    name="Orders assignment"
)
async def assign_order_dev(request: OrderAssignmentRequestDev, session: AsyncSession = Depends(get_async_session)):
    try:
        query = select(couriers)
        result = await session.execute(query)
        couriers_db = result.fetchall()
        available_couriers = []
        for _courier in couriers_db:
            for working_hours in _courier[0].working_hours:
                available_couriers.append(CourierLoad(_courier[0], working_hours, request.delivery_date))


        query = select(orders).filter(orders.completed_time == None). \
                                filter(orders.order_id.not_in(select(func.unnest(orders_assignments.orders))
                                       ))

        result = await session.execute(query)
        orders_db = result.fetchall()
        loaded = []
        for _order in orders_db:
            order = OrderAssign(_order[0])
            try:
                courier = next(
                    c for c in sorted(available_couriers) if c.can_allocate(order)
                )
                courier.allocate(order)
            except:
                # нет доступных курьеров
                pass

            if courier.is_loaded():
                loaded.append(courier)
                available_couriers.remove(courier)

        loaded.extend(available_couriers)

        result = []
        for turn in loaded:
            turn.restart_turn()
            for group in turn.order_groups_list:
                result.append(dict(courier_id=turn.courier_id, courier_type=turn.courier_type, delivery_date=turn.delivery_date, turn_time=group.turn_time,
                                   regions=group.regions, orders=group.orders))

        session.add_all([orders_assignments(**i) for i in result])
        await session.commit()
        return result
    except Exception:
        # Передать ошибку разработчикам
        raise HTTPException(status_code=500, detail={
            "status": "resolved",
            "data": None,
            "details": "Нет данных для распределения"
        })


