# ERP Mayorista "Oki Doki" (Distribol) - MVP de Integración Empresarial

Sistema de Gestión de Almacén, Catálogo e Inventario Mayorista con control de salidas/ventas en tiempo real y autenticación por tokens JWT.

---

## 📌 Reglas de Negocio Estrictas de "Oki Doki"

1. **Giro del Negocio:** Comercialización y distribución mayorista de productos de consumo masivo (abarrotes, bebidas, lácteos, limpieza) empacados por cajas, fardos, paquetes o quintales.
2. **Moneda Oficial:** Bolivianos (`Bs.`). Todos los precios, cálculos y totales se operan y visualizan en `Bs.`.
3. **Restricción Crítica (Sin Transportistas):**
   - La distribuidora **NO cuenta con flota de reparto ni personal de entrega externa**.
   - Queda **estrictamente prohibido** incluir choferes, rutas de despacho, guías de transporte o comisiones de reparto.
   - Las ventas y entregas se realizan exclusivamente en mostrador de almacén central o por preventa con retiro en sucursal.
4. **Control de Stock en Tiempo Real:**
   - Al registrar una venta, el backend valida la existencia física en almacén (`stock >= cantidad`).
   - Si no alcanza, responde `400 Bad Request` indicando el faltante.
   - Si hay existencias, descuenta las unidades de forma inmediata e incrementa la bitácora de auditoría.

---

## 📂 Árbol de Directorios del Proyecto

```text
oki-doki-integracion/
├── backend/
│   ├── main.py              # API REST FastAPI, modelos Pydantic, seguridad JWT y lógica de negocio
│   ├── requirements.txt     # Dependencias: fastapi, uvicorn, pyjwt, pydantic
│   └── test_api.py          # Suite de pruebas automatizadas de validación
├── frontend/
│   ├── index.html           # Dashboard ERP administrativo estructurado
│   ├── styles.css           # Estilos corporativos (#2c3e50, #f39c12, #f4f6f9)
│   └── app.js               # Lógica con Fetch API, async/await y manejo de localStorage JWT
└── README.md                # Documentación técnica y guía de puesta en marcha
```

---

## 🛠️ Stack Tecnológico

* **Backend:**
  - Python 3.10+ / 3.11+
  - FastAPI (Framework web REST asíncrono)
  - Uvicorn (Servidor ASGI de alto rendimiento en puerto `8000`)
  - PyJWT (`HS256`, expiración a 2 horas)
  - Pydantic v2 (Validación estricta de esquemas)
  - CORSMiddleware (`allow_origins=["*"]`)
* **Frontend:**
  - HTML5 Semántico
  - CSS3 Moderno (Acentuación corporativa azul marino y ámbar)
  - Vanilla JavaScript ES6+ (Fetch API, async/await, sincronización reactiva de UI)

---

## 🔑 Credenciales de Prueba (MVP)

| Rol | Usuario | Contraseña | Validez del Token |
| :--- | :--- | :--- | :--- |
| **Jefe de Almacén e Inventarios** | `admin` | `123456` | 2 horas (`HS256`) |

---

## 📡 Especificación de Endpoints

| Método | Endpoint | Acceso | Tag | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Público | Seguridad | Genera el Token JWT al validar `username` y `password`. |
| `GET` | `/api/v1/productos` | Público | Inventario | Lista el inventario mayorista completo con precios en `Bs.` y stock. |
| `POST` | `/api/v1/productos` | **Protegido (JWT)** | Inventario | Registra nuevo lote/mercancía (`precio_mayorista > 0`, `stock >= 0`). |
| `POST` | `/api/v1/ventas` | **Protegido (JWT)** | Ventas | Venta de mostrador y descuento inmediato de stock. |
| `GET` | `/api/v1/ventas` | **Protegido (JWT)** | Ventas | Bitácora histórica de auditoría de salidas de almacén. |
| `GET` | `/docs` | Público | Documentación | Swagger UI interactivo generado por FastAPI. |

---

## 🚀 Guía de Instalación y Ejecución

### 1. Levantar el Backend (FastAPI + Uvicorn)

#### En Windows (PowerShell):
```powershell
# 1. Ingresar a la carpeta del backend
cd c:\xampp\htdocs\Diplomado\oki-doki-integracion\backend

# 2. (Opcional recomendado) Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar servidor FastAPI en el puerto 8000
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

#### En Linux / macOS (Bash):
```bash
cd oki-doki-integracion/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

El backend estará disponible en:
- API Base: `http://localhost:8000`
- Documentación Swagger UI: `http://localhost:8000/docs`

---

### 2. Levantar el Frontend

Al ser un frontend desacoplado en Vanilla JS, puedes abrirlo directamente o servirlo con cualquier servidor estático HTTP.

#### Opción A: Servidor HTTP integrado de Python (Recomendado para evitar bloqueos CORS por protocolo `file://`)
```powershell
# En otra terminal:
cd c:\xampp\htdocs\Diplomado\oki-doki-integracion\frontend
python -m http.server 3000
```
Abrir en el navegador: **`http://localhost:3000`**

#### Opción B: Mediante XAMPP Apache
Como el proyecto se ubica dentro de `c:\xampp\htdocs\Diplomado`, basta con iniciar el módulo Apache en el panel de XAMPP y acceder a:
**`http://localhost/Diplomado/oki-doki-integracion/frontend/`**

---

### 3. Ejecutar Pruebas Automatizadas
Para verificar el 100% de la lógica de negocio y las restricciones:
```powershell
cd c:\xampp\htdocs\Diplomado\oki-doki-integracion\backend
python test_api.py
```
