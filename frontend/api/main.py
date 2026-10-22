"""
=============================================================================
API ERP MAYORISTA "OKI DOKI" (DISTRIBOL) - FASTAPI & SQLALCHEMY
=============================================================================
MVP de Compra-Venta e Inventario Mayorista con FastAPI, SQLAlchemy,
Supabase PostgreSQL / SQLite y Autenticación JWT.
Regla de negocio: Sin transportistas. Transacciones atómicas (ACID).
Moneda: Bolivianos (Bs.).
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
    title="API ERP Oki Doki (Distribol) - Supabase DB",
    version="2.0.0",
    description="MVP de Compra-Venta e Inventario Mayorista con FastAPI, SQLAlchemy, Supabase PostgreSQL y JWT"
)

# Configuración de CORS permitiendo orígenes cruzados para la integración con Frontend
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

# Semilla automática de productos mayoristas Oki Doki si la base de datos está vacía
def seed_initial_products():
    db = SessionLocal()
    try:
        # 1. Crear usuario admin inicial si no existe
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin_user:
            admin_user = models.User(
                nombre_completo="Administrador General de Almacén",
                username="admin",
                email="admin@okidoki.bo",
                password_hash="123456",
                rol="Administrador",
                activo=True
            )
            db.add(admin_user)
            db.commit()

        # 2. Precargar productos de consumo masivo en Bolivia
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
    except Exception as e:
        db.rollback()
        print(f"Aviso durante seed: {e}")
    finally:
        db.close()

try:
    seed_initial_products()
except Exception as e:
    print(f"Seed ya ejecutado: {e}")

# Función auxiliar para validar el Token JWT
def verificar_jwt(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token JWT no proporcionado")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=403, detail="Token JWT inválido o expirado")


@app.get("/", tags=["Información"])
def raiz():
    return {
        "empresa": "Distribuidora Mayorista Oki Doki (Distribol)",
        "sistema": "ERP Compra-Venta e Inventario Mayorista (Supabase / SQLAlchemy ACID)",
        "moneda": "Bolivianos (Bs.)",
        "estado": "Operativo",
        "restriccion_logistica": "Venta y despacho directo en almacén central. Cero transportistas.",
        "documentacion": "/docs"
    }


# =============================================================================
# 1. AUTENTICACIÓN JWT
# =============================================================================
@app.post("/api/v1/auth/login", tags=["Seguridad"])
def login(credenciales: schemas.LoginRequest):
    if credenciales.username == "admin" and credenciales.password == "123456":
        payload = {
            "sub": credenciales.username,
            "rol": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(hours=2)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Credenciales inválidas")


# =============================================================================
# 2. CATÁLOGO E INVENTARIO (Rutas compatibles: /products y /productos)
# =============================================================================
@app.get("/api/v1/products", response_model=List[schemas.ProductOut], tags=["Inventario"])
@app.get("/api/v1/productos", response_model=List[schemas.ProductOut], tags=["Inventario"])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).order_by(models.Product.id.asc()).all()


@app.post("/api/v1/products", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED, tags=["Inventario"])
@app.post("/api/v1/productos", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED, tags=["Inventario"])
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    if authorization:
        verificar_jwt(authorization)

    db_product = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if db_product:
        raise HTTPException(status_code=400, detail="El SKU ya existe en el inventario de Oki Doki")

    new_product = models.Product(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # Registrar movimiento inicial en Kardex
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
# 3. TRANSACCIÓN ATÓMICA DE VENTA (CHECKOUT ACID)
# =============================================================================
@app.post("/api/v1/sales/checkout", response_model=schemas.SaleOut, status_code=status.HTTP_201_CREATED, tags=["Ventas"])
@app.post("/api/v1/ventas", response_model=schemas.SaleOut, status_code=status.HTTP_201_CREATED, tags=["Ventas"])
def checkout_sale(
    sale_in: schemas.SaleCreate,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    if authorization:
        verificar_jwt(authorization)

    if not sale_in.items:
        raise HTTPException(status_code=400, detail="La orden de venta no contiene productos")

    total = 0.0
    items_to_create = []

    try:
        # Validación y descuento de stock en tiempo real
        for item in sale_in.items:
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto con ID {item.product_id} no encontrado")

            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente para '{product.name}'. Solicitado: {item.quantity}, Disponible: {product.stock}"
                )

            # Fotografía para Kardex
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

        # Generar código comprobante único
        count_ventas = db.query(models.Sale).count() + 1
        vouch = f"VTA-{datetime.now().strftime('%Y%m%d')}-{count_ventas:04d}"

        # Registrar cabecera de la venta
        db_sale = models.Sale(total_amount=round(total, 2), voucher_code=vouch)
        db.add(db_sale)
        db.flush()  # Obtiene db_sale.id sin hacer commit definitivo

        # Registrar detalle de ítems y movimiento en Kardex
        for detail in items_to_create:
            db_detail = models.SaleItem(
                sale_id=db_sale.id,
                product_id=detail["product_id"],
                quantity=detail["quantity"],
                unit_price=detail["unit_price"]
            )
            db.add(db_detail)

            # Movimiento Kardex inmutable
            kardex_mov = models.InventoryMovement(
                product_id=detail["product_id"],
                movement_type="SALIDA",
                quantity=detail["quantity"],
                previous_quantity=detail["stock_previo"],
                final_quantity=detail["stock_final"],
                document_reference=f"VENTA {vouch}"
            )
            db.add(kardex_mov)

        # Confirmar la transacción atómica (ACID)
        db.commit()
        db.refresh(db_sale)

        # Notificación a Slack (Herramienta 2)
        notificar_slack(
            f"⚡ *Venta Mayorista ACID Confirmada*\n"
            f"• Comprobante: `{vouch}`\n"
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


@app.get("/api/v1/sales", response_model=List[schemas.SaleOut], tags=["Ventas"])
def list_sales(db: Session = Depends(get_db)):
    """Consulta el historial de ventas registradas en almacén."""
    return db.query(models.Sale).order_by(models.Sale.id.desc()).all()


# =============================================================================
# 4. INTEGRACIÓN DE HERRAMIENTAS EXTERNAS (SLACK WEBHOOKS)
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
    print(" INICIANDO ERP 'OKI DOKI' (DISTRIBOL) - FASTAPI & SUPABASE POSTGRESQL")
    print(" Puerto: 8000 | Venta de mostrador (Sin transportistas)")
    print("=" * 70 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
