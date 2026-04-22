import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    volume_ml: Mapped[int] = mapped_column(Integer)
    price_uah: Mapped[int] = mapped_column(Integer)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String(255))
    qty: Mapped[int] = mapped_column(Integer)
    customer_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(Text)
    comment: Mapped[str] = mapped_column(Text)
    total_uah: Mapped[int] = mapped_column(Integer)


@dataclass
class Storage:
    database_url: Optional[str]

    def __post_init__(self) -> None:
        self._engine = None
        if self.database_url:
            self._engine = create_engine(self.database_url, future=True)
            Base.metadata.create_all(self._engine)
            self._seed_products_if_empty()

    @property
    def uses_database(self) -> bool:
        return self._engine is not None

    def _load_json(self, filename: str):
        with (DATA_DIR / filename).open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save_json(self, filename: str, data: Any) -> None:
        with (DATA_DIR / filename).open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _seed_products_if_empty(self) -> None:
        assert self._engine is not None
        with Session(self._engine) as session:
            existing = session.scalar(select(Product.id).limit(1))
            if existing:
                return
            for item in self._load_json("catalog.json"):
                session.add(
                    Product(
                        sku=item.get("id") or f"p{item['name'][:6]}",
                        name=item["name"],
                        volume_ml=int(item["volume_ml"]),
                        price_uah=int(item["price_uah"]),
                        in_stock=bool(item["in_stock"]),
                        description=item["description"],
                    )
                )
            session.commit()

    def get_catalog(self) -> List[Dict[str, Any]]:
        if not self._engine:
            return self._load_json("catalog.json")

        with Session(self._engine) as session:
            products = session.scalars(select(Product).order_by(Product.id)).all()
            return [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "volume_ml": item.volume_ml,
                    "price_uah": item.price_uah,
                    "in_stock": item.in_stock,
                    "description": item.description,
                }
                for item in products
            ]

    def add_product(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not self._engine:
            catalog = self._load_json("catalog.json")
            item["id"] = f"p{len(catalog) + 1:03d}"
            catalog.append(item)
            self._save_json("catalog.json", catalog)
            return item

        with Session(self._engine) as session:
            product = Product(
                sku=f"p{int(session.scalar(select(Product.id).order_by(Product.id.desc()).limit(1)) or 0) + 1:03d}",
                name=item["name"],
                volume_ml=int(item["volume_ml"]),
                price_uah=int(item["price_uah"]),
                in_stock=bool(item["in_stock"]),
                description=item["description"],
            )
            session.add(product)
            session.commit()
            session.refresh(product)
            return {
                "id": str(product.id),
                "name": product.name,
                "volume_ml": product.volume_ml,
                "price_uah": product.price_uah,
                "in_stock": product.in_stock,
                "description": product.description,
            }

    def update_product_price_by_index(self, index_1based: int, price_uah: int) -> bool:
        if not self._engine:
            catalog = self._load_json("catalog.json")
            idx = index_1based - 1
            if idx < 0 or idx >= len(catalog):
                return False
            catalog[idx]["price_uah"] = int(price_uah)
            self._save_json("catalog.json", catalog)
            return True

        with Session(self._engine) as session:
            products = session.scalars(select(Product).order_by(Product.id)).all()
            idx = index_1based - 1
            if idx < 0 or idx >= len(products):
                return False
            products[idx].price_uah = int(price_uah)
            session.commit()
            return True

    def toggle_stock_by_index(self, index_1based: int) -> Optional[bool]:
        if not self._engine:
            catalog = self._load_json("catalog.json")
            idx = index_1based - 1
            if idx < 0 or idx >= len(catalog):
                return None
            catalog[idx]["in_stock"] = not bool(catalog[idx]["in_stock"])
            self._save_json("catalog.json", catalog)
            return bool(catalog[idx]["in_stock"])

        with Session(self._engine) as session:
            products = session.scalars(select(Product).order_by(Product.id)).all()
            idx = index_1based - 1
            if idx < 0 or idx >= len(products):
                return None
            products[idx].in_stock = not products[idx].in_stock
            session.commit()
            return bool(products[idx].in_stock)

    def delete_product_by_index(self, index_1based: int) -> Optional[str]:
        if not self._engine:
            catalog = self._load_json("catalog.json")
            idx = index_1based - 1
            if idx < 0 or idx >= len(catalog):
                return None
            removed = catalog.pop(idx)
            self._save_json("catalog.json", catalog)
            return removed["name"]

        with Session(self._engine) as session:
            products = session.scalars(select(Product).order_by(Product.id)).all()
            idx = index_1based - 1
            if idx < 0 or idx >= len(products):
                return None
            removed_name = products[idx].name
            session.delete(products[idx])
            session.commit()
            return removed_name

    def save_order(self, order: Dict[str, Any]) -> int:
        total = int(order["qty"]) * int(order.get("unit_price_uah", 0))
        if not self._engine:
            orders_file = DATA_DIR / "orders.json"
            existing = []
            if orders_file.exists():
                with orders_file.open("r", encoding="utf-8") as file:
                    existing = json.load(file)
            next_id = len(existing) + 1
            payload = dict(order)
            payload["id"] = next_id
            payload["total_uah"] = total
            existing.append(payload)
            with orders_file.open("w", encoding="utf-8") as file:
                json.dump(existing, file, ensure_ascii=False, indent=2)
            return next_id

        with Session(self._engine) as session:
            record = Order(
                product=order["product"],
                qty=int(order["qty"]),
                customer_name=order["name"],
                phone=order["phone"],
                address=order["address"],
                comment=order["comment"],
                total_uah=total,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return int(record.id)
