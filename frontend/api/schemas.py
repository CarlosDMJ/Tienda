"""
=============================================================================
SISTEMA ERP MAYORISTA "OKI DOKI" (DISTRIBOL) - ESQUEMAS PYDANTIC
=============================================================================
Validación estricta de datos para los 5 Módulos / Sectores:
1. users (Usuarios y Roles RBAC)
2. products (Catálogo e Inventario Mayorista)
3. suppliers, purchases, purchase_items (Proveedores y Compras)
4. customers, sales, sale_items (Clientes y Ventas ACID en mostrador)
5. inventory_movements (Kardex / Auditoría de movimientos)
Moneda: Bolivianos (Bs.).
=============================================================================
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# 1. ESQUEMAS DE USUARIOS Y AUTENTICACIÓN JWT (users)
# =============================================================================
class LoginRequest(BaseModel):
    username: str = Field(..., description="Nombre de usuario del operador")
    password: str = Field(..., description="Contraseña de acceso")


class HeartbeatRequest(BaseModel):
    username: str = Field(..., description="Usuario activo que reporta presencia")


class LogoutRequest(BaseModel):
    username: Optional[str] = Field(None, description="Usuario que cierra sesión")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    nombre_completo: str
    username: str
    email: Optional[str] = None
    rol: str
    activo: bool
    en_linea: Optional[bool] = False
    ultimo_acceso: Optional[datetime] = None
    fecha_creacion: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# 2. ESQUEMAS DE PRODUCTO (CATÁLOGO E INVENTARIO) (products)
# =============================================================================
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


# =============================================================================
# 3. ESQUEMAS DE PROVEEDORES Y COMPRAS (suppliers, purchases)
# =============================================================================
class SupplierBase(BaseModel):
    razon_social: str = Field(..., description="Nombre o Razón Social de la empresa proveedora")
    nit: str = Field(..., description="NIT del proveedor en Bolivia")
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierOut(SupplierBase):
    id: int
    activo: bool

    class Config:
        from_attributes = True


class PurchaseItemCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="ID del producto reabastecido")
    quantity: int = Field(..., gt=0, description="Cantidad de cajas o fardos")
    unit_price: float = Field(..., gt=0, description="Costo unitario de compra en Bs.")


class PurchaseCreate(BaseModel):
    supplier_id: int = Field(..., gt=0, description="ID del proveedor mayorista")
    numero_factura: Optional[str] = Field("FAC-001", description="Número de factura o nota de entrega")
    items: List[PurchaseItemCreate] = Field(..., min_length=1, description="Lista de mercancía recibida")


class PurchaseItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class PurchaseOut(BaseModel):
    id: int
    numero_factura: Optional[str] = None
    supplier_id: Optional[int] = None
    total_amount: float
    created_at: datetime
    items: Optional[List[PurchaseItemOut]] = []

    class Config:
        from_attributes = True


# =============================================================================
# 4. ESQUEMAS DE CLIENTES Y VENTAS (customers, sales, sale_items)
# =============================================================================
class CustomerBase(BaseModel):
    nombre_razon_social: str = Field(..., description="Nombre o razón social del cliente")
    nit_ci: str = Field(..., description="NIT o CI")
    telefono: Optional[str] = None
    tipo_cliente: Optional[str] = "Mayorista Mostrador"


class CustomerCreate(CustomerBase):
    pass


class CustomerOut(CustomerBase):
    id: int
    activo: bool

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


# =============================================================================
# 5. ESQUEMAS DE KARDEX Y MOVIMIENTOS DE INVENTARIO (inventory_movements)
# =============================================================================
class KardexMovementOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = "Producto"
    product_sku: Optional[str] = "SKU"
    movement_type: str  # ENTRADA | SALIDA | AJUSTE
    quantity: int
    previous_quantity: int
    final_quantity: int
    document_reference: str
    movement_date: datetime

    class Config:
        from_attributes = True
