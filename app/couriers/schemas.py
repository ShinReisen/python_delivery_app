from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, validator
from pydantic.types import date

from app.models import Couriers_Types, hours_pattern
from app.orders.schemas import OrderAssignmentResponse


class OurBaseModel(BaseModel):
    class Config:
        orm_mode = True


class CourierDto(OurBaseModel):
    courier_id: int
    courier_type: Couriers_Types
    regions: List[int]
    working_hours: List[str]


class CreateCourierDto(BaseModel):
    courier_type: Couriers_Types
    regions: List[int]
    working_hours: List[str] = ["11:00-15:00"]

    @validator("working_hours", each_item=True)
    def validate_working_hours(cls, value):
        if not hours_pattern.match(value):
            raise HTTPException(
                status_code=422, detail="График работы задается списком строк формата HH:MM-HH:MM"
            )
        return value


class CreateCourierRequest(BaseModel):
    couriers: List[CreateCourierDto]


class GetCourierMetaInfoResponse(BaseModel):
    start_date: date
    end_date: date
    courier_id: int
    courier_type: Optional[Couriers_Types]
    orders_count: Optional[int]
    orders_cost: Optional[int]
    hours_count: Optional[int]
    rating: Optional[float]
    earnings: Optional[float]


class CreateCouriersResponse(OurBaseModel):
    couriers: List[CourierDto]


class GetCouriersResponse(BaseModel):
    couriers: List[CourierDto]
    limit: int
    offset: int


class GetOrderAssignmentResponse(BaseModel):
    orders_assignment: List[OrderAssignmentResponse]
    limit: int
    offset: int