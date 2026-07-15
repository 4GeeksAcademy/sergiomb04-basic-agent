import csv
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


PRODUCTS_FILE = Path(__file__).resolve().parent.parent / "products.csv"
CSV_HEADERS = ["id", "name", "quantity", "unit"]


class Product(BaseModel):
	id: int
	name: str
	quantity: int = Field(ge=0)
	unit: str


class ProductCreate(BaseModel):
	name: str = Field(min_length=1)
	quantity: int = Field(ge=0)
	unit: str = Field(min_length=1)


class StockUpdate(BaseModel):
	delta: int


app = FastAPI(title="Inventory API")


def ensure_products_csv_exists() -> None:
	PRODUCTS_FILE.parent.mkdir(parents=True, exist_ok=True)
	if not PRODUCTS_FILE.exists() or PRODUCTS_FILE.stat().st_size == 0:
		with PRODUCTS_FILE.open("w", newline="", encoding="utf-8") as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
			writer.writeheader()


def read_products() -> List[Product]:
	ensure_products_csv_exists()
	products: List[Product] = []
	try:
		with PRODUCTS_FILE.open("r", newline="", encoding="utf-8") as csv_file:
			reader = csv.DictReader(csv_file)
			for row in reader:
				if not row:
					continue
				products.append(
					Product(
						id=int(row["id"]),
						name=str(row["name"]),
						quantity=int(row["quantity"]),
						unit=str(row["unit"]),
					)
				)
	except FileNotFoundError:
		return []
	except (ValueError, KeyError) as error:
		raise HTTPException(status_code=500, detail=f"CSV format error: {error}") from error
	except OSError as error:
		raise HTTPException(status_code=500, detail=f"Failed to read products: {error}") from error

	return products


def save_products(products: List[Product]) -> None:
	ensure_products_csv_exists()
	try:
		with PRODUCTS_FILE.open("w", newline="", encoding="utf-8") as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
			writer.writeheader()
			for product in products:
				writer.writerow(product.model_dump())
	except OSError as error:
		raise HTTPException(status_code=500, detail=f"Failed to save products: {error}") from error


def generate_next_id(products: List[Product]) -> int:
	if not products:
		return 1
	return max(product.id for product in products) + 1


@app.get("/inventory", response_model=List[Product])
def get_inventory() -> List[Product]:
	return read_products()


@app.post("/inventory", response_model=Product, status_code=201)
def create_product(payload: ProductCreate) -> Product:
	products = read_products()
	new_product = Product(
		id=generate_next_id(products),
		name=payload.name.strip(),
		quantity=payload.quantity,
		unit=payload.unit.strip(),
	)
	products.append(new_product)
	save_products(products)
	return new_product


@app.patch("/inventory/{product_id}", response_model=Product)
def update_inventory(product_id: int, payload: StockUpdate) -> Product:
	products = read_products()
	for index, product in enumerate(products):
		if product.id == product_id:
			new_quantity = product.quantity + payload.delta
			if new_quantity < 0:
				raise HTTPException(
					status_code=400,
					detail="Stock update would result in negative quantity",
				)
			updated = Product(
				id=product.id,
				name=product.name,
				quantity=new_quantity,
				unit=product.unit,
			)
			products[index] = updated
			save_products(products)
			return updated

	raise HTTPException(status_code=404, detail="Product not found")


@app.get("/inventory/alerts", response_model=List[Product])
def get_inventory_alerts(threshold: int = Query(default=10, ge=0)) -> List[Product]:
	products = read_products()
	return [product for product in products if product.quantity < threshold]
