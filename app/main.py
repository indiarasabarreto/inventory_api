from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models
from app.database import Base, engine, get_db
from app.models import Category, Product, StockMovement
from app.schemas import (
    CategoryCreate, 
    CategoryResponse,
    ProductCreate,
    ProductResponse,
    StockMovementCreate,
    StockMovementResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Inventory API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
):
    existing_category = db.scalar(
        select(Category).where(Category.name == category_data.name)
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists.",
        )

    category = Category(name=category_data.name)
    db.add(category)
    db.commit()
    db.refresh(category)

    return category



@app.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(
        select(Category).order_by(Category.name)
    ).all()


@app.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
):
    existing_category = db.scalar(
        select(Category).where(Category.name == category_data.name)
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists.",
        )

    category = Category(name=category_data.name)
    db.add(category)
    db.commit()
    db.refresh(category)

    return category

@app.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
):
    category = db.get(Category, product_data.category_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    existing_product = db.scalar(
        select(Product).where(Product.sku == product_data.sku)
    )

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU already exists.",
        )

    product = Product(**product_data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    return product


@app.get("/products", response_model=list[ProductResponse])
def list_products(
    category_id: int | None = None,
    db: Session = Depends(get_db),
):
    statement = select(Product).order_by(Product.name)

    if category_id is not None:
        statement = statement.where(Product.category_id == category_id)

    return db.scalars(statement).all()

@app.post(
    "/stock-movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement(
    movement_data: StockMovementCreate,
    db: Session = Depends(get_db),
):
    product = db.get(Product, movement_data.product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    if (
        movement_data.movement_type == "out"
        and movement_data.quantity > product.quantity
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Insufficient stock for this movement.",
        )

    if movement_data.movement_type == "in":
        product.quantity += movement_data.quantity
    else:
        product.quantity -= movement_data.quantity

    movement = StockMovement(**movement_data.model_dump())
    db.add(movement)
    db.commit()
    db.refresh(movement)

    return movement

@app.get(
    "/products/{product_id}/movements",
    response_model=list[StockMovementResponse],
)
def list_product_movements(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return db.scalars(
        select(StockMovement)
        .where(StockMovement.product_id == product_id)
        .order_by(StockMovement.created_at.desc())
    ).all()

