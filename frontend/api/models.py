"""
=============================================================================
SISTEMA ERP MAYORISTA "OKI DOKI" (DISTRIBOL) - MODELOS ORM (POSTGRESQL / SQLITE)
=============================================================================
Implementación de las 5 entidades base del dominio empresarial:
1. users (Usuarios y Roles RBAC)
2. products (Catálogo de Inventario Mayorista)
3. suppliers, purchases, purchase_items (Proveedores y Compras)
4. customers, sales, sale_items (Clientes y Ventas ACID en mostrador)
5. inventory_movements (Kardex / Auditoría de movimientos)
=============================================================================
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base


# =============================================================================
# 1. MÓDULO DE USUARIOS Y ROLES (users)
# =============================================================================
class User(Base):
    """Operadores del sistema ERP mayorista con control de acceso RBAC."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(30), default="Administrador", nullable=False)  # Administrador | Cajero/Vendedor | Encargado de Almacén
    activo = Column(Boolean, default=True, nullable=False)
    en_linea = Column(Boolean, default=False, nullable=True)
    ultimo_acceso = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)
    fecha_creacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sales = relationship("Sale", back_populates="user")
    purchases = relationship("Purchase", back_populates="user")
    movements = relationship("InventoryMovement", back_populates="user")


# =============================================================================
# 2. MÓDULO DE CATÁLOGO E INVENTARIO (products)
# =============================================================================
class Product(Base):
    """
    Productos de consumo masivo mayorista (cajas, fardos, paquetes, quintales).
    Precios e importes en Bolivianos (Bs.).
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    price = Column(Float, nullable=False)       # Precio de venta mayorista en Bs.
    cost_price = Column(Float, default=0.0)      # Precio de compra en Bs.
    stock = Column(Integer, default=0, nullable=False)  # Existencia física actual
    min_stock = Column(Integer, default=10, nullable=False)  # Umbral de alerta de reabastecimiento

    sale_items = relationship("SaleItem", back_populates="product")
    purchase_items = relationship("PurchaseItem", back_populates="product")
    movements = relationship("InventoryMovement", back_populates="product")


# =============================================================================
# 3. MÓDULO DE PROVEEDORES Y COMPRAS (suppliers, purchases, purchase_items)
# =============================================================================
class Supplier(Base):
    """Proveedores mayoristas de abarrotes (ej. Industrias Fino, Guabirá, PIL Andina)."""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    razon_social = Column(String(120), nullable=False)
    nit = Column(String(30), unique=True, nullable=False)
    telefono = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    direccion = Column(String(200), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)

    purchases = relationship("Purchase", back_populates="supplier")


class Purchase(Base):
    """Cabecera de compra / recepción de mercancía en almacén."""
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    numero_factura = Column(String(50), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    supplier = relationship("Supplier", back_populates="purchases")
    user = relationship("User", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseItem(Base):
    """Detalle de producto recibido en una compra."""
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")


# =============================================================================
# 4. MÓDULO DE CLIENTES Y VENTAS (customers, sales, sale_items)
# =============================================================================
class Customer(Base):
    """Clientes mayoristas atendidos directamente en mostrador/sucursal."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    nombre_razon_social = Column(String(120), nullable=False)
    nit_ci = Column(String(30), nullable=False, index=True)
    telefono = Column(String(20), nullable=True)
    tipo_cliente = Column(String(30), default="Mayorista Mostrador", nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    sales = relationship("Sale", back_populates="customer")


class Sale(Base):
    """
    Cabecera de venta / salida de almacén en mostrador.
    Sin transportistas ni módulos de choferes.
    """
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_amount = Column(Float, nullable=False)
    voucher_code = Column(String(50), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    customer = relationship("Customer", back_populates="sales")
    user = relationship("User", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")


class SaleItem(Base):
    """Detalle de producto vendido y descontado en tiempo real."""
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")


# =============================================================================
# 5. MÓDULO DE KARDEX / AUDITORÍA DE INVENTARIO (inventory_movements)
# =============================================================================
class InventoryMovement(Base):
    """
    Bitácora inmutable de auditoría y trazabilidad histórica de existencias.
    Tipos de operación: ENTRADA (por compra), SALIDA (por venta), AJUSTE (conteo físico).
    """
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    movement_type = Column(String(20), nullable=False)  # ENTRADA | SALIDA | AJUSTE
    quantity = Column(Integer, nullable=False)
    previous_quantity = Column(Integer, nullable=False)
    final_quantity = Column(Integer, nullable=False)
    document_reference = Column(String(100), nullable=False)  # Ej. VENTA VTA-001, COMPRA FAC-88
    movement_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="movements")
    user = relationship("User", back_populates="movements")
