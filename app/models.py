from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"),
        nullable=True,
    )

    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side=[id],
        back_populates="subcategories",
    )
    subcategories: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
    )
    products: Mapped[list["Product"]] = relationship(back_populates="category")

    import_batches: Mapped[list["ImportBatch"]] = relationship(
        back_populates="category"
    )

class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    preview_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    category: Mapped["Category"] = relationship(
        back_populates="import_batches"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="import_batch"
    )

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    minimum_quantity: Mapped[int] = mapped_column(
        default=3,
        server_default="3",
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )

    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id"),
        nullable=True,
    )

    category: Mapped["Category"] = relationship(back_populates="products")
    movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="product"
    )

    import_batch: Mapped["ImportBatch | None"] = relationship(
        back_populates="products"
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )
    movement_type: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    product: Mapped["Product"] = relationship(back_populates="movements")
