# Despliegue gratuito de KittyBoom

Esta guía prepara Cloudflare Pages + Render + Neon + Cloudinary. No ejecutes el seed en producción. Render no conserva archivos locales: PostgreSQL vive en Neon y las imágenes en Cloudinary.

## 1. GitHub

1. Crea un repositorio vacío en GitHub.
2. Comprueba `git status` y que `.env`, `uploads`, `node_modules` y `dist` no estén versionados.
3. Sube el proyecto. Conserva únicamente `.env.example`, `frontend/.env.example` y `production.env.example`.
4. Si alguna credencial real llegó a un commit, rótala en el proveedor y limpia el historial antes de publicar.

## 2. Neon PostgreSQL

1. Crea una cuenta y un proyecto PostgreSQL en Neon.
2. Copia la URL de conexión con SSL (`sslmode=require`). Guárdala como `DATABASE_URL` en Render; no la pegues en archivos Git.
3. KittyBoom convierte automáticamente `postgresql://` a `postgresql+psycopg://`, usa `pool_pre_ping`, recicla conexiones y limita el pool para una instancia pequeña.

Migración manual desde Render Shell, si fuera necesaria:

```sh
alembic upgrade head
```

El contenedor también ejecuta este comando una sola vez antes de iniciar cada instancia. No genera migraciones ni ejecuta seed.

## 3. Cloudinary

1. Crea una cuenta gratuita.
2. En el panel copia Cloud name, API key y API secret.
3. Configura esas tres variables únicamente en Render. El secret nunca pertenece a Cloudflare.
4. Usa `CLOUDINARY_FOLDER=kittyboom`.

En producción, productos y portadas subidos mediante multipart se guardan como HTTPS y su `public_id` queda en el campo de almacenamiento. Al eliminar el registro correspondiente, el backend elimina el recurso remoto. Desarrollo conserva `STORAGE_PROVIDER=local` y el volumen `uploads`.

## 4. Backend en Render

1. Conecta el repositorio GitHub en Render y crea un Web Service mediante `render.yaml`, o configura Docker manualmente con contexto `backend` y `backend/Dockerfile`.
2. Agrega las variables de `production.env.example`:

```text
ENVIRONMENT=production
DATABASE_URL=<URL Neon>
JWT_SECRET=<secreto aleatorio de 32 caracteres o más>
CORS_ORIGINS=https://kittyboom.pages.dev
STORAGE_PROVIDER=cloudinary
CLOUDINARY_CLOUD_NAME=<valor Cloudinary>
CLOUDINARY_API_KEY=<valor Cloudinary>
CLOUDINARY_API_SECRET=<valor Cloudinary>
CLOUDINARY_FOLDER=kittyboom
ADMIN_EMAIL=<correo propietario>
ADMIN_PASSWORD=<clave inicial segura de 12 caracteres o más>
BUSINESS_TIMEZONE=America/Lima
```

3. Render proporciona `PORT`; `start.sh` escucha en `0.0.0.0:$PORT`, acepta cabeceras proxy HTTPS, aplica migraciones y arranca Uvicorn.
4. Comprueba `https://TU-BACKEND.onrender.com/health`. Debe devolver aplicación y base de datos en estado `ok`.
5. Abre Render Shell y crea el primer administrador de forma idempotente:

```sh
python -m app.create_admin
```

El comando nunca usa la clave demo en producción y no modifica un usuario ya existente. Después puedes retirar `ADMIN_PASSWORD` del entorno.

## 5. Frontend en Cloudflare Pages

El frontend usa exclusivamente npm. Conserva `frontend/package-lock.json` en Git y actualízalo con npm cuando cambien las dependencias.

1. Crea un proyecto Pages conectado al mismo repositorio.
2. Configura:

```text
Root directory: frontend
Build command: npm ci && npm run build
Output directory: dist
```

3. Agrega únicamente:

```text
VITE_API_URL=https://TU-BACKEND.onrender.com/api/v1
```

4. Despliega y asigna `kittyboom.pages.dev` si está disponible. `public/_redirects` hace que `/admin`, `/producto/:id` y demás rutas SPA recarguen `index.html`.
5. Si Cloudflare entrega otro dominio o un dominio de vista previa, agrégalo a `CORS_ORIGINS` separado por coma y reinicia Render.

## 6. Comprobación funcional

Prueba tienda, acceso `/admin`, productos, variantes, pedidos, Caja, compras, configuración, carga y eliminación de productos y portadas. Inspecciona el bundle del navegador: solo debe contener la URL pública de API, nunca credenciales Neon o Cloudinary.

## 7. Actualizaciones

Sube cambios a GitHub. Cloudflare reconstruye el frontend; en Render activa despliegue manual o `autoDeploy` cuando estés conforme. El arranque aplica únicamente migraciones pendientes. Para cambios delicados, exporta primero la base.

## 8. Copias de seguridad

Exportar PostgreSQL:

```sh
pg_dump "$DATABASE_URL" --format=custom --file=kittyboom.dump
```

Restaurar en una base vacía o de recuperación:

```sh
pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" kittyboom.dump
```

Cloudinary conserva los binarios; exporta periódicamente desde Media Library/API un listado con `public_id`, `secure_url` y metadatos, y descarga los originales si necesitas una copia independiente. La base contiene las referencias. Si Neon se suspende, la aplicación pierde temporalmente datos comerciales; si Cloudinary se suspende, permanecen los registros pero las imágenes no cargan; si Render duerme, la primera petición puede demorar; Cloudflare sigue sirviendo el frontend estático.
