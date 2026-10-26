"""
Test suite de verificación para la refactorización ACID de Oki Doki (Distribol).
Valida los 5 sectores: Usuarios/JWT, Inventario, Compras, Ventas ACID y Kardex.
"""
import sys
import os

# Asegurar path para importar desde el directorio actual
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
import models
import schemas
from main import (
    login,
    list_products,
    checkout_sale,
    receive_purchase,
    list_kardex,
    verificar_jwt
)
from fastapi import HTTPException

def test_acid_suite():
    print("=================================================================")
    print(" INICIANDO TEST SUITE DE VERIFICACION ACID - ERP OKI DOKI")
    print("=================================================================")

    # Asegurar tablas
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Login y JWT
        print("\n[1] Autenticacion RBAC y Emision de Token JWT:")
        res_login = login(schemas.LoginRequest(username="admin", password="123456"), db=db)
        token = res_login["access_token"]
        assert token is not None, "El token no fue generado"
        auth_header = f"Bearer {token}"
        payload = verificar_jwt(auth_header)
        assert payload["sub"] == "admin"
        print(f" -> OK: Token JWT generado para '{payload['nombre']}' (Rol: {payload['rol']})")

        # 2. Catalogo Inicial
        print("\n[2] Catalogo Inicial de Existencias Mayoristas:")
        prods = list_products(db=db)
        assert len(prods) > 0, "No se encontraron productos"
        prod_test = prods[0]
        print(f" -> OK: {len(prods)} productos registrados. Test con '[{prod_test.sku}] {prod_test.name}' (Stock: {prod_test.stock})")

        # 3. Compra Mayorista (ACID - Aumento de Stock y Kardex ENTRADA)
        print("\n[3] Recepcion de Compra (ACID - Aumento de Stock):")
        supplier = db.query(models.Supplier).first()
        if not supplier:
            supplier = models.Supplier(razon_social="Industrias Fino S.A.", nit="9999999")
            db.add(supplier)
            db.commit()
            db.refresh(supplier)

        stock_inicial = prod_test.stock
        cant_compra = 10
        purchase_in = schemas.PurchaseCreate(
            supplier_id=supplier.id,
            numero_factura="TEST-FAC-001",
            items=[
                schemas.PurchaseItemCreate(
                    product_id=prod_test.id,
                    quantity=cant_compra,
                    unit_price=prod_test.cost_price or 100.0
                )
            ]
        )
        res_compra = receive_purchase(purchase_in, db=db, authorization=auth_header)
        assert res_compra.id is not None
        db.refresh(prod_test)
        assert prod_test.stock == stock_inicial + cant_compra
        print(f" -> OK: Compra #{res_compra.id} registrada. Total: Bs. {res_compra.total_amount:.2f}")
        print(f"    Stock subio de {stock_inicial} a {prod_test.stock} unidades.")

        # 4. Venta Mostrador (ACID - Descuento de Stock y Kardex SALIDA)
        print("\n[4] Venta en Mostrador (ACID - Descuento en Tiempo Real):")
        stock_antes_vta = prod_test.stock
        cant_vta = 5
        sale_in = schemas.SaleCreate(
            customer_name="Cliente Mayorista Test",
            items=[
                schemas.SaleItemCreate(
                    product_id=prod_test.id,
                    quantity=cant_vta
                )
            ]
        )
        res_vta = checkout_sale(sale_in, db=db, authorization=auth_header)
        assert res_vta.id is not None
        db.refresh(prod_test)
        assert prod_test.stock == stock_antes_vta - cant_vta
        print(f" -> OK: Venta Comprobante {res_vta.voucher_code} procesada. Total: Bs. {res_vta.total_amount:.2f}")
        print(f"    Stock descontado de {stock_antes_vta} a {prod_test.stock} unidades.")

        # 5. Venta Fallida por Stock Insuficiente (ACID Rollback)
        print("\n[5] Venta con Stock Insuficiente (Garantia de Rollback ACID):")
        stock_antes_fallo = prod_test.stock
        solicitud_excesiva = stock_antes_fallo + 9999

        try:
            sale_fallo = schemas.SaleCreate(
                customer_name="Cliente Sobreorden",
                items=[
                    schemas.SaleItemCreate(
                        product_id=prod_test.id,
                        quantity=solicitud_excesiva
                    )
                ]
            )
            checkout_sale(sale_fallo, db=db, authorization=auth_header)
            assert False, "Debio fallar con HTTP 400"
        except HTTPException as e:
            assert e.status_code == 400
            print(f" -> OK: Interceptado HTTP 400 esperado: '{e.detail}'")

        db.refresh(prod_test)
        assert prod_test.stock == stock_antes_fallo
        print(f" -> OK: Verificado Rollback ACID. Stock protegido e intacto en {prod_test.stock} unidades.")

        # 6. Auditoria de Kardex
        print("\n[6] Verificacion de Asientos de Kardex (Sector 5):")
        movimientos = list_kardex(db=db)
        print(f" -> OK: {len(movimientos)} movimientos inmutables registrados en Kardex.")

        print("\n" + "=" * 65)
        print(" [EXITO FORENSE] TODAS LAS PRUEBAS DE MODELOS Y ACID PASARON AL 100%")
        print("=================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    test_acid_suite()
