from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, time
import re
from enum import Enum
from typing import List

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Date, Time
from sqlalchemy.dialects.postgresql import ARRAY

Base = declarative_base()

hours_pattern = re.compile(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]-([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")


##############################
# BLOCK WITH DATABASE MODELS #
##############################

class couriers(Base):
    __tablename__ = 'couriers'
    courier_id = Column(Integer, primary_key=True)
    courier_type = Column(String, nullable=False)
    regions = Column(ARRAY(Integer), nullable=False)
    working_hours = Column(ARRAY(String), nullable=False)


class orders(Base):
    __tablename__ = 'orders'
    order_id = Column(Integer, primary_key=True)
    weight = Column(Float, nullable=False)
    regions = Column(Integer, nullable=False)
    delivery_hours = Column(ARRAY(String), nullable=False)
    cost = Column(Integer, nullable=False)
    completed_time = Column(String, nullable=True)


class delivery(Base):
    __tablename__ = 'delivery'
    delivery_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey(orders.order_id), nullable=False)
    courier_id = Column(Integer, ForeignKey(couriers.courier_id), nullable=False)
    delivery_date = Column(Date, nullable=False)


class orders_assignments(Base):
    __tablename__ = 'orders_assignments'
    assignments_id = Column(Integer, primary_key=True)
    courier_id = Column(Integer, ForeignKey(couriers.courier_id), nullable=False)
    courier_type = Column(String, nullable=False)
    delivery_date = Column(Date, nullable=False)
    turn_time = Column(Time, nullable=False)
    regions = Column(ARRAY(Integer), nullable=False)
    orders = Column(ARRAY(Integer), nullable=False)

###################################
# BLOCK WITH DOMAIN-DRIVEN DESIGN #
###################################

class Couriers_Types(str, Enum):
    COURIER_TYPE_FOOT = "FOOT"
    COURIER_TYPE_BIKE = "BIKE"
    COURIER_TYPE_AUTO = "AUTO"


# класс для расчета рейтинга курьера
class CourierCoefficients:
    def __init__(self, courier_type: Couriers_Types):
        if courier_type == Couriers_Types.COURIER_TYPE_FOOT:
            self.earnings_coeff = 2
            self.rating_coeff = 3
        elif courier_type == Couriers_Types.COURIER_TYPE_BIKE:
            self.earnings_coeff = 3
            self.rating_coeff = 2
        elif courier_type == Couriers_Types.COURIER_TYPE_AUTO:
            self.earnings_coeff = 4
            self.rating_coeff = 1
        else:
            self.earnings_coeff = 0
            self.rating_coeff = 0


# класс заказа для алгоритма распределения заказов
class OrderAssign:
    def __init__(self, order: orders):
        self.order_id = order.order_id
        self.regions = order.regions
        self.cost = order.cost
        self.weight = order.weight

        # в бд у нас список, но мы упростим модель и будем считать, что у нас одно окно доставки
        delivery_hours = order.delivery_hours[0]
        self.delivery_start = datetime.strptime(delivery_hours[:5], '%H:%M').time()
        self.delivery_end = datetime.strptime(delivery_hours[6:], '%H:%M').time()


@dataclass
class CourierTurn:
    turn_time: time = field(default_factory=time)
    regions: List[int] = field(default_factory=list)
    orders: List[int] = field(default_factory=list)


# класс курьера для алгоритма распределения заказов
class CourierLoad:
    # инициализируем смену
    def __init__(self, courier: couriers, working_hours, delivery_date):

        # определим вводные данные текущей смены
        self.delivery_date = delivery_date
        self.courier_id = courier.courier_id
        self.courier_type = courier.courier_type
        self.regions = courier.regions
        self.working_hours = working_hours

        # определим ограничения курьера по транспорту
        if courier.courier_type == Couriers_Types.COURIER_TYPE_FOOT:
            self.max_load = 10
            self.max_regions = 1
            self.max_orders = 2
            self.time_for_first = 25
            self.time_for_subs = 10
        elif courier.courier_type == Couriers_Types.COURIER_TYPE_BIKE:
            self.max_load = 20
            self.max_regions = 2
            self.max_orders = 4
            self.time_for_first = 12
            self.time_for_subs = 8
        elif courier.courier_type == Couriers_Types.COURIER_TYPE_AUTO:
            self.max_load = 40
            self.max_regions = 3
            self.max_orders = 7
            self.time_for_first = 8
            self.time_for_subs = 4

        # инициализируем текущую загрузку смены
        self.available_load = self.max_load
        self.available_regions = self.max_regions
        self.available_orders = self.max_orders
        self.start_time = datetime.strptime(working_hours[:5], '%H:%M').time()
        self.end_time = datetime.strptime(working_hours[6:], '%H:%M').time()
        self.order_groups_list = []  # список заказов в текущей смене, по сути это список order_group
        self.current_turn = CourierTurn()  # список заказов в текущей доставке

    def __gt__(self, other):
        if self.start_time is None:
            return False
        if other.start_time is None:
            return True
        return self.start_time > other.start_time

    @property
    def time_to_deliver(self):
        if len(self.current_turn.orders) == 0:
            return self.time_for_first
        else:
            return self.time_for_subs

    @property
    def deliver_time(self):
        return (datetime.combine(date.today(), self.start_time) + timedelta(minutes=self.time_to_deliver)).time()

    # блок проверок может ли курьер взять заказ
    def __can_allocate_by_time(self, order: OrderAssign) -> bool:
        result = order.delivery_start <= self.deliver_time <= order.delivery_end
        # возможно больше нет заказов в это время, тогда нужно завершить тур и начать заново
        if not result and (datetime.combine(date.today(), self.end_time) -
                           timedelta(minutes=self.time_for_first)).time() >= order.delivery_start:
            self.restart_turn()
            self.start_time = order.delivery_start
            result = True
        return result

    def __can_allocate_by_weight(self, order: OrderAssign) -> bool:
        return self.available_load >= order.weight

    def __can_allocate_by_regions(self, order: OrderAssign) -> bool:
        result = order.regions in self.regions and (
                order.regions in self.current_turn.regions or self.available_regions > 0)
        return result

    def can_allocate(self, order: OrderAssign) -> bool:
        return self.__can_allocate_by_time(order) and \
            self.__can_allocate_by_weight(order) and self.__can_allocate_by_regions(order)

    # добавим заказ в группу и уменьшим доступные ресурсы курьера
    def allocate(self, order: OrderAssign):
        self.start_time = self.deliver_time
        self.current_turn.orders.append(order.order_id)
        self.available_orders -= 1
        if order.regions not in self.current_turn.regions:
            self.current_turn.regions.append(order.regions)
            self.available_regions -= 1
        self.available_load -= order.weight

        # проверим не достигли ли мы предельных значений группы
        if self.__check_limits_for_turn():
            self.restart_turn()

    # проверка предельных значений для группы
    def __check_limits_for_turn(self):
        return self.available_load == 0 or self.available_orders == 0

    # проверка, что курьер больше сегодня недоступен
    def is_loaded(self):
        return self.deliver_time > self.end_time

    # запомним группу заказов и обновим данные для доставки
    def restart_turn(self):
        if len(self.current_turn.orders) > 0:
            self.current_turn.turn_time = self.start_time
            self.order_groups_list.append(self.current_turn)
        self.available_load = self.max_load
        self.available_regions = self.max_regions
        self.available_orders = self.max_orders
        self.current_turn = CourierTurn()
