# KittyBoom

Para preparar o publicar la arquitectura Cloudflare Pages + Render + Neon + Cloudinary, consulta [DEPLOYMENT.md](DEPLOYMENT.md). El modo Docker local continúa usando PostgreSQL y almacenamiento local.

Primera versión funcional y escalable de la tienda y panel administrativo de KittyBoom. El proyecto separa `frontend` y `backend`, usa precios decimales y prepara la estructura para imágenes externas, pagos y módulos administrativos adicionales.

## Funciones implementadas

- Inicio responsive con identidad visual, banner, productos destacados, beneficios y redes.
- Catálogo con buscador, filtros combinados por categoría, material, color y precio, ordenamiento y estados vacíos.
- Carrito persistente con cantidades, eliminación, total, datos de entrega y WhatsApp.
- Registro del pedido en PostgreSQL antes de abrir WhatsApp.
- Login JWT y permisos por rol (`admin` y `seller`).
- API pública y administrativa documentada en Swagger.
- Productos, categorías, clientes, pedidos, artículos de pedido, variantes, imágenes, inventario, configuración, banners y auditoría en la migración inicial.
- Confirmación de pedidos con descuento de stock, cancelación con reposición y bloqueo de stock negativo.
- Pedidos simplificados en Pendiente, Finalizado y Cancelado. Finalizar descuenta stock y registra movimientos dentro de una transacción; los estados terminales quedan bloqueados.
- Detalle administrativo del pedido con cliente, artículos, imágenes, precios históricos, pago, canal, auditoría y usuario que cerró el pedido.
- Registro de ventas manuales pendientes o finalizadas, clientes ocasionales/registrados, selección de productos e idempotencia contra doble envío.
- Filtros de pedidos por número, cliente, estados, pago, método, canal y fechas.
- Dashboard y gestión administrativa de productos, categorías, imágenes, inventario, pedidos, clientes y configuración.
- Selector visual integrado en el producto: selección múltiple, arrastrar y soltar, miniaturas, imagen principal, reemplazo y estados de carga.
- Carga multipart de JPG/JPEG, PNG y WebP, límite de 5 MB, nombres UUID y eliminación física/metadata.
- WhatsApp consultado en tiempo real desde la configuración comercial, con normalización peruana y mensajes codificados.
- Docker Compose, Alembic, seed, CORS y variables de entorno.

## Inicio rápido en Windows PowerShell

Requiere Docker Desktop. Desde la raíz del proyecto:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Abre la tienda en `http://localhost:5173`, el panel en `http://localhost:5173/admin` y Swagger en `http://localhost:8000/docs`.

Carga los datos demo en otra terminal:

```powershell
docker compose exec backend python -m app.seed
```

Credenciales demo (cámbialas en `.env` antes de ejecutar el seed):

- Usuario: `admin@kittyboom.pe`
- Contraseña: `KittyBoom123!`

## Comandos por servicio

PostgreSQL y backend:

```powershell
docker compose up -d db
docker compose up backend
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
docker compose exec backend pytest
```

Frontend sin Docker:

```powershell
Set-Location frontend
npm install
npm run dev
npm run build
npm test
```

Reconstruir únicamente los servicios modificados:

```powershell
# Backend y frontend; conserva PostgreSQL y los volúmenes
docker compose up -d --build backend frontend

# Solo frontend
docker compose up -d --build frontend

# Solo backend
docker compose up -d --build backend
```

Verificación completa:

```powershell
docker compose exec backend python -m pytest -q
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

Para detener todo:

```powershell
docker compose down
```

Los datos de PostgreSQL y las imágenes se conservan en volúmenes. `docker compose down -v` también elimina esos datos; úsalo únicamente si quieres reiniciar el entorno.

## Imágenes

En desarrollo se sirven desde `backend/uploads`. PostgreSQL conserva únicamente URL, nombre, tipo MIME, tamaño, orden y marca de imagen principal. `app/services/storage.py` desacopla el almacenamiento para poder sustituirlo por S3 o Cloudinary.

En Administración → Productos → Nuevo/Editar producto, el área **Agregar imágenes** permite seleccionar varios archivos, arrastrarlos, revisar miniaturas, quitar selecciones, reemplazar imágenes existentes y elegir la principal. Los archivos nuevos se envían después de guardar el producto. Se aceptan JPG/JPEG, PNG y WebP de hasta 5 MB.

## WhatsApp

El encabezado, el detalle de producto, el pie y la confirmación del pedido obtienen el número desde `business_settings.whatsapp` mediante `GET /api/v1/public/settings`. No existe un número fijo en el frontend.

- `987654321` se convierte en `51987654321`.
- `+51 987-654-321` también produce `51987654321`.
- Los mensajes se codifican con `encodeURIComponent`.
- El pedido debe registrarse antes de abrir WhatsApp.
- La configuración pública se solicita sin caché y se actualiza después de guardar desde administración.

## Personalización

- Colores y tipografía: `frontend/src/index.css` y clases del archivo `frontend/src/main.tsx`.
- Logo: el texto `KittyBoom` en el encabezado está aislado y puede sustituirse por `<img>`.
- WhatsApp: edítalo desde Administración → Configuración. `WHATSAPP_NUMBER` solo establece el valor inicial del seed.
- Instagram, TikTok, dirección y horarios: campos disponibles en `business_settings`; los textos demo están en el pie de página.

## Migraciones

La migración `backend/alembic/versions/0001_initial.py` crea las entidades, claves foráneas, índices y restricciones iniciales. Para cambios futuros:

```powershell
docker compose exec backend alembic revision --autogenerate -m "descripcion"
docker compose exec backend alembic upgrade head
```

La migración `0002_simplify_order_statuses.py` convierte de forma segura los estados históricos: `confirmed`, `preparing`, `ready` y `delivered` pasan a `finalized`; `pending` y `cancelled` se conservan. La migración no modifica stock ni crea movimientos de inventario.

La migración `0003_manual_sales_and_order_details.py` agrega `sales_channel` e `idempotency_key` a pedidos. Los pedidos existentes reciben el canal `web`; no se modifica stock, pedidos, imágenes ni movimientos.

La migración `0004_virtual_cash_and_purchases.py` agrega `paid_at`, compras, detalle de compras y movimientos de Caja. Es segura para instalaciones existentes: no borra ni modifica pedidos históricos, stock, imágenes o movimientos previos. Para aplicarla sin ejecutar el seed:

```powershell
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose up -d --build backend frontend
```

La migración `0005_product_variants.py` completa la tabla de variantes ya existente y agrega referencias opcionales en pedidos, compras y movimientos de inventario. Todos los productos existentes conservan `has_variants = false`, su SKU, precio y stock general. Las referencias históricas permanecen nulas y la migración no redistribuye stock ni genera movimientos artificiales.

## Variantes opcionales

Un producto sencillo sigue usando su SKU, precio y stock general. Al activar **Este producto tiene variantes**, administración permite crear combinaciones con SKU único, atributos, precio opcional, stock independiente, mínimo, imagen, estado y posición. El stock general existente no se mueve automáticamente: debe distribuirse explícitamente.

La tienda exige seleccionar una variante activa, separa variantes del mismo producto en el carrito e incluye nombre y SKU en WhatsApp. El precio propio prevalece; si está vacío se usa la oferta o el precio del producto. Pedidos, ventas manuales, compras y ajustes de inventario guardan `variant_id` y afectan exclusivamente su stock. Los pedidos antiguos sin variante continúan usando el stock general.

## Logo y portada

El encabezado público usa `frontend/public/kittyboom-logo-horizontal.png`; el logo cuadrado continúa en `frontend/public/favicon.png`. `business_settings.logo_url` permite reemplazar posteriormente el logo horizontal desde Configuración.

Administración → Configuración → Portada administra múltiples imágenes multipart con orden, estado, principal y texto alternativo. La migración `0006_admin_hero_banners.py` amplía de forma segura `banners` sin borrar registros. La portada pública comienza por la principal, rota cada cinco segundos cuando corresponde, reinicia después de interacción manual, pausa con cursor/foco, admite gestos y respeta `prefers-reduced-motion`.

## Caja virtual y analítica

Administración → Caja muestra saldo, ingresos y egresos diarios/mensuales, historial acumulado y paginación. Permite registrar gastos, ingresos, saldo inicial, ajustes justificados y compras de mercadería. Una compra incrementa stock, crea movimientos de inventario y registra el egreso en una misma transacción. Finalizar un pedido lo marca pagado y genera un único ingreso enlazado mediante una clave idempotente; cancelar o dejar pendiente no afecta Caja ni inventario.

El formulario de compras admite varias líneas en una sola operación: busca por nombre o SKU, combina productos repetidos, calcula subtotales y total, y envía todas las líneas juntas a la API. El historial de Caja expone filtros visibles por fechas, dirección, tipo, método, usuario, pedido y texto; dichos filtros se mantienen al paginar. El saldo mostrado en cada fila es el saldo histórico global de ese momento, incluso cuando la tabla está filtrada.

El resumen administrativo consume datos reales de pedidos finalizados y movimientos de Caja. El logo oficial está en `frontend/public/kittyboom-logo.png` y también se usa como favicon. La tienda usa Arequipa como ubicación predeterminada y enlaza las cuentas oficiales de Instagram y TikTok; esos valores pueden reemplazarse en Configuración sin reconstruir el frontend.

## Ventas manuales y detalle de pedidos

Desde Administración → Pedidos se puede abrir cualquier pedido, cambiar su estado de pago, consultar artículos con precios históricos y revisar su historial. El botón **Nueva venta** permite buscar productos y clientes, crear una clienta rápidamente o usar Cliente ocasional.

Al guardar como pendiente no se modifica stock. **Finalizar venta** reutiliza el mismo servicio transaccional de finalización de pedidos: valida todos los productos, descuenta una sola vez y crea movimientos. El frontend nunca envía precios ni totales confiables; la API los calcula con `Decimal`.

## Estado por fases

1. Base, Docker, autenticación, roles, diseño y configuración: implementado.
2. Productos, categorías, imágenes multipart e inventario: gestión administrativa funcional; variantes avanzadas quedan como ampliación.
3. Tienda, catálogo, detalle de producto, filtros avanzados, buscador y carrito: implementado.
4. Clientes, pedidos, WhatsApp, venta manual, Caja virtual y analítica: implementado y conectado con inventario.
5. Pruebas esenciales, demo, responsive, seguridad y documentación: implementado; conviene ampliar pruebas end-to-end con PostgreSQL.

## Mejoras futuras

- Administración de usuarios, banners y auditoría completa visible desde la interfaz.
- Reordenamiento por arrastrar, optimización automática y migración a almacenamiento externo.
- Variantes seleccionables y paginación visible.
- Recuperación de contraseña, rotación de refresh tokens y rate limiting.
- Pasarela de pago, comprobantes, reportes, notificaciones y despliegue productivo.
