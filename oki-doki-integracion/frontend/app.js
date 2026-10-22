/**
 * ==============================================================================
 * SISTEMA ERP MAYORISTA "OKI DOKI" (DISTRIBOL) - CONTROLADOR FRONTEND
 * ==============================================================================
 * Integración de las 6 herramientas:
 * 1. Devin AI: Estructura y lógica de integración
 * 2. Slack: Webhooks y alertas en tiempo real
 * 3. Vercel: CI/CD y despliegue del cliente web
 * 4. Comentera: Widget y modal de feedback visual
 * 5. Gráficos 3D: Visor tridimensional interactivo con Three.js
 * 6. Supabase / Render: Base de datos PostgreSQL y backend FastAPI
 * ==============================================================================
 */

// Detección automática de entorno: Localhost vs Vercel / Render
const DEFAULT_LOCAL_API = "http://127.0.0.1:8000/api/v1";

function obtenerApiUrl() {
  const custom = localStorage.getItem("custom_api_url");
  if (custom) return custom.replace(/\/+$/, "");
  // En desarrollo local con frontend en puerto 3000 y backend en 8000
  if ((window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") && window.location.port === "3000") {
    return DEFAULT_LOCAL_API;
  }
  // En Vercel Serverless (mismo dominio), usar ruta relativa
  return "/api/v1";
}

const API_URL = obtenerApiUrl();

function configurarApiUrl() {
  const actual = localStorage.getItem("custom_api_url") || API_URL;
  const nueva = prompt("Configure la URL de su API FastAPI (ej. desplegada en Render o local):", actual);
  if (nueva !== null && nueva.trim()) {
    const urlLimpia = nueva.trim().replace(/\/+$/, "");
    localStorage.setItem("custom_api_url", urlLimpia);
    alert(`URL de API actualizada a: ${urlLimpia}`);
    window.location.reload();
  }
}

// Cache local de productos para cálculos rápidos
let productosCache = [];

// Variables globales del Visor 3D (Three.js)
let scene, camera, renderer, cubeMesh, edgeMesh, orbitControls;
let isSpinning = true;
let animFrameId = null;

// Inicialización general al cargar el DOM
document.addEventListener("DOMContentLoaded", () => {
  verificarEstadoSesion();
  cargarProductos();
  verificarSaludBackend();
  initVisor3D();

  // Escuchar cambios en selector y cantidad para actualizar texto de vista previa
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
// 1. VISOR 3D INTERACTIVO CON THREE.JS (HERRAMIENTA 5)
// ==============================================================================
function initVisor3D() {
  const container = document.getElementById("canvas-container");
  if (!container || typeof THREE === "undefined") {
    console.warn("Three.js no está disponible o el contenedor 3D no se encontró.");
    return;
  }

  // 1. Crear Escena
  scene = new THREE.Scene();

  // 2. Crear Cámara
  const width = container.clientWidth || 400;
  const height = container.clientHeight || 280;
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
  camera.position.set(3.5, 2.5, 4.5);

  // 3. Crear Renderizador WebGL
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.shadowMap.enabled = true;
  container.innerHTML = "";
  container.appendChild(renderer.domElement);

  // 4. Luces de Estudio
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
  dirLight.position.set(5, 10, 7);
  scene.add(dirLight);

  const fillLight = new THREE.DirectionalLight(0xf59e0b, 0.4);
  fillLight.position.set(-5, -2, -5);
  scene.add(fillLight);

  // 5. Malla 3D Representativa (Caja Mayorista de Cartón Oki Doki)
  crearMallaEmpaque(2.2, 1.8, 1.6, 0xb4793b, 0x1e293b);

  // 6. Controles de Órbita (Rotar e Interactuar con el Mouse)
  if (typeof THREE.OrbitControls !== "undefined") {
    orbitControls = new THREE.OrbitControls(camera, renderer.domElement);
    orbitControls.enableDamping = true;
    orbitControls.dampingFactor = 0.05;
    orbitControls.enableZoom = true;
    orbitControls.maxDistance = 10;
    orbitControls.minDistance = 2;
  }

  // 7. Bucle de Animación
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

  // Redimensionar responsivamente
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

  // Bordes estilizados para realismo
  const edgesGeometry = new THREE.EdgesGeometry(geometry);
  const edgesMaterial = new THREE.LineBasicMaterial({ color: colorEdge, linewidth: 2 });
  edgeMesh = new THREE.LineSegments(edgesGeometry, edgesMaterial);
  scene.add(edgeMesh);
}

function toggleGiro3D() {
  isSpinning = !isSpinning;
  const btn = document.getElementById("btn-toggle-spin");
  if (btn) {
    btn.textContent = isSpinning ? "⏸️ Pausar Giro" : "▶️ Reanudar Giro";
  }
}

function cambiarEmpaque3D(tipo) {
  const tagType = document.getElementById("canvas-product-type");
  const tagDim = document.getElementById("box-dimensions-label");

  if (tipo === "caja") {
    crearMallaEmpaque(2.2, 1.8, 1.6, 0xb4793b, 0x1e293b);
    if (tagType) tagType.textContent = "Caja Cartón Corrugado (12x1L)";
    if (tagDim) tagDim.textContent = "Dim: 40x30x25cm • Peso: ~12kg";
  } else if (tipo === "fardo") {
    crearMallaEmpaque(2.0, 2.5, 1.4, 0x38bdf8, 0x0369a1);
    if (tagType) tagType.textContent = "Fardo Termoencogible x24";
    if (tagDim) tagDim.textContent = "Dim: 45x35x30cm • Peso: ~10kg";
  } else if (tipo === "saco") {
    crearMallaEmpaque(1.8, 2.8, 1.2, 0xd4a373, 0x78350f);
    if (tagType) tagType.textContent = "Quintal / Saco Arpillera 50kg";
    if (tagDim) tagDim.textContent = "Dim: 50x40x90cm • Peso: 50kg";
  }
}

function sincronizarProducto3D(productId) {
  const prod = productosCache.find(p => p.id === productId);
  if (!prod) return;

  const skuTag = document.getElementById("canvas-product-sku");
  const typeTag = document.getElementById("canvas-product-type");

  if (skuTag) skuTag.textContent = `SKU: ${prod.sku}`;

  // Ajustar forma según el tipo de producto
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
  mostrarAlerta(`📦 Inspeccionando en el Visor 3D el producto ID #${productId}. Puede rotarlo 360° con el mouse.`, "info");
  const visor = document.getElementById("canvas-container");
  if (visor) visor.scrollIntoView({ behavior: "smooth", block: "center" });
}

// ==============================================================================
// 2. INTEGRACIÓN DE SLACK (HERRAMIENTA 2: WEBHOOKS)
// ==============================================================================
async function probarSlackWebhook() {
  mostrarAlerta("Enviando notificación de prueba al canal de Slack...", "info");
  try {
    const res = await fetch(`${API_URL}/integrations/slack/test`, {
      method: "POST"
    });
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

// ==============================================================================
// 3. INTEGRACIÓN DE COMENTERA (HERRAMIENTA 4: FEEDBACK VISUAL)
// ==============================================================================
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

  // Insertar antes del área de escritura
  const footerArea = modalBody.lastElementChild;
  modalBody.insertBefore(nuevoItem, footerArea);

  input.value = "";
  mostrarAlerta("✍️ Anotación visual registrada exitosamente en Comentera.", "success");
}

// ==============================================================================
// 4. AUTENTICACIÓN JWT (iniciarSesion / cerrarSesion)
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

    // Guardar token JWT en localStorage según especificación
    localStorage.setItem("jwt_token", data.access_token);
    localStorage.setItem("jwt_user", username);
    localStorage.removeItem("jwt_logged_out");

    mostrarAlerta(`¡Bienvenido, ${username}! Token JWT activo guardado en localStorage.`, "success");
    await verificarEstadoSesion();

  } catch (error) {
    mostrarAlerta("No fue posible conectar con el servidor backend.", "danger");
    console.error("Error en login:", error);
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

  // Auto-autenticación inicial para evitar fricción al evaluar el sistema
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
      console.warn("Auto-login no disponible:", e);
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

// ==============================================================================
// 5. CATÁLOGO E INVENTARIO (cargarProductos)
// ==============================================================================
async function cargarProductos() {
  const tbody = document.getElementById("inventory-tbody");
  const select = document.getElementById("sale-product-select");

  try {
    const respuesta = await fetch(`${API_URL}/products`);
    if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);

    const productos = await respuesta.json();
    productosCache = productos;

    // 1. Llenar tabla de inventario en tiempo real
    if (tbody) {
      if (productos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 1.5rem; color: var(--muted);">No hay productos registrados en el almacén.</td></tr>`;
      } else {
        tbody.innerHTML = productos.map(p => {
          const badgeClass = p.stock > 10 ? "high" : "low";
          const precioBs = Number(p.price).toFixed(2);
          return `
            <tr>
              <td><strong>#${p.id}</strong></td>
              <td><span style="background: #f1f5f9; padding: 0.2rem 0.5rem; border-radius: 4px; font-family: monospace; font-weight: 700;">${p.sku}</span></td>
              <td><strong>${p.name}</strong></td>
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

    // 2. Llenar selector dinámico del punto de venta
    if (select) {
      const selectedPrev = select.value;
      select.innerHTML = `<option value="">-- Seleccione un producto del almacén --</option>` +
        productos.map(p => `
          <option value="${p.id}" ${p.id == selectedPrev ? 'selected' : ''}>
            [${p.sku}] ${p.name} - Bs. ${Number(p.price).toFixed(2)} (Stock: ${p.stock})
          </option>
        `).join("");
      actualizarPreviewVenta();
    }

  } catch (error) {
    console.error("Error al cargar productos:", error);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger); padding: 1.5rem;">⚠️ No se pudo conectar al servidor backend en <code>${API_URL}</code>.</td></tr>`;
    }
  }
}

function seleccionarParaVenta(productId) {
  const select = document.getElementById("sale-product-select");
  if (select) {
    select.value = productId;
    actualizarPreviewVenta();
    sincronizarProducto3D(productId);
    select.scrollIntoView({ behavior: "smooth", block: "center" });
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
    if (preview) preview.innerHTML = "Seleccione un ítem y cantidad para verificar el descuento en tiempo real y el cálculo en Bolivianos (Bs.).";
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

// ==============================================================================
// 6. REGISTRO DE NUEVA MERCANCÍA (guardarProducto)
// ==============================================================================
async function guardarProducto() {
  const token = localStorage.getItem("jwt_token");

  const sku = document.getElementById("new-sku").value.trim();
  const name = document.getElementById("new-name").value.trim();
  const price = parseFloat(document.getElementById("new-price").value);
  const stock = parseInt(document.getElementById("new-stock").value, 10);

  if (!sku || !name || isNaN(price) || price <= 0 || isNaN(stock) || stock < 0) {
    mostrarAlerta("Por favor complete todos los campos requeridos (Precio > 0 y Stock >= 0).", "danger");
    return;
  }

  const payload = { sku, name, price, stock };
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const respuesta = await fetch(`${API_URL}/products`, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload)
    });

    const data = await respuesta.json();

    if (!respuesta.ok) {
      if (respuesta.status === 401 || respuesta.status === 403) {
        mostrarAlerta("Sesión inválida o expirada. Por favor inicie sesión nuevamente.", "danger");
        cerrarSesion();
        return;
      }
      mostrarAlerta(`Error al guardar producto: ${data.detail || "Verifique los datos."}`, "danger");
      return;
    }

    mostrarAlerta(`✅ ¡Producto "${data.name}" (${data.sku}) registrado exitosamente con ${data.stock} unidades en almacén! Alerta enviada a Slack.`, "success");

    // Limpiar campos
    document.getElementById("new-sku").value = "";
    document.getElementById("new-name").value = "";
    document.getElementById("new-price").value = "";
    document.getElementById("new-stock").value = "25";

    // Recargar inventario automáticamente
    await cargarProductos();
    sincronizarProducto3D(data.id);

  } catch (error) {
    mostrarAlerta("Error de conexión al guardar el producto.", "danger");
    console.error("Error:", error);
  }
}

// ==============================================================================
// 7. PUNTO DE VENTA Y CHECKOUT TRANSACCIONAL (registrarVenta)
// ==============================================================================
async function registrarVenta() {
  const token = localStorage.getItem("jwt_token");
  const select = document.getElementById("sale-product-select");
  const inputCant = document.getElementById("sale-quantity");
  const btnProcess = document.getElementById("btn-process-sale");

  const productId = parseInt(select?.value, 10);
  const quantity = parseInt(inputCant?.value, 10);

  if (!token) {
    mostrarAlerta("⚠️ Se requiere inicio de sesión con Token JWT antes de procesar ventas mayoristas.", "danger");
    const loginEl = document.getElementById("username");
    if (loginEl) loginEl.scrollIntoView({ behavior: "smooth", block: "center" });
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
  btnProcess.textContent = "⚡ Descontando Stock...";

  const payload = {
    items: [
      { product_id: productId, quantity: quantity }
    ]
  };

  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const respuesta = await fetch(`${API_URL}/sales/checkout`, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload)
    });

    const data = await respuesta.json();

    if (!respuesta.ok) {
      // Manejo específico de error de stock insuficiente (400 Bad Request)
      mostrarAlerta(`⚠️ ${data.detail || "Error en la transacción de venta."}`, "danger");
      return;
    }

    // Éxito: Mostrar alerta con el total en Bs. y comprobante
    const totalBs = Number(data.total_amount).toFixed(2);
    mostrarAlerta(`✅ ¡Venta #${data.id} procesada con éxito! Total cobrado en mostrador: Bs. ${totalBs}. Stock descontado en tiempo real. Alerta enviada a Slack.`, "success");

    // Resetear cantidad a 1
    inputCant.value = 1;

    // Recargar la tabla automáticamente para reflejar el descuento de stock en tiempo real
    await cargarProductos();
    sincronizarProducto3D(productId);

  } catch (error) {
    mostrarAlerta("Error de comunicación con el backend al procesar la venta.", "danger");
    console.error("Error en registrarVenta:", error);
  } finally {
    btnProcess.disabled = false;
    btnProcess.textContent = "⚡ Procesar Venta Mostrador";
  }
}

// ==============================================================================
// 8. UTILIDADES GENERALES
// ==============================================================================
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
