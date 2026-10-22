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
        # 1. Login y JWT
        print("\n[1] Autenticacion:")
        res_login = login(LoginRequest(username="admin", password="123456"), db=db)
        token = res_login.access_token
        assert token is not None
        print(f" -> OK: Token JWT generado ({res_login.username})")

        usuario_actual = verificar_token_acceso(
            auth=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            db=db
        )
        assert usuario_actual.username == "admin"

        # 2. Catalogo Inicial
        print("\n[2] Catalogo Inicial:")
        prods = listar_productos(db=db)
        assert len(prods) >= 8
        prod_test = prods[0]
        print(f" -> OK: {len(prods)} productos. Test con '{prod_test.nombre}' (Stock actual: {prod_test.stock})")

        # 3. Compra ACID (Aumento de stock)
        print("\n[3] Compra Mayorista (ACID - Aumento de Stock):")
        stock_inicial = prod_test.stock
        cant_compra = 20
        res_compra = registrar_compra(
            CompraCreate(
                proveedor="Industrias Fino S.A. - Planta Warnes",
                numero_factura="FAC-88412",
                items=[
                    ItemCompraCreate(
                        producto_id=prod_test.id,
                        cantidad=cant_compra,
                        precio_compra_bs=120.00
                    )
                ]
            ),
            usuario_actual=usuario_actual,
            db=db
        )
        assert res_compra.id is not None
        db.refresh(prod_test)
        assert prod_test.stock == stock_inicial + cant_compra
        print(f" -> OK: Compra #{res_compra.id} registrada. Total: Bs. {res_compra.total_bs:.2f}")
        print(f"    Stock subio de {stock_inicial} a {prod_test.stock} {prod_test.unidad}")

        # 4. Venta ACID Exitosa (Descuento de stock en tiempo real)
        print("\n[4] Venta Mostrador (ACID - Descuento de Stock):")
        stock_antes_vta = prod_test.stock
        cant_vta = 15
        res_vta = registrar_venta(
            VentaCreate(
                cliente="Supermercado Mayorista El Sol - El Alto",
                nit_ci="847291014",
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
        print(f" -> OK: Venta {res_vta.codigo_comprobante} registrada. Total: Bs. {res_vta.total_bs:.2f}")
        print(f"    Stock descontado de {stock_antes_vta} a {prod_test.stock} {prod_test.unidad}")

        # 5. Venta Fallida por Stock Insuficiente (ACID Rollback)
        print("\n[5] Venta con Stock Insuficiente (ACID Rollback):")
        stock_antes_fallo = prod_test.stock
        solicitud_excesiva = stock_antes_fallo + 500

        try:
            registrar_venta(
                VentaCreate(
                    cliente="Cliente Excedido",
                    nit_ci="123",
                    items=[
                        ItemVentaCreate(
                            producto_id=prod_test.id,
                            cantidad=solicitud_excesiva
                        )
                    ]
                ),
                usuario_actual=usuario_actual,
                db=db
            )
            assert False, "Debio fallar con 400 Bad Request"
        except HTTPException as e:
            assert e.status_code == 400
            print(f" -> OK: Interceptado HTTP 400: {e.detail}")

        # Comprobar que el stock no cambio debido al rollback
        db.refresh(prod_test)
        assert prod_test.stock == stock_antes_fallo
        print(f" -> OK: Verificado Rollback ACID. Stock intacto en {prod_test.stock} {prod_test.unidad}.")

        # 6. KPIs
        print("\n[6] Métricas y KPIs:")
        kpis = obtener_kpis(db=db)
        print(f" -> OK: SKUs: {kpis.total_skus} | Stock global: {kpis.total_stock} | Valor: Bs. {kpis.valor_inventario_bs:.2f}")

        print("\n [EXITO] TODAS LAS PRUEBAS ACID Y MODELOS PASARON AL 100%")
        print("=================================================================")

    finally:
        db.close()

if __name__ == "__main__":
    test_acid_suite()
