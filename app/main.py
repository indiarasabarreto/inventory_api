import os

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.security import SESSION_SECRET, is_valid_password

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

import app.models
from app.database import Base, DATABASE_URL, engine, get_db
from app.models import Category, Product, StockMovement
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    StockMovementCreate,
    StockMovementResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No SQLite local, mantém a criação automática usada durante o desenvolvimento.
    # No PostgreSQL da nuvem, as tabelas serão criadas somente pelo Alembic.
    if DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)

    yield


APP_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Inventory API",
    version="0.1.0",
    lifespan=lifespan,
)

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=COOKIE_SECURE, 
)

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/login", status_code=303)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    return {
        "status": "ok",
        "database_backend": engine.url.get_backend_name(),
        "counts": {
            "categories": db.scalar(select(func.count(Category.id))),
            "products": db.scalar(select(func.count(Product.id))),
            "stock_movements": db.scalar(select(func.count(StockMovement.id))),
            },
        }


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

@app.put(
    "/categories/{category_id}",
    response_model=CategoryResponse,
)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
):
    category = db.get(Category, category_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada.",
        )

    normalized_name = category_data.name.strip()

    if len(normalized_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe um nome com pelo menos 2 caracteres.",
        )

    existing_category = db.scalar(
        select(Category).where(
            func.lower(Category.name) == normalized_name.lower(),
            Category.id != category_id,
        )
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma categoria com este nome.",
        )

    category.name = normalized_name
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

@app.get("/products/low-stock", response_model=list[ProductResponse])
def list_low_stock_products(db: Session = Depends(get_db)):
    return db.scalars(
        select(Product)
        .where(Product.quantity <= Product.minimum_quantity)
        .order_by(Product.quantity, Product.name)
    ).all()


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


def redirect_to_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("warehouse_access"):
        return RedirectResponse(url="/warehouse", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None},
    )

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, password: str = Form(...)):
    if not is_valid_password(password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Senha incorreta. Tente novamente."},
            status_code=401,
        )

    request.session["warehouse_access"] = True
    return RedirectResponse(url="/warehouse", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/warehouse", response_class=HTMLResponse)
def warehouse_page(
    request: Request,
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    products = db.scalars(
        select(Product)
        .options(selectinload(Product.category))
        .order_by(Product.name)
    ).all()

    low_stock_products = [
        product
        for product in products
        if product.quantity <= product.minimum_quantity
    ]


    notice = request.session.pop("notice", None)

    return templates.TemplateResponse(
        request=request,
        name="warehouse.html",
        context={"products": products, "low_stock_products": low_stock_products, "notice": notice},
    )

@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    category = db.get(Category, product_data.category_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não existente.",
        )

    product.name = product_data.name.strip()
    product.category_id = product_data.category_id
    product.minimum_quantity = product_data.minimum_quantity

    db.commit()
    db.refresh(product)

    return product


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    movement_count = db.scalar(
        select(func.count(StockMovement.id)).where(
            StockMovement.product_id == product_id
        )
    )

    if movement_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível remover um item que possui movimentações.",
        )

    db.delete(product)
    db.commit()



@app.get('/warehouse/movement/{movement_type}', response_class=HTMLResponse)
def movement_form(
    movement_type: str,
    request: Request,
    db: Session = Depends(get_db),
):

    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    if movement_type not in {"in", "out"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    products = db.scalars(select(Product).order_by(Product.name)).all()

    return templates.TemplateResponse(
        request=request,
        name="movement_form.html",
        context={"products": products, "movement_type": movement_type},
    )


@app.post("/warehouse/products/new", response_class=HTMLResponse)
def submit_new_product(
    request: Request,
    name: str = Form(...),
    initial_quantity: int = Form(0),
    minimum_quantity: int = Form(3),
    category_id: int = Form(...),
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    values = {
        "name": name,
        "initial_quantity": initial_quantity,
        "minimum_quantity": minimum_quantity,
        "category_id": category_id,
    }

    normalized_name = name.strip()

    if len(normalized_name) < 2:
        return render_new_product_form(
            request,
            db,
            error="Informe um nome com pelo menos 2 caracteres.",
            values=values,
            status_code=422,
        )

    if initial_quantity < 0 or minimum_quantity < 0:
        return render_new_product_form(
            request,
            db,
            error="As quantidades não podem ser negativas.",
            values=values,
            status_code=422,
        )

    category = db.get(Category, category_id)

    if category is None:
        return render_new_product_form(
            request,
            db,
            error="Selecione uma categoria válida.",
            values=values,
            status_code=404,
        )

    product = Product(
        name=normalized_name,
        quantity=0,
        minimum_quantity=minimum_quantity,
        category_id=category_id,
    )
    db.add(product)
    db.flush()

    if initial_quantity > 0:
        db.add(
            StockMovement(
                product_id=product.id,
                movement_type="in",
                quantity=initial_quantity,
            )
        )
        product.quantity = initial_quantity

    db.commit()

    request.session["notice"] = f"Item {product.name} cadastrado com sucesso."
    return RedirectResponse(url="/warehouse", status_code=303)



@app.get("/warehouse/categories/new", response_class=HTMLResponse)
def new_category_form(request: Request):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    return templates.TemplateResponse(
        request=request,
        name="category_form.html",
        context={"error": None},
    )


@app.post("/warehouse/categories/new", response_class=HTMLResponse)
def submit_new_category(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    normalized_name = name.strip()

    if len(normalized_name) < 2:
        return templates.TemplateResponse(
            request=request,
            name="category_form.html",
            context={"error": "Informe um nome com pelo menos 2 caracteres."},
            status_code=422,
        )

    existing_category = db.scalar(
        select(Category).where(Category.name == normalized_name)
    )

    if existing_category:
        return templates.TemplateResponse(
            request=request,
            name="category_form.html",
            context={"error": "Essa categoria já está cadastrada."},
            status_code=409,
        )

    category = Category(name=normalized_name)
    db.add(category)
    db.commit()

    request.session["notice"] = f"Categoria {category.name} cadastrada com sucesso."
    return RedirectResponse(url="/warehouse", status_code=303)

@app.get("/warehouse/categories/{category_id}/edit", response_class=HTMLResponse)
def edit_category_form(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    category = db.get(Category, category_id)

    if category is None:
        request.session["category_notice"] = "Categoria não encontrada."
        request.session["category_notice_kind"] = "warning"
        return RedirectResponse(url="/warehouse/categories", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="category_edit_form.html",
        context={"category": category, "error": None, "values": {}},
    )


@app.post("/warehouse/categories/{category_id}/edit", response_class=HTMLResponse)
def submit_edit_category(
    category_id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    category = db.get(Category, category_id)

    if category is None:
        request.session["category_notice"] = "Categoria não encontrada."
        request.session["category_notice_kind"] = "warning"
        return RedirectResponse(url="/warehouse/categories", status_code=303)

    normalized_name = name.strip()

    if len(normalized_name) < 2:
        return templates.TemplateResponse(
            request=request,
            name="category_edit_form.html",
            context={
                "category": category,
                "error": "Informe um nome com pelo menos 2 caracteres.",
                "values": {"name": name},
            },
            status_code=422,
        )

    existing_category = db.scalar(
        select(Category).where(
            func.lower(Category.name) == normalized_name.lower(),
            Category.id != category_id,
        )
    )

    if existing_category:
        return templates.TemplateResponse(
            request=request,
            name="category_edit_form.html",
            context={
                "category": category,
                "error": "Já existe uma categoria com este nome.",
                "values": {"name": name},
            },
            status_code=409,
        )

    category.name = normalized_name
    db.commit()

    request.session["category_notice"] = (
        f"Categoria {category.name} atualizada com sucesso."
    )
    return RedirectResponse(url="/warehouse/categories", status_code=303)

@app.get("/warehouse/categories/{category_id}", response_class=HTMLResponse)
def category_products_page(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    category = db.get(Category, category_id)

    if category is None:
        request.session["category_notice"] = "Categoria não encontrada."
        request.session["category_notice_kind"] = "warning"
        return RedirectResponse(url="/warehouse/categories", status_code=303)

    products = db.scalars(
        select(Product)
        .where(Product.category_id == category_id)
        .order_by(Product.name)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="category_products.html",
        context={"category": category, "products": products},
    )

@app.get("/warehouse/categories", response_class=HTMLResponse)
def categories_page(
    request: Request,
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    category_rows = db.execute(
        select(
            Category,
            func.count(Product.id).label("product_count"),
        )
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id, Category.name)
        .order_by(Category.name)
    ).all()

    categories = [
        {
            "id": category.id,
            "name": category.name,
            "product_count": product_count,
        }
        for category, product_count in category_rows
    ]

    category_notice = request.session.pop("category_notice", None)
    notice_kind = request.session.pop("category_notice_kind", "success")

    return templates.TemplateResponse(
        request=request,
        name="categories.html",
        context={
            "categories": categories,
            "category_notice": category_notice,
            "notice_kind": notice_kind,
        },
    )

def render_new_product_form(
    request: Request,
    db: Session,
    error: str | None = None,
    values: dict | None = None,
    status_code: int = 200,
):
    categories = db.scalars(select(Category).order_by(Category.name)).all()

    return templates.TemplateResponse(
        request=request,
        name="product_form.html",
        context={
            "categories": categories,
            "error": error,
            "values": values or {},
        },
        status_code=status_code,
    )

def render_edit_product_form(
    request: Request,
    db: Session,
    product: Product,
    error: str | None = None,
    values: dict | None = None,
    status_code: int = 200,
):
    categories = db.scalars(select(Category).order_by(Category.name)).all()

    return templates.TemplateResponse(
        request=request,
        name="product_edit_form.html",
        context={
            "product": product,
            "categories": categories,
            "error": error,
            "values": values or {},
        },
        status_code=status_code,
    )


@app.get("/warehouse/products/{product_id}/edit", response_class=HTMLResponse)
def edit_product_form(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    product = db.get(Product, product_id)

    if product is None:
        request.session["notice"] = "Item não encontrado."
        return RedirectResponse(url="/warehouse", status_code=303)

    return render_edit_product_form(request, db, product)


@app.post("/warehouse/products/{product_id}/edit", response_class=HTMLResponse)
def submit_edit_product(
    product_id: int,
    request: Request,
    name: str = Form(...),
    category_id: int = Form(...),
    minimum_quantity: int = Form(...),
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    product = db.get(Product, product_id)

    if product is None:
        request.session["notice"] = "Item não encontrado."
        return RedirectResponse(url="/warehouse", status_code=303)

    values = {
        "name": name,
        "category_id": category_id,
        "minimum_quantity": minimum_quantity,
    }
    normalized_name = name.strip()

    if len(normalized_name) < 2:
        return render_edit_product_form(
            request,
            db,
            product,
            error="Informe um nome com pelo menos 2 caracteres.",
            values=values,
            status_code=422,
        )

    if minimum_quantity < 0:
        return render_edit_product_form(
            request,
            db,
            product,
            error="O estoque mínimo não pode ser negativo.",
            values=values,
            status_code=422,
        )

    category = db.get(Category, category_id)

    if category is None:
        return render_edit_product_form(
            request,
            db,
            product,
            error="Selecione uma categoria válida.",
            values=values,
            status_code=404,
        )

    product.name = normalized_name
    product.category_id = category_id
    product.minimum_quantity = minimum_quantity
    db.commit()

    request.session["notice"] = f"Item {product.name} atualizado com sucesso."
    return RedirectResponse(url="/warehouse", status_code=303)

@app.post("/warehouse/products/{product_id}/delete")
def submit_delete_product(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    product = db.get(Product, product_id)

    if product is None:
        request.session["notice"] = "Item não encontrado."
        return RedirectResponse(url="/warehouse", status_code=303)

    movement_count = db.scalar(
        select(func.count(StockMovement.id)).where(
            StockMovement.product_id == product_id
        )
    )

    if movement_count > 0:
        request.session["notice"] = (
            f"Não é possível remover {product.name}: o item possui movimentações."
        )
        return RedirectResponse(url="/warehouse", status_code=303)

    product_name = product.name
    db.delete(product)
    db.commit()

    request.session["notice"] = f"Item {product_name} removido com sucesso."
    return RedirectResponse(url="/warehouse", status_code=303)



@app.get("/warehouse/products/new", response_class=HTMLResponse)
def new_product_form(
    request: Request,
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    return render_new_product_form(request, db)


@app.post("/warehouse/products/new", response_class=HTMLResponse)
def submit_new_product(
    request: Request,
    name: str = Form(...),
    initial_quantity: int = Form(0),
    minimum_quantity: int = Form(3),
    category_id: int = Form(...),
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    values = {
        "name": name,
        "initial_quantity": initial_quantity,
        "minimum_quantity": minimum_quantity,
        "category_id": category_id,
    }

    normalized_name = name.strip()

    if len(normalized_name) < 2:
        return render_new_product_form(
            request,
            db,
            error="Informe um nome com pelo menos 2 caracteres.",
            values=values,
            status_code=422,
        )

    if initial_quantity < 0 or minimum_quantity < 0:
        return render_new_product_form(
            request,
            db,
            error="As quantidades não podem ser negativas.",
            values=values,
            status_code=422,
        )

    category = db.get(Category, category_id)

    if category is None:
        return render_new_product_form(
            request,
            db,
            error="Selecione uma categoria válida.",
            values=values,
            status_code=404,
        )

    product = Product(
        name=normalized_name,
        quantity=0,
        minimum_quantity=minimum_quantity,
        category_id=category_id,
    )
    db.add(product)
    db.flush()

    if initial_quantity > 0:
        db.add(
            StockMovement(
                product_id=product.id,
                movement_type="in",
                quantity=initial_quantity,
            )
        )
        product.quantity = initial_quantity

    db.commit()

    request.session["notice"] = f"Item {product.name} cadastrado com sucesso."
    return RedirectResponse(url="/warehouse", status_code=303)


@app.post("/warehouse/categories/{category_id}/delete")
def delete_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    if not request.session.get("warehouse_access"):
        return redirect_to_login()

    category = db.get(Category, category_id)

    if category is None:
        request.session["category_notice"] = "Categoria não encontrada."
        request.session["category_notice_kind"] = "warning"
        return RedirectResponse(url="/warehouse/categories", status_code=303)

    product_count = db.scalar(
        select(func.count(Product.id)).where(Product.category_id == category.id)
    )

    if product_count > 0:
        request.session["category_notice"] = (
            f"A categoria {category.name} não pode ser removida porque possui {product_count} item(ns)."
        )
        request.session["category_notice_kind"] = "warning"
        return RedirectResponse(url="/warehouse/categories", status_code=303)

    category_name = category.name
    db.delete(category)
    db.commit()

    request.session["category_notice"] = f"Categoria {category_name} removida com sucesso."
    request.session["category_notice_kind"] = "success"
    return RedirectResponse(url="/warehouse/categories", status_code=303)
