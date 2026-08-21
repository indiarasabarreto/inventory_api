from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
        examples=["Bebidas"],
    )


class CategoryUpdate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
        examples=["Bebidas"],
    )


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=160,
        examples=["Vela branca"],
    )
    quantity: int = Field(default=0, ge=0, examples=[10])
    minimum_quantity: int = Field(default=3, ge=0, examples=[3])
    category_id: int = Field(gt=0, examples=[1])


class ProductUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    category_id: int = Field(gt=0)
    minimum_quantity: int = Field(default=3, ge=0, examples=[3])


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity: int
    minimum_quantity: int
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
