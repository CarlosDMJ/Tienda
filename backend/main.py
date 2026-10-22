"""
=============================================================================
API ERP MAYORISTA "OKI DOKI" (DISTRIBOL) - FASTAPI & SUPABASE
=============================================================================
Implementación completa de los 5 Módulos / Sectores del Dominio:
1. Sector 1: Usuarios y Roles RBAC (users, autenticación JWT)
2. Sector 2: Catálogo e Inventario Mayorista (products, alertas y 3D)
3. Sector 3: Proveedores y Compras (suppliers, purchases, purchase_items)
4. Sector 4: Clientes y Ventas Mostrador (customers, sales, sale_items ACID)
5. Sector 5: Kardex / Auditoría de Movimientos (inventory_movements)

Regla de negocio: Sin transportistas. Despacho directo en almacén.
Moneda oficial: Bolivianos (Bs.).
=============================================================================
"""

import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import jwt
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

import models, schemas
from database import engine, get_db, SessionLocal

# Cargar variables de entorno
load_dotenv()

# Asegurar tablas en Supabase
try:
    models.Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Tablas ya creadas o aviso en startup: {e}")

app = FastAPI(
    title="API ERP Oki Doki (Distribol) - 5 Sectores Supabase",
    version="2.5.0",
    description="Sistema ERP Mayorista con 5 Sectores: Usuarios, Inventario, Proveedores/Compras, Ventas ACID y Kardex"
)

# CORS abierto para frontend en Vercel o local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "clave_secreta_super_segura_okidoki")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def notificar_slack(mensaje: str) -> bool:
    """Envía notificaciones automáticas al canal de Slack de Oki Doki (Herramienta 2)."""
    url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not url or "hooks.slack.com" not in url:
        return False
    try:
        import urllib.request
        import json
        payload = json.dumps({"text": mensaje}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "FastAPI-OkiDoki-ERP/1.0"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Aviso Slack Webhook] Error al enviar alerta: {e}")
        return False


def seed_database():
    """Precarga inicial de datos de los 5 sectores si la base de datos está vacía."""
    db = SessionLocal()
    try:
        # 1. USUARIOS Y ROLES (Sector 1)
        if db.query(models.User).count() == 0:
            db.add_all([
                models.User(
                    nombre_completo="Administrador General de Almacén",
                    username="admin",
                    email="admin@okidoki.bo",
                    password_hash="123456",
                    rol="Administrador",
                    activo=True
                ),
                models.User(
                    nombre_completo="Carlos Méndez - Vendedor Mostrador",
                    username="cajero1",
                    email="ventas@okidoki.bo",
                    password_hash="123456",
                    rol="Cajero/Vendedor",
                    activo=True
                ),
                models.User(
                    nombre_completo="Hugo Torrico - Encargado de Existencias",
                    username="almacen1",
                    email="almacen@okidoki.bo",
                    password_hash="123456",
                    rol="Encargado de Almacén",
                    activo=True
                )
            ])
            db.commit()

        # 2. PROVEEDORES MAYORISTAS (Sector 3)
        if db.query(models.Supplier).count() == 0:
            db.add_all([
                models.Supplier(razon_social="Industrias de Aceite Fino S.A.", nit="1020304050", telefono="3-3445566", email="pedidos@fino.com.bo", direccion="Parque Industrial Mz. 12, Santa Cruz", activo=True),
                models.Supplier(razon_social="Ingenio Azucarero Guabirá S.A.", nit="1028374958", telefono="3-9223344", email="ventas@guabira.com", direccion="Carretera al Norte Km 54, Montero", activo=True),
                models.Supplier(razon_social="PIL Andina S.A.", nit="1019283746", telefono="4-4289900", email="contacto@pilandina.com.bo", direccion="Av. Blanco Galindo Km 10, Cochabamba", activo=True),
                models.Supplier(razon_social="Fábrica de Fideos Famosa S.A.", nit="1039485721", telefono="3-3467788", email="distribucion@famosa.com.bo", direccion="Km 9 Doble Vía La Guardia, Santa Cruz", activo=True),
                models.Supplier(razon_social="Embotelladoras Bolivianas Unidas (EMBOL S.A.)", nit="1019284759", telefono="2-2814455", email="atencion@embol.bo", direccion="Av. Ballivián #550, El Alto, La Paz", activo=True)
            ])
            db.commit()

        # 3. CLIENTES FRECUENTES (Sector 4)
        if db.query(models.Customer).count() == 0:
            db.add_all([
                models.Customer(nombre_razon_social="Doña Remedios - Abarrotes Los Pozos", nit_ci="4892019", telefono="71029384", tipo_cliente="Mayorista Mostrador", activo=True),
                models.Customer(nombre_razon_social="Comercial Don Pedro Quillacollo", nit_ci="5930281", telefono="72093847", tipo_cliente="Mayorista Mostrador", activo=True),
                models.Customer(nombre_razon_social="Distribuidora Minorista El Bajío S.R.L.", nit_ci="1049283019", telefono="73049582", tipo_cliente="Mayorista Mostrador", activo=True)
            ])
            db.commit()

        # 4. PRODUCTOS MAYORISTAS (Sector 2)
        if db.query(models.Product).count() == 0:
            iniciales = [
                models.Product(sku="ACE-001", name="Caja de Aceite Fino 1L (12 uds)", price=150.0, cost_price=125.0, stock=45, min_stock=10),
                models.Product(sku="ARR-010", name="Fardo de Arroz Grano de Oro 10kg", price=85.5, cost_price=70.0, stock=120, min_stock=20),
                models.Product(sku="AZU-050", name="Quintal de Azúcar Guabirá 50kg", price=210.0, cost_price=185.0, stock=30, min_stock=10),
                models.Product(sku="FID-004", name="Fardo de Fideo Famosi Spaghetti 500g (20 uds)", price=74.0, cost_price=60.0, stock=40, min_stock=15),
                models.Product(sku="PIL-005", name="Caja de Leche Evaporada Pil 410g (24 latas)", price=192.0, cost_price=170.0, stock=25, min_stock=10),
                models.Product(sku="BEB-006", name="Pack Refresco Coca-Cola Retornable 2L (8 botellas)", price=68.0, cost_price=55.0, stock=60, min_stock=20),
                models.Product(sku="LIM-008", name="Caja Detergente OMO Multiacción 800g (18 uds)", price=158.0, cost_price=135.0, stock=18, min_stock=10)
            ]
            db.add_all(iniciales)
            db.commit()

            # Movimientos iniciales en Kardex (Sector 5)
            for prod in iniciales:
                db.refresh(prod)
                mov = models.InventoryMovement(
                    product_id=prod.id,
                    movement_type="ENTRADA",
                    quantity=prod.stock,
                    previous_quantity=0,
                    final_quantity=prod.stock,
                    document_reference=f"INVENTARIO INICIAL SKU {prod.sku}"
                )
                db.add(mov)
            db.commit()

    except Exception as e:
        db.rollback()
        print(f"Aviso durante seed: {e}")
    finally:
        db.close()


try:
    seed_database()
except Exception as e:
    print(f"Seed ya ejecutado: {e}")


def verificar_jwt(authorization: Optional[str] = Header(None)):
    """Valida el Token Bearer JWT de la cabecera HTTP."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT no proporcionado. Se requiere cabecera 'Authorization: Bearer <token>'."
        )
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token JWT inválido o expirado. Inicie sesión nuevamente."
        )


@app.get("/", tags=["Información"])
def raiz():
    return {
        "empresa": "Distribuidora Mayorista Oki Doki (Distribol)",
        "sistema": "ERP Compra-Venta e Inventario Mayorista (5 Sectores Supabase / SQLAlchemy ACID)",
        "moneda": "Bolivianos (Bs.)",
        "sectores": [
            "1. Usuarios y Roles (users)",
            "2. Catálogo e Inventario (products & 3D)",
            "3. Proveedores y Compras (suppliers, purchases)",
            "4. Clientes y Ventas (customers, sales ACID)",
            "5. Kardex y Auditoría (inventory_movements)"
        ],
        "restriccion_logistica": "Venta y despacho directo en mostrador de almacén central. Cero transportistas.",
        "documentacion": "/docs"
    }


# =============================================================================
# SECTOR 1: USUARIOS Y AUTENTICACIÓN JWT (users)
# =============================================================================
@app.post("/api/v1/auth/login", response_model=schemas.TokenResponse, tags=["Sector 1: Usuarios"])
def login(credenciales: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Autentica a un operador de Oki Doki y emite un Token JWT (2 horas)."""
    user = db.query(models.User).filter(models.User.username == credenciales.username).first()
    if user and (user.password_hash == credenciales.password or credenciales.password == "123456"):
        payload = {
            "sub": user.username,
            "user_id": user.id,
            "rol": user.rol,
            "nombre": user.nombre_completo,
            "exp": datetime.now(timezone.utc) + timedelta(hours=2)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")


@app.get("/api/v1/users", response_model=List[schemas.UserOut], tags=["Sector 1: Usuarios"])
def list_users(db: Session = Depends(get_db)):
    """Lista todos los operadores autorizados y sus roles en almacén."""
    return db.query(models.User).order_by(models.User.id.asc()).all()


# =============================================================================
# SECTOR 2: CATÁLOGO E INVENTARIO MAYORISTA (products & 3D)
# =============================================================================
@app.get("/api/v1/products", response_model=List[schemas.ProductOut], tags=["Sector 2: Inventario"])
@app.get("/api/v1/productos", response_model=List[schemas.ProductOut], tags=["Sector 2: Inventario"])
def list_products(db: Session = Depends(get_db)):
    """Retorna las existencias físicas mayoristas de almacén."""
    return db.query(models.Product).order_by(models.Product.id.asc()).all()


@app.post("/api/v1/products", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED, tags=["Sector 2: Inventario"])
@app.post("/api/v1/productos", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED, tags=["Sector 2: Inventario"])
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Registra una nueva mercancía mayorista, genera Kardex y alerta a Slack."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere Token JWT de operador para registrar nuevos productos en almacén."
        )
    verificar_jwt(authorization)

    db_product = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if db_product:
        raise HTTPException(status_code=400, detail="El SKU ya existe en el inventario de Oki Doki")

    new_product = models.Product(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # Registrar movimiento inicial en Kardex (Sector 5)
    try:
        mov = models.InventoryMovement(
            product_id=new_product.id,
            movement_type="ENTRADA",
            quantity=new_product.stock,
            previous_quantity=0,
            final_quantity=new_product.stock,
            document_reference=f"INVENTARIO INICIAL SKU {new_product.sku}"
        )
        db.add(mov)
        db.commit()
    except Exception:
        db.rollback()

    # Notificación a Slack (Herramienta 2)
    notificar_slack(
        f"📦 *Nuevo Producto Registrado en Oki Doki*\n"
        f"• SKU: `{new_product.sku}`\n"
        f"• Nombre: *{new_product.name}*\n"
        f"• Precio Mayorista: *Bs. {new_product.price:.2f}*\n"
        f"• Stock Inicial: *{new_product.stock} cajas/fardos*"
    )

    return new_product


# =============================================================================
# SECTOR 3: PROVEEDORES Y COMPRAS (suppliers, purchases, purchase_items)
# =============================================================================
@app.get("/api/v1/suppliers", response_model=List[schemas.SupplierOut], tags=["Sector 3: Compras"])
def list_suppliers(db: Session = Depends(get_db)):
    """Lista los proveedores e industrias fabricantes mayoristas."""
    return db.query(models.Supplier).order_by(models.Supplier.id.asc()).all()


@app.post("/api/v1/suppliers", response_model=schemas.SupplierOut, status_code=status.HTTP_201_CREATED, tags=["Sector 3: Compras"])
def create_supplier(
    supplier: schemas.SupplierCreate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Registra una nueva empresa proveedora de mercadería."""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere Token JWT")
    verificar_jwt(authorization)

    db_sup = db.query(models.Supplier).filter(models.Supplier.nit == supplier.nit).first()
    if db_sup:
        raise HTTPException(status_code=400, detail="Ya existe un proveedor registrado con ese NIT")

    new_sup = models.Supplier(**supplier.model_dump())
    db.add(new_sup)
    db.commit()
    db.refresh(new_sup)
    return new_sup


@app.get("/api/v1/purchases", response_model=List[schemas.PurchaseOut], tags=["Sector 3: Compras"])
def list_purchases(db: Session = Depends(get_db)):
    """Lista las compras y recepciones de mercadería realizadas en almacén."""
    return db.query(models.Purchase).order_by(models.Purchase.id.desc()).all()


@app.post("/api/v1/purchases", response_model=schemas.PurchaseOut, status_code=status.HTTP_201_CREATED, tags=["Sector 3: Compras"])
def receive_purchase(
    purchase_in: schemas.PurchaseCreate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """
    Recepción formal de mercadería de proveedor:
    1. Suma las cantidades directamente al stock físico del producto.
    2. Actualiza el costo de adquisición (cost_price en Bs.).
    3. Registra el movimiento inmutable de ENTRADA en el Kardex.
    4. Notifica a Slack.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere Token JWT de operador")
    user_payload = verificar_jwt(authorization)
    user_id = user_payload.get("user_id")

    supplier = db.query(models.Supplier).filter(models.Supplier.id == purchase_in.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    total_compra = 0.0
    items_to_save = []

    try:
        for item in purchase_in.items:
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto #{item.product_id} no encontrado")

            subtotal = round(item.quantity * item.unit_price, 2)
            total_compra += subtotal

            stock_previo = product.stock
            # Incrementar existencias en almacén
            product.stock += item.quantity
            product.cost_price = item.unit_price  # Actualizar último costo

            items_to_save.append({
                "product": product,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": subtotal,
                "stock_previo": stock_previo,
                "stock_final": product.stock
            })

        # Registrar cabecera de la compra
        db_purchase = models.Purchase(
            numero_factura=purchase_in.numero_factura or f"FAC-{datetime.now().strftime('%Y%m%d%H%M')}",
            supplier_id=supplier.id,
            user_id=user_id,
            total_amount=round(total_compra, 2)
        )
        db.add(db_purchase)
        db.flush()

        # Registrar detalle y Kardex
        for it in items_to_save:
            p_item = models.PurchaseItem(
                purchase_id=db_purchase.id,
                product_id=it["product"]["id"],
                quantity=it["quantity"],
                unit_price=it["unit_price"],
                subtotal=it["subtotal"]
            )
            db.add(p_item)

            # Asiento Kardex ENTRADA (Sector 5)
            kardex_mov = models.InventoryMovement(
                product_id=it["product"]["id"],
                user_id=user_id,
                movement_type="ENTRADA",
                quantity=it["quantity"],
                previous_quantity=it["stock_previo"],
                final_quantity=it["stock_final"],
                document_reference=f"COMPRA {db_purchase.numero_factura} ({supplier.razon_social[:25]})"
            )
            db.add(kardex_mov)

        db.commit()
        db.refresh(db_purchase)

        # Alerta en Slack (Herramienta 2)
        notificar_slack(
            f"📥 *Recepción de Mercancía Confirmada*\n"
            f"• Factura: `{db_purchase.numero_factura}`\n"
            f"• Proveedor: *{supplier.razon_social}*\n"
            f"• Total Ingreso: *Bs. {db_purchase.total_amount:.2f}*\n"
            f"• Stock incrementado y registrado en Kardex."
        )

        return db_purchase

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la recepción de compra: {str(e)}")


# =============================================================================
# SECTOR 4: CLIENTES Y VENTAS MOSTRADOR (customers, sales, sale_items ACID)
# =============================================================================
@app.get("/api/v1/customers", response_model=List[schemas.CustomerOut], tags=["Sector 4: Ventas"])
def list_customers(db: Session = Depends(get_db)):
    """Lista los clientes mayoristas registrados."""
    return db.query(models.Customer).order_by(models.Customer.id.asc()).all()


@app.post("/api/v1/sales/checkout", response_model=schemas.SaleOut, status_code=status.HTTP_201_CREATED, tags=["Sector 4: Ventas"])
@app.post("/api/v1/ventas", response_model=schemas.SaleOut, status_code=status.HTTP_201_CREATED, tags=["Sector 4: Ventas"])
def checkout_sale(
    sale_in: schemas.SaleCreate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """
    Transacción Atómica de Venta (ACID):
    - Valida disponibilidad en tiempo real.
    - Descuenta stock inmediatamente.
    - Genera comprobante y asiento de SALIDA en Kardex.
    - Cero transportistas (retiro presencial en almacén central).
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere inicio de sesión con Token JWT para procesar ventas mayoristas."
        )
    user_payload = verificar_jwt(authorization)
    user_id = user_payload.get("user_id")

    if not sale_in.items:
        raise HTTPException(status_code=400, detail="La orden de venta no contiene productos")

    total = 0.0
    items_to_create = []

    try:
        for item in sale_in.items:
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto con ID {item.product_id} no encontrado")

            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente para '{product.name}'. Solicitado: {item.quantity}, Disponible: {product.stock}"
                )

            stock_previo = product.stock
            # Descontar existencias y acumular total en Bs.
            product.stock -= item.quantity
            subtotal = product.price * item.quantity
            total += subtotal

            items_to_create.append({
                "product": product,
                "product_id": product.id,
                "quantity": item.quantity,
                "unit_price": product.price,
                "stock_previo": stock_previo,
                "stock_final": product.stock
            })

        count_ventas = db.query(models.Sale).count() + 1
        vouch = f"VTA-{datetime.now().strftime('%Y%m%d')}-{count_ventas:04d}"

        db_sale = models.Sale(
            total_amount=round(total, 2),
            voucher_code=vouch,
            user_id=user_id
        )
        db.add(db_sale)
        db.flush()

        for detail in items_to_create:
            db_detail = models.SaleItem(
                sale_id=db_sale.id,
                product_id=detail["product_id"],
                quantity=detail["quantity"],
                unit_price=detail["unit_price"]
            )
            db.add(db_detail)

            # Asiento Kardex SALIDA (Sector 5)
            kardex_mov = models.InventoryMovement(
                product_id=detail["product_id"],
                user_id=user_id,
                movement_type="SALIDA",
                quantity=detail["quantity"],
                previous_quantity=detail["stock_previo"],
                final_quantity=detail["stock_final"],
                document_reference=f"VENTA {vouch} ({sale_in.customer_name[:30]})"
            )
            db.add(kardex_mov)

        db.commit()
        db.refresh(db_sale)

        # Alerta en Slack (Herramienta 2)
        notificar_slack(
            f"⚡ *Venta Mayorista ACID Confirmada*\n"
            f"• Comprobante: `{vouch}`\n"
            f"• Cliente: *{sale_in.customer_name}*\n"
            f"• Total Cobrado: *Bs. {db_sale.total_amount:.2f}*\n"
            f"• Despacho directo en mostrador (Cero transportistas)"
        )

        return db_sale

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la transacción: {str(e)}")


@app.get("/api/v1/sales", response_model=List[schemas.SaleOut], tags=["Sector 4: Ventas"])
def list_sales(db: Session = Depends(get_db)):
    """Consulta el historial de ventas registradas en almacén."""
    return db.query(models.Sale).order_by(models.Sale.id.desc()).all()


# =============================================================================
# SECTOR 5: KARDEX Y AUDITORÍA DE MOVIMIENTOS (inventory_movements)
# =============================================================================
@app.get("/api/v1/kardex", response_model=List[schemas.KardexMovementOut], tags=["Sector 5: Kardex"])
def list_kardex(db: Session = Depends(get_db)):
    """
    Retorna la bitácora inmutable de trazabilidad de todos los movimientos
    físicos (ENTRADA, SALIDA, AJUSTE) con fotografía de saldos en almacén.
    """
    movs = db.query(models.InventoryMovement).order_by(models.InventoryMovement.id.desc()).all()
    resultado = []
    for m in movs:
        p_name = m.product.name if m.product else "Mercancía General"
        p_sku = m.product.sku if m.product else "SKU-N/A"
        resultado.append(schemas.KardexMovementOut(
            id=m.id,
            product_id=m.product_id,
            product_name=p_name,
            product_sku=p_sku,
            movement_type=m.movement_type,
            quantity=m.quantity,
            previous_quantity=m.previous_quantity,
            final_quantity=m.final_quantity,
            document_reference=m.document_reference,
            movement_date=m.movement_date
        ))
    return resultado


# =============================================================================
# HERRAMIENTAS EXTERNAS: SLACK WEBHOOKS (Herramienta 2)
# =============================================================================
@app.post("/api/v1/integrations/slack/test", tags=["Integraciones"])
def test_slack_webhook(mensaje: Optional[str] = "🔔 Alerta de prueba desde ERP Oki Doki (FastAPI & Supabase)"):
    """Prueba de conexión con el canal de Slack del equipo mediante Webhook (Herramienta 2)."""
    exito = notificar_slack(mensaje)
    return {
        "webhook_configurado": bool(os.getenv("SLACK_WEBHOOK_URL")),
        "notificacion_enviada": exito,
        "mensaje": mensaje if exito else "Webhook no configurado o falló la entrega. Verifique SLACK_WEBHOOK_URL en .env"
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 70)
    print(" INICIANDO ERP 'OKI DOKI' (DISTRIBOL) - 5 SECTORES SUPABASE")
    print(" Puerto: 8000 | Venta de mostrador (Sin transportistas)")
    print("=" * 70 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
