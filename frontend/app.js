/**
 * ==============================================================================
 * SISTEMA ERP MAYORISTA "OKI DOKI" (DISTRIBOL) - CONTROLADOR FRONTEND MODULAR
 * ==============================================================================
 * 5 SECTORES INDEPENDIENTES:
 * 1. Sector 1: Usuarios y Roles RBAC (users)
 * 2. Sector 2: Catálogo e Inventario Mayorista (products & 3D Three.js)
 * 3. Sector 3: Proveedores y Compras (suppliers, purchases)
 * 4. Sector 4: Clientes y Ventas Mostrador (customers, sales ACID)
 * 5. Sector 5: Kardex y Auditoría Inmutable (inventory_movements)
 *
 * INTEGRACIÓN DE LAS 6 HERRAMIENTAS:
 * 1. Devin AI | 2. Slack | 3. Vercel | 4. Comentera | 5. Gráficos 3D | 6. Supabase
 * ==============================================================================
 */

// Detección automática de entorno: Localhost vs Vercel Serverless
const DEFAULT_LOCAL_API = "http://127.0.0.1:8000/api/v1";

function obtenerApiUrl() {
  const custom = localStorage.getItem("custom_api_url");
  if (custom) return custom.replace(/\/+$/, "");
  if ((window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") && window.location.port === "3000") {
    return DEFAULT_LOCAL_API;
  }
  return "/api/v1";
}

const API_URL = obtenerApiUrl();

// Cache local de productos y proveedores
let productosCache = [];
let proveedoresCache = [];

// Variables globales del Visor 3D (Three.js)
let scene, camera, renderer, cubeMesh, edgeMesh, orbitControls;
let isSpinning = true;
let animFrameId = null;

// Inicialización general
document.addEventListener("DOMContentLoaded", async () => {
  await verificarEstadoSesion();
  await cargarProductos();
  verificarSaludBackend();
  initVisor3D();

  // Escuchar cambios en selector de venta
  const selectProd = document.getElementById("sale-product-select");
  const inputCant = document.getElementById("sale-quantity");
  if (selectProd) selectProd.addEventListener("change", () => {
    actualizarPreviewVenta();
    const id = parseInt(selectProd.value, 10);
    if (id) sincronizarProducto3D(id);
  });
  if (inputCant) inputCant.addEventListener("input", actualizarPreviewVenta);
});


// ==============================================================================
// NAVEGACIÓN MODULAR ENTRE LOS 5 SECTORES
// ==============================================================================
function mostrarSector(sectorId) {
  // Ocultar todos los sectores
  document.querySelectorAll(".sector-view").forEach(sec => sec.classList.remove("active"));
  document.querySelectorAll(".sector-tab").forEach(tab => tab.classList.remove("active"));

  // Activar el sector elegido
  const vistaActiva = document.getElementById(sectorId);
  if (vistaActiva) vistaActiva.classList.add("active");

  const tabActiva = document.querySelector(`.sector-tab[data-sector="${sectorId}"]`);
  if (tabActiva) tabActiva.classList.add("active");

  // Cargar datos específicos del sector seleccionado
  if (sectorId === "sector-inventario") {
    cargarProductos();
    setTimeout(() => {
      if (renderer && camera && scene) {
        const container = document.getElementById("canvas-container");
        if (container) {
          const w = container.clientWidth;
          const h = container.clientHeight || 280;
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setSize(w, h);
        }
      }
    }, 150);
  } else if (sectorId === "sector-ventas") {
    cargarProductos();
    cargarVentasHistorial();
  } else if (sectorId === "sector-compras") {
    cargarProveedores();
    cargarProductos();
  } else if (sectorId === "sector-kardex") {
    cargarKardex();
  } else if (sectorId === "sector-usuarios") {
    cargarUsuarios();
  }
}


// ==============================================================================
// SECTOR 2: CATÁLOGO E INVENTARIO MAYORISTA (products & 3D Three.js)
// ==============================================================================
async function cargarProductos() {
  const tbody = document.getElementById("inventory-tbody");
  const selectVenta = document.getElementById("sale-product-select");
  const selectCompra = document.getElementById("purchase-product-select");
  const badgeCount = document.getElementById("badge-count-prod");

  try {
    const respuesta = await fetch(`${API_URL}/products`);
    if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);

    const productos = await respuesta.json();
    productosCache = productos;

    if (badgeCount) badgeCount.textContent = productos.length;

    // 1. Llenar tabla del Sector 2
    if (tbody) {
      if (productos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 1.5rem; color: var(--muted);">No hay productos registrados en el almacén.</td></tr>`;
      } else {
        tbody.innerHTML = productos.map(p => {
          const badgeClass = p.stock > (p.min_stock || 10) ? "high" : "low";
          const precioBs = Number(p.price).toFixed(2);
          const costoBs = Number(p.cost_price || 0).toFixed(2);
          return `
            <tr>
              <td><strong>#${p.id}</strong></td>
              <td><span style="background: #f1f5f9; padding: 0.2rem 0.5rem; border-radius: 4px; font-family: monospace; font-weight: 700;">${p.sku}</span></td>
              <td><strong>${p.name}</strong></td>
              <td style="color: var(--muted);">Bs. ${costoBs}</td>
              <td><strong style="color: var(--primary);">Bs. ${precioBs}</strong></td>
              <td><span class="badge-stock ${badgeClass}">● ${p.stock} cajas/fardos</span></td>
              <td>
                <div style="display: flex; gap: 0.4rem;">
                  <button class="btn btn-outline btn-sm" onclick="seleccionarParaVenta(${p.id})">
                    🛒 Vender
                  </button>
                  <button class="btn btn-outline btn-sm" style="border-color: #3b82f6; color: #1d4ed8;" onclick="inspeccionarEn3D(${p.id})">
                    🎯 Ver 3D
                  </button>
                </div>
              </td>
            </tr>
          `;
        }).join("");
      }
    }

    // 2. Llenar selector de ventas (Sector 4)
    if (selectVenta) {
      const selectedPrev = selectVenta.value;
      selectVenta.innerHTML = `<option value="">-- Seleccione un producto del almacén --</option>` +
        productos.map(p => `
          <option value="${p.id}" ${p.id == selectedPrev ? 'selected' : ''}>
            [${p.sku}] ${p.name} - Bs. ${Number(p.price).toFixed(2)} (Stock: ${p.stock})
          </option>
        `).join("");
      actualizarPreviewVenta();
    }

    // 3. Llenar selector de compras (Sector 3)
    if (selectCompra) {
      selectCompra.innerHTML = `<option value="">-- Seleccione producto a ingresar --</option>` +
        productos.map(p => `
          <option value="${p.id}">
            [${p.sku}] ${p.name} (Stock Actual: ${p.stock})
          </option>
        `).join("");
    }

  } catch (error) {
    console.error("Error al cargar productos:", error);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 1.5rem;">⚠️ No se pudo conectar al servidor backend en <code>${API_URL}</code>.</td></tr>`;
    }
  }
}

async function guardarProducto() {
  const token = localStorage.getItem("jwt_token");
  const sku = document.getElementById("new-sku").value.trim();
  const name = document.getElementById("new-name").value.trim();
  const cost = parseFloat(document.getElementById("new-cost").value) || 0.0;
  const price = parseFloat(document.getElementById("new-price").value);
  const stock = parseInt(document.getElementById("new-stock").value, 10);

  if (!token) {
    mostrarAlerta("⚠️ Inicie sesión como operador para registrar productos.", "danger");
    mostrarSector("sector-usuarios");
    return;
  }

  if (!sku || !name || isNaN(price) || price <= 0 || isNaN(stock) || stock < 0) {
    mostrarAlerta("Por favor complete todos los campos requeridos (Precio > 0 y Stock >= 0).", "danger");
    return;
  }

  const payload = { sku, name, cost_price: cost, price, stock, min_stock: 10 };

  try {
    const respuesta = await fetch(`${API_URL}/products`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    const data = await respuesta.json();

    if (!respuesta.ok) {
      mostrarAlerta(`Error al guardar producto: ${data.detail || "Verifique los datos."}`, "danger");
      return;
    }

    mostrarAlerta(`✅ ¡Producto "${data.name}" (${data.sku}) registrado exitosamente con ${data.stock} unidades! Alerta enviada a Slack.`, "success");

    document.getElementById("new-sku").value = "";
    document.getElementById("new-name").value = "";

    await cargarProductos();
    sincronizarProducto3D(data.id);

  } catch (error) {
    mostrarAlerta("Error de conexión al guardar el producto.", "danger");
    console.error("Error:", error);
  }
}


// ==============================================================================
// VISOR 3D THREE.JS (HERRAMIENTA 5)
// ==============================================================================
function initVisor3D() {
  const container = document.getElementById("canvas-container");
  if (!container || typeof THREE === "undefined") return;

  scene = new THREE.Scene();
  const width = container.clientWidth || 400;
  const height = container.clientHeight || 280;
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
  camera.position.set(3.5, 2.5, 4.5);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.shadowMap.enabled = true;
  container.innerHTML = "";
  container.appendChild(renderer.domElement);

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
  dirLight.position.set(5, 10, 7);
  scene.add(dirLight);

  crearMallaEmpaque(2.2, 1.8, 1.6, 0xb4793b, 0x1e293b);

  if (typeof THREE.OrbitControls !== "undefined") {
    orbitControls = new THREE.OrbitControls(camera, renderer.domElement);
    orbitControls.enableDamping = true;
    orbitControls.dampingFactor = 0.05;
  }

  function animate() {
    animFrameId = requestAnimationFrame(animate);
    if (isSpinning && cubeMesh) {
      cubeMesh.rotation.y += 0.008;
      if (edgeMesh) edgeMesh.rotation.y = cubeMesh.rotation.y;
    }
    if (orbitControls) orbitControls.update();
    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener("resize", () => {
    if (!container || !renderer || !camera) return;
    const newW = container.clientWidth;
    const newH = container.clientHeight;
    camera.aspect = newW / newH;
    camera.updateProjectionMatrix();
    renderer.setSize(newW, newH);
  });
}

function crearMallaEmpaque(w, h, d, colorBox, colorEdge) {
  if (cubeMesh) scene.remove(cubeMesh);
  if (edgeMesh) scene.remove(edgeMesh);

  const geometry = new THREE.BoxGeometry(w, h, d);
  const material = new THREE.MeshStandardMaterial({
    color: colorBox,
    roughness: 0.5,
    metalness: 0.1
  });
  cubeMesh = new THREE.Mesh(geometry, material);
  scene.add(cubeMesh);

  const edgesGeometry = new THREE.EdgesGeometry(geometry);
  const edgesMaterial = new THREE.LineBasicMaterial({ color: colorEdge, linewidth: 2 });
  edgeMesh = new THREE.LineSegments(edgesGeometry, edgesMaterial);
  scene.add(edgeMesh);
}

function toggleGiro3D() {
  isSpinning = !isSpinning;
  const btn = document.getElementById("btn-toggle-spin");
  if (btn) btn.textContent = isSpinning ? "⏸️ Pausar Giro" : "▶️ Reanudar Giro";
}

function cambiarEmpaque3D(tipo) {
  const tagType = document.getElementById("canvas-product-type");
  const tagDim = document.getElementById("box-dimensions-label");

  if (tipo === "caja") {
    crearMallaEmpaque(2.2, 1.8, 1.6, 0xb4793b, 0x1e293b);
    if (tagType) tagType.textContent = "Caja Cartón Corrugado (12x1L)";
    if (tagDim) tagDim.textContent = "Dim: 40x30x25cm • ~12kg";
  } else if (tipo === "fardo") {
    crearMallaEmpaque(2.0, 2.5, 1.4, 0x38bdf8, 0x0369a1);
    if (tagType) tagType.textContent = "Fardo Termoencogible x24";
    if (tagDim) tagDim.textContent = "Dim: 45x35x30cm • ~10kg";
  } else if (tipo === "saco") {
    crearMallaEmpaque(1.8, 2.8, 1.2, 0xd4a373, 0x78350f);
    if (tagType) tagType.textContent = "Quintal / Saco Arpillera 50kg";
    if (tagDim) tagDim.textContent = "Dim: 50x40x90cm • 50kg";
  }
}

function sincronizarProducto3D(productId) {
  const prod = productosCache.find(p => p.id === productId);
  if (!prod) return;

  const skuTag = document.getElementById("canvas-product-sku");
  const typeTag = document.getElementById("canvas-product-type");

  if (skuTag) skuTag.textContent = `SKU: ${prod.sku}`;

  const lower = prod.name.toLowerCase();
  if (lower.includes("quintal") || lower.includes("azúcar") || lower.includes("azucar") || lower.includes("harina")) {
    cambiarEmpaque3D("saco");
    if (typeTag) typeTag.textContent = prod.name;
  } else if (lower.includes("fardo") || lower.includes("fideo") || lower.includes("arroz") || lower.includes("pack")) {
    cambiarEmpaque3D("fardo");
    if (typeTag) typeTag.textContent = prod.name;
  } else {
    cambiarEmpaque3D("caja");
    if (typeTag) typeTag.textContent = prod.name;
  }
}

function inspeccionarEn3D(productId) {
  sincronizarProducto3D(productId);
  mostrarSector("sector-inventario");
  mostrarAlerta(`📦 Inspeccionando en el Visor 3D el producto #${productId}. Puede rotarlo 360° con el mouse.`, "info");
}


// ==============================================================================
// SECTOR 4: CLIENTES Y VENTAS MOSTRADOR (ACID)
// ==============================================================================
function seleccionarParaVenta(productId) {
  mostrarSector("sector-ventas");
  const select = document.getElementById("sale-product-select");
  if (select) {
    select.value = productId;
    actualizarPreviewVenta();
    sincronizarProducto3D(productId);
  }
}

function actualizarPreviewVenta() {
  const select = document.getElementById("sale-product-select");
  const inputCant = document.getElementById("sale-quantity");
  const preview = document.getElementById("sale-preview-info");

  const prodId = parseInt(select?.value, 10);
  const cantidad = parseInt(inputCant?.value, 10) || 0;

  const prod = productosCache.find(p => p.id === prodId);
  if (!prod) {
    if (preview) preview.innerHTML = "Seleccione un ítem para calcular el importe en Bs. y verificar el stock.";
    return;
  }

  const subtotal = (prod.price * cantidad).toFixed(2);
  const remanente = prod.stock - cantidad;

  let remanenteTexto = `<span style="color: var(--success); font-weight: 700;">Stock restante tras venta: ${remanente} cajas/fardos.</span>`;
  if (remanente < 0) {
    remanenteTexto = `<span style="color: var(--danger); font-weight: 700;">⚠️ ¡Stock insuficiente! Faltan ${Math.abs(remanente)} cajas/fardos.</span>`;
  }

  if (preview) {
    preview.innerHTML = `
      Producto: <strong>${prod.name}</strong> | Precio Unitario: <strong>Bs. ${Number(prod.price).toFixed(2)}</strong> | 
      Total a cobrar: <strong style="color: var(--accent-hover); font-size: 0.95rem;">Bs. ${subtotal}</strong> | 
      ${remanenteTexto}
    `;
  }
}

async function registrarVenta() {
  const token = localStorage.getItem("jwt_token");
  const select = document.getElementById("sale-product-select");
  const inputCant = document.getElementById("sale-quantity");
  const inputCliente = document.getElementById("sale-customer-name");
  const btnProcess = document.getElementById("btn-process-sale");

  const productId = parseInt(select?.value, 10);
  const quantity = parseInt(inputCant?.value, 10);
  const cliente = inputCliente?.value.trim() || "Venta Mostrador Almacén";

  if (!token) {
    mostrarAlerta("⚠️ Se requiere inicio de sesión con Token JWT antes de procesar ventas mayoristas.", "danger");
    mostrarSector("sector-usuarios");
    return;
  }

  if (!productId) {
    mostrarAlerta("Seleccione un producto del almacén para despachar.", "danger");
    return;
  }
  if (!quantity || quantity <= 0) {
    mostrarAlerta("La cantidad a vender debe ser de al menos 1 caja/fardo.", "danger");
    return;
  }

  btnProcess.disabled = true;
  btnProcess.textContent = "⚡ Descontando Stock ACID...";

  const payload = {
    items: [{ product_id: productId, quantity: quantity }],
    customer_name: cliente
  };

  try {
    const respuesta = await fetch(`${API_URL}/sales/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    const data = await respuesta.json();

    if (!respuesta.ok) {
      mostrarAlerta(`⚠️ ${data.detail || "Error en la transacción de venta."}`, "danger");
      return;
    }

    const totalBs = Number(data.total_amount).toFixed(2);
    mostrarAlerta(`✅ ¡Venta confirmada (${data.voucher_code})! Total cobrado en mostrador: Bs. ${totalBs}. Stock descontado en tiempo real. Alerta enviada a Slack.`, "success");

    inputCant.value = 1;
    await cargarProductos();
    await cargarVentasHistorial();

  } catch (error) {
    mostrarAlerta("Error de comunicación con el backend al procesar la venta.", "danger");
  } finally {
    btnProcess.disabled = false;
    btnProcess.textContent = "⚡ Procesar Venta Mostrador";
  }
}

async function cargarVentasHistorial() {
  const tbody = document.getElementById("sales-history-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_URL}/sales`);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const ventas = await res.json();

    if (ventas.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 1.5rem; color: var(--muted);">No hay comprobantes de venta registrados aún.</td></tr>`;
      return;
    }

    tbody.innerHTML = ventas.map(v => {
      const fecha = new Date(v.created_at).toLocaleString("es-BO");
      const cantItems = v.items ? v.items.length : 1;
      return `
        <tr>
          <td><strong>#${v.id}</strong></td>
          <td><span style="font-family: monospace; font-weight: 700; color: #1e40af; background: #eff6ff; padding: 0.2rem 0.5rem; border-radius: 4px;">${v.voucher_code || 'VTA-S/N'}</span></td>
          <td style="color: var(--muted); font-size: 0.78rem;">${fecha}</td>
          <td><strong style="color: var(--success);">Bs. ${Number(v.total_amount).toFixed(2)}</strong></td>
          <td>${cantItems} producto(s)</td>
          <td><span class="badge-stock high">● Despachado</span></td>
        </tr>
      `;
    }).join("");
  } catch (e) {
    console.error("Error al cargar ventas:", e);
  }
}


// ==============================================================================
// SECTOR 3: PROVEEDORES Y COMPRAS (REABASTECIMIENTO)
// ==============================================================================
async function cargarProveedores() {
  const tbody = document.getElementById("suppliers-tbody");
  const select = document.getElementById("purchase-supplier-select");

  try {
    const res = await fetch(`${API_URL}/suppliers`);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const proveedores = await res.json();
    proveedoresCache = proveedores;

    if (tbody) {
      tbody.innerHTML = proveedores.map(s => `
        <tr>
          <td><strong>#${s.id}</strong></td>
          <td><strong>${s.razon_social}</strong></td>
          <td><code>${s.nit}</code></td>
          <td>${s.telefono || 'S/N'}</td>
          <td>${s.email || 'S/N'}</td>
          <td><span class="badge-stock high">● Activo</span></td>
        </tr>
      `).join("");
    }

    if (select) {
      select.innerHTML = `<option value="">-- Seleccione proveedor mayorista --</option>` +
        proveedores.map(s => `<option value="${s.id}">${s.razon_social} (NIT: ${s.nit})</option>`).join("");
    }

  } catch (e) {
    console.error("Error al cargar proveedores:", e);
  }
}

async function guardarProveedor() {
  const token = localStorage.getItem("jwt_token");
  const razon = document.getElementById("sup-razon").value.trim();
  const nit = document.getElementById("sup-nit").value.trim();
  const tel = document.getElementById("sup-tel").value.trim();

  if (!token) {
    mostrarAlerta("⚠️ Inicie sesión como operador para registrar proveedores.", "danger");
    mostrarSector("sector-usuarios");
    return;
  }
  if (!razon || !nit) {
    mostrarAlerta("Razón Social y NIT son obligatorios.", "danger");
    return;
  }

  try {
    const res = await fetch(`${API_URL}/suppliers`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ razon_social: razon, nit: nit, telefono: tel })
    });
    const d = await res.json();
    if (!res.ok) {
      mostrarAlerta(`Error al crear proveedor: ${d.detail || 'Verifique NIT'}`, "danger");
      return;
    }
    mostrarAlerta(`✅ Proveedor "${d.razon_social}" registrado con éxito.`, "success");
    document.getElementById("sup-razon").value = "";
    document.getElementById("sup-nit").value = "";
    document.getElementById("sup-tel").value = "";
    await cargarProveedores();
  } catch (e) {
    mostrarAlerta("Error de conexión al registrar proveedor.", "danger");
  }
}

async function registrarCompra() {
  const token = localStorage.getItem("jwt_token");
  const supId = parseInt(document.getElementById("purchase-supplier-select")?.value, 10);
  const prodId = parseInt(document.getElementById("purchase-product-select")?.value, 10);
  const fact = document.getElementById("purchase-invoice")?.value.trim() || "FAC-INGRESO";
  const cant = parseInt(document.getElementById("purchase-quantity")?.value, 10);
  const costo = parseFloat(document.getElementById("purchase-unit-cost")?.value);

  if (!token) {
    mostrarAlerta("⚠️ Inicie sesión como operador para registrar ingresos de compras.", "danger");
    mostrarSector("sector-usuarios");
    return;
  }
  if (!supId || !prodId || !cant || cant <= 0 || isNaN(costo) || costo <= 0) {
    mostrarAlerta("Seleccione proveedor, producto y verifique cantidad y costo unitario.", "danger");
    return;
  }

  const payload = {
    supplier_id: supId,
    numero_factura: fact,
    items: [{ product_id: prodId, quantity: cant, unit_price: costo }]
  };

  try {
    const res = await fetch(`${API_URL}/purchases`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      mostrarAlerta(`Error al recibir compra: ${data.detail || 'Verifique los datos'}`, "danger");
      return;
    }

    mostrarAlerta(`✅ ¡Recepción confirmada (${data.numero_factura})! Ingresaron ${cant} unidades al inventario físico. Kardex actualizado.`, "success");
    await cargarProductos();
    mostrarSector("sector-inventario");

  } catch (e) {
    mostrarAlerta("Error de conexión al procesar la compra.", "danger");
  }
}


// ==============================================================================
// SECTOR 5: KARDEX Y AUDITORÍA DE MOVIMIENTOS (inventory_movements)
// ==============================================================================
async function cargarKardex() {
  const tbody = document.getElementById("kardex-tbody");
  const statCount = document.getElementById("stat-kardex-count");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_URL}/kardex`);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const movs = await res.json();

    if (statCount) statCount.textContent = movs.length;

    if (movs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 2rem; color: var(--muted);">No hay movimientos registrados en el Kardex.</td></tr>`;
      return;
    }

    tbody.innerHTML = movs.map(m => {
      const fecha = new Date(m.movement_date).toLocaleString("es-BO");
      const tipoClass = m.movement_type.toLowerCase();
      const signo = m.movement_type === "ENTRADA" ? "+" : (m.movement_type === "SALIDA" ? "-" : "");
      return `
        <tr>
          <td><strong>#${m.id}</strong></td>
          <td><span class="badge-type ${tipoClass}">${m.movement_type}</span></td>
          <td><code>${m.product_sku || 'SKU'}</code></td>
          <td><strong>${m.product_name}</strong></td>
          <td><strong style="color: ${m.movement_type === 'ENTRADA' ? 'var(--success)' : 'var(--danger)'};">${signo}${m.quantity}</strong></td>
          <td>${m.previous_quantity}</td>
          <td><strong>${m.final_quantity}</strong></td>
          <td style="font-family: monospace; font-size: 0.78rem; color: #475569;">${m.document_reference}</td>
          <td style="color: var(--muted); font-size: 0.75rem;">${fecha}</td>
        </tr>
      `;
    }).join("");

  } catch (e) {
    console.error("Error al cargar Kardex:", e);
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--danger); padding: 1.5rem;">Error al cargar bitácora de Kardex.</td></tr>`;
  }
}


// ==============================================================================
// SECTOR 1: USUARIOS Y AUTENTICACIÓN JWT (users)
// ==============================================================================
async function iniciarSesion() {
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");
  const btnLogin = document.getElementById("btn-login");

  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (!username || !password) {
    mostrarAlerta("Por favor ingrese usuario y contraseña.", "danger");
    return;
  }

  btnLogin.disabled = true;
  btnLogin.textContent = "⌛ Autenticando...";

  try {
    const respuesta = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await respuesta.json();

    if (!respuesta.ok) {
      mostrarAlerta(`Error de acceso: ${data.detail || "Credenciales incorrectas"}`, "danger");
      return;
    }

    localStorage.setItem("jwt_token", data.access_token);
    localStorage.setItem("jwt_user", username);
    localStorage.removeItem("jwt_logged_out");

    mostrarAlerta(`¡Bienvenido, ${username}! Token JWT activo guardado en localStorage.`, "success");
    await verificarEstadoSesion();

  } catch (error) {
    mostrarAlerta("No fue posible conectar con el servidor backend.", "danger");
  } finally {
    btnLogin.disabled = false;
    btnLogin.textContent = "⚡ Iniciar Sesión y Guardar Token";
  }
}

function cerrarSesion() {
  localStorage.removeItem("jwt_token");
  localStorage.removeItem("jwt_user");
  localStorage.setItem("jwt_logged_out", "true");
  verificarEstadoSesion();
  mostrarAlerta("Sesión cerrada. Token JWT eliminado.", "info");
}

async function verificarEstadoSesion() {
  let token = localStorage.getItem("jwt_token");
  let user = localStorage.getItem("jwt_user") || "admin";
  const loggedOut = localStorage.getItem("jwt_logged_out");

  if (!token && !loggedOut) {
    try {
      const resp = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: "admin", password: "123456" })
      });
      if (resp.ok) {
        const d = await resp.json();
        token = d.access_token;
        user = "admin";
        localStorage.setItem("jwt_token", token);
        localStorage.setItem("jwt_user", user);
      }
    } catch (e) {
      console.warn("Auto-login inicial no disponible:", e);
    }
  }

  const loginBox = document.getElementById("login-box");
  const userInfoBox = document.getElementById("user-info-box");
  const sessionBadge = document.getElementById("session-badge");
  const jwtStatusPill = document.getElementById("jwt-status");
  const loggedUser = document.getElementById("logged-user");

  if (token) {
    if (loginBox) loginBox.style.display = "none";
    if (userInfoBox) userInfoBox.style.display = "block";
    if (sessionBadge) {
      sessionBadge.textContent = "✅ JWT Activo";
      sessionBadge.style.color = "#10b981";
    }
    if (jwtStatusPill) {
      jwtStatusPill.textContent = `Sesión: ${user} (JWT)`;
      jwtStatusPill.style.borderColor = "rgba(16, 185, 129, 0.5)";
      jwtStatusPill.style.color = "#10b981";
    }
    if (loggedUser) loggedUser.textContent = user;
  } else {
    if (loginBox) loginBox.style.display = "block";
    if (userInfoBox) userInfoBox.style.display = "none";
    if (sessionBadge) {
      sessionBadge.textContent = "Sin Sesión";
      sessionBadge.style.color = "#f59e0b";
    }
    if (jwtStatusPill) {
      jwtStatusPill.textContent = "Sesión: Sin Token";
      jwtStatusPill.style.borderColor = "rgba(245, 158, 11, 0.5)";
      jwtStatusPill.style.color = "#f59e0b";
    }
  }
}

async function cargarUsuarios() {
  const tbody = document.getElementById("users-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_URL}/users`);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const users = await res.json();

    tbody.innerHTML = users.map(u => `
      <tr>
        <td><strong>#${u.id}</strong></td>
        <td><strong>${u.nombre_completo}</strong></td>
        <td><code>${u.username}</code></td>
        <td><span style="background: #f1f5f9; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700; color: #1e293b;">${u.rol}</span></td>
        <td>${u.email || 'S/N'}</td>
        <td><span class="badge-stock high">● Habilitado</span></td>
      </tr>
    `).join("");
  } catch (e) {
    console.error("Error al cargar usuarios:", e);
  }
}


// ==============================================================================
// INTEGRACIONES DE HERRAMIENTAS (SLACK & COMENTERA)
// ==============================================================================
async function probarSlackWebhook() {
  mostrarAlerta("Enviando notificación de prueba al canal de Slack...", "info");
  try {
    const res = await fetch(`${API_URL}/integrations/slack/test`, { method: "POST" });
    const data = await res.json();
    if (data.notificacion_enviada) {
      mostrarAlerta("🔔 ¡Notificación de prueba enviada con éxito a Slack!", "success");
    } else {
      mostrarAlerta(`Aviso Slack: ${data.mensaje}`, "info");
    }
  } catch (err) {
    mostrarAlerta("No fue posible comunicarse con el servicio de alertas Slack.", "danger");
  }
}

function abrirModalComentera() {
  const modal = document.getElementById("modal-comentera");
  if (modal) modal.style.display = "flex";
}

function cerrarModalComentera(event) {
  if (event && event.target && event.target.id !== "modal-comentera") return;
  const modal = document.getElementById("modal-comentera");
  if (modal) modal.style.display = "none";
}

function agregarComentarioVisual() {
  const input = document.getElementById("nuevo-comentario-input");
  const texto = input?.value.trim();
  if (!texto) return;

  const modalBody = document.querySelector("#modal-comentera .modal-body");
  const nuevoItem = document.createElement("div");
  nuevoItem.className = "comment-item";
  nuevoItem.innerHTML = `
    <div class="comment-author">
      <span>👤 Estudiante / Auditor (Nuevo)</span>
      <span style="color: #64748b;">Justo ahora</span>
    </div>
    <p style="color: #334155;">"${texto}"</p>
  `;

  const footerArea = modalBody.lastElementChild;
  modalBody.insertBefore(nuevoItem, footerArea);
  input.value = "";
  mostrarAlerta("✍️ Anotación registrada exitosamente en Comentera.", "success");
}

async function verificarSaludBackend() {
  const pill = document.getElementById("api-status");
  if (!pill) return;
  try {
    const res = await fetch(`${API_URL}/products`);
    if (res.ok) {
      pill.textContent = "API: Conectada (Supabase Cloud)";
      pill.style.borderColor = "rgba(16, 185, 129, 0.6)";
      pill.style.color = "#10b981";
    } else {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (e) {
    pill.textContent = "API: Desconectada";
    pill.style.borderColor = "rgba(239, 68, 68, 0.6)";
    pill.style.color = "#ef4444";
  }
}

function mostrarAlerta(mensaje, tipo = "info") {
  const alerta = document.getElementById("global-alert");
  if (!alerta) return;

  alerta.className = `alert ${tipo}`;
  alerta.textContent = mensaje;
  alerta.style.display = "block";
  alerta.scrollIntoView({ behavior: "smooth", block: "nearest" });

  setTimeout(() => {
    alerta.style.display = "none";
  }, 6500);
}
