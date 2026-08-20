from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
        examples=["Eletrônicos"],
    )


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=160,
        examples=["Teclado mecânico"],
    )
    sku: str = Field(
        min_length=3,
        max_length=60,
        examples=["TEC-MEC-001"],
    )
    unit_price: Decimal = Field(gt=0, examples=[299.90])
    quantity: int = Field(default=0, ge=0, examples=[10])
    category_id: int = Field(gt=0, examples=[1])


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    unit_price: Decimal
    quantity: int
    category_id: int

class StockMovementCreate(BaseModel):
    product_id: int = Field(gt=0, examples=[1])
    movement_type: Literal["in", "out"] = Field(examples=["in"])
    quantity: int = Field(gt=0, examples=[5])


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    movement_type: str
    quantity: int
    created_at: datetime
