from typing import List, Optional
from datetime import datetime as pydate

from fastapi import HTTPException
from pydantic import BaseModel, validator
from pydantic.schema import datetime, date, time

from app.models import hours_pattern


class OurBaseModel(BaseModel):
    class Config:
        orm_mode = True


class OrderDTO(OurBaseModel):
    order_id: Optional[int]
    weight: float
    regions: int
    delivery_hours: List[str]

    cost: int
    completed_time: Optional[datetime]


class CreateOrderDto(BaseModel):
    weight: float
    regions: int
    delivery_hours: List[str] = ["09:00-21:00"]
    cost: int

    @validator("delivery_hours", each_item=True)
    def validate_working_hours(cls, value):
        if not hours_pattern.match(value):
            raise HTTPException(
                status_code=422, detail="Время доставки задается списком строк формата HH:MM-HH:MM"
            )
        return value


class CreateOrdersResponse(OurBaseModel):
    orders: List[OrderDTO]


class CreateOrderRequest(BaseModel):
    orders: List[CreateOrderDto]


class CompleteOrder(BaseModel):
    complete_time: datetime = pydate.now().strftime("%Y-%m-%d %H:%M")
    courier_id: int
    order_id: int


class CompleteOrderRequestDto(BaseModel):
    complete_info: List[CompleteOrder]


class OrderAssignmentRequest(BaseModel):
    order_id: int
    courier_id: int
    delivery_date: Optional[date] = pydate.today().strftime("%Y-%m-%d")

class OrderAssignmentRequestDev(BaseModel):
    delivery_date: Optional[date] = pydate.today().strftime("%Y-%m-%d")


class OrderAssignmentResponse(OurBaseModel):
    courier_id: int
    courier_type: str
    delivery_date: date
    turn_time: time
    regions: List[int]
    orders: List[int]
