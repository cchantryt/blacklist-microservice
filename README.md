# Blacklist Microservice

Microservicio REST desarrollado en Python con Flask y PostgreSQL para registrar y consultar correos electrónicos en una lista negra.

## 1. Requisitos previos

Instalar y tener disponible:

- Python 3.11 o una versión compatible.
- PostgreSQL.
- Git.
- Postman.

## 2. Descargar el proyecto

```bash
git clone https://github.com/cchantryt/blacklist-microservice.git
cd blacklist-microservice
```

## 3. Crear y activar el entorno virtual

En Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1 
```

Si PowerShell bloquea la activación, se puede ejecutar directamente:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 4. Instalar las dependencias

Con el entorno virtual activado:

```powershell
python -m pip install -r requirements.txt
```

## 5. Configurar PostgreSQL

Crear una base de datos llamada `blacklist_db` en PostgreSQL.

Copiar `.env.example` y renombrar la copia a `.env`. Configurar las credenciales de PostgreSQL y una clave secreta propia.

Ejemplo:

```dotenv
DATABASE_URL=postgresql+psycopg2://postgres:TU_PASSWORD@localhost:5432/blacklist_db
JWT_SECRET_KEY=CAMBIA_POR_UN_SECRETO_LARGO 'Ver paso 7'
```

Reemplazar `TU_PASSWORD` por la contraseña local de PostgreSQL.

## 6. Ejecutar el microservicio

Desde la carpeta raíz del proyecto:

```powershell
python -m app.app
```

La aplicación estará disponible en:

http://127.0.0.1:5000/

La primera ejecución crea las tablas si la aplicación tiene configurado `db.create_all()`.

## 7. Generar un token JWT

Con el entorno virtual activado y desde la raíz:

```powershell
python -c "from app.app import app; from flask_jwt_extended import create_access_token; app.app_context().push(); print(create_access_token(identity='postman-client'))"
```

Puede ser necesario desctivar Smart app control en windows para generar la key JWT, luego de tenerla, se puede volver a activar.

Copiar el token generado para utilizarlo en Postman.

## 8. Probar los endpoints en Postman

Todas las solicitudes requieren autenticación JWT mediante `Authorization: Bearer TOKEN`.

### Registrar un correo

- Método: `POST`
- URL: `http://127.0.0.1:5000/blacklists`
- Body → raw → JSON:

```json
{
  "email": "prueba@example.com",
  "app_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "blocked_reason": "Prueba del microservicio"
}
```

Se espera una respuesta `201 Created` si el correo se registra correctamente.

### Consultar un correo

- Método: `GET`
- URL: `http://127.0.0.1:5000/blacklists/prueba@example.com`

Se espera una respuesta JSON que indique si el correo está en la lista negra y su motivo de bloqueo.

Consultar la colección de Postman incluida en la carpeta `postman/`, si está disponible, para ver los ejemplos de solicitudes.

## Notas

- No subir el archivo `.env` ni la carpeta `venv/` a GitHub.
- Cada integrante debe configurar su propia base de datos y sus variables de entorno.
- Si aparece un error de PostgreSQL o de sus controladores, revisar la instalación local antes de probar los endpoints.
