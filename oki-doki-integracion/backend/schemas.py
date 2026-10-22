from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str = Field(..., description="Nombre de usuario del operador")
    password: str = Field(..., description="Contraseña de acceso")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ProductBase(BaseModel):
    sku: str = Field(..., description="Código SKU único del producto")
    name: str = Field(..., min_length=3, description="Descripción mayorista")
    price: float = Field(..., gt=0, description="Precio mayorista de venta en Bs.")
    stock: int = Field(0, ge=0, description="Existencia física inicial en cajas/fardos")

class ProductCreate(ProductBase):
    cost_price: Optional[float] = Field(0.0, ge=0, description="Costo de compra en Bs.")
    min_stock: Optional[int] = Field(10, ge=0, description="Stock mínimo de alerta")

class ProductOut(ProductBase):
    id: int
    cost_price: Optional[float] = 0.0
    min_stock: Optional[int] = 10

    class Config:
        from_attributes = True

class SaleItemCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="ID del producto a vender")
    quantity: int = Field(..., gt=0, description="Cantidad de cajas/fardos")

class SaleCreate(BaseModel):
    items: List[SaleItemCreate] = Field(..., min_length=1, description="Lista de productos a despachar")
    customer_name: Optional[str] = Field("Venta Mostrador Almacén", description="Cliente mayorista")
    nit_ci: Optional[str] = Field("0", description="NIT o CI")

class SaleItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True

class SaleOut(BaseModel):
    id: int
    created_at: datetime
    total_amount: float
    voucher_code: Optional[str] = None
    items: Optional[List[SaleItemOut]] = []

    class Config:
        from_attributes = True
