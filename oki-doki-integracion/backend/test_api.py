"""
Test suite de verificación para la refactorización ACID de Oki Doki (Distribol).
"""
from database import SessionLocal, init_db
from models import Producto, Venta, Compra
from main import (
    login,
    listar_productos,
    registrar_producto,
    registrar_venta,
    registrar_compra,
    obtener_kpis,
    verificar_token_acceso
)
from schemas import (
    LoginRequest,
    ProductoCreate,
    VentaCreate,
    ItemVentaCreate,
    CompraCreate,
    ItemCompraCreate
)
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

def test_acid_suite():
    print("=================================================================")
    print(" INICIANDO TEST SUITE DE REFACTORIZACION ACID - OKI DOKI")
    print("=================================================================")

    init_db()
    db = SessionLocal()

    try:
        res_login = login(LoginRequest(username="admin", password="123456"), db=db)
        token = res_login.access_token
        assert token is not None

        usuario_actual = verificar_token_acceso(
            auth=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            db=db
        )
        assert usuario_actual.username == "admin"

        prods = listar_productos(db=db)
        assert len(prods) >= 8
        prod_test = prods[0]

        stock_inicial = prod_test.stock
        cant_compra = 10
        res_compra = registrar_compra(
            CompraCreate(
                proveedor="Industrias Fino S.A.",
                items=[
                    ItemCompraCreate(
                        producto_id=prod_test.id,
                        cantidad=cant_compra
                    )
                ]
            ),
            usuario_actual=usuario_actual,
            db=db
        )
        assert res_compra.id is not None
        db.refresh(prod_test)
        assert prod_test.stock == stock_inicial + cant_compra

        stock_antes_vta = prod_test.stock
        cant_vta = 5
        res_vta = registrar_venta(
            VentaCreate(
                cliente="Abarrotes El Carmen",
                items=[
                    ItemVentaCreate(
                        producto_id=prod_test.id,
                        cantidad=cant_vta
                    )
                ]
            ),
            usuario_actual=usuario_actual,
            db=db
        )
        assert res_vta.id is not None
        db.refresh(prod_test)
        assert prod_test.stock == stock_antes_vta - cant_vta

        stock_antes_fallo = prod_test.stock
        try:
            registrar_venta(
                VentaCreate(
                    cliente="Cliente Excedido",
                    items=[
                        ItemVentaCreate(
                            producto_id=prod_test.id,
                            cantidad=99999
                        )
                    ]
                ),
                usuario_actual=usuario_actual,
                db=db
            )
            assert False, "Debió fallar con 400"
        except HTTPException as e:
            assert e.status_code == 400

        db.refresh(prod_test)
        assert prod_test.stock == stock_antes_fallo

        kpis = obtener_kpis(db=db)
        assert kpis.total_skus >= 8

        print(" [EXITO] PRUEBAS ACID CONFIRMADAS AL 100%")
        print("=================================================================")
    finally:
        db.close()

if __name__ == "__main__":
    test_acid_suite()
