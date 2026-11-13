
# HelpDesk EDU – Ficha 08

Sistema web de gestión de tickets y préstamos de equipos informáticos, desarrollado con Python y FastAPI.

## Descripción del proyecto

HelpDesk EDU es una aplicación web diseñada para facilitar la administración de solicitudes de soporte técnico y el control de préstamos de equipos informáticos.

El sistema permite registrar tickets, gestionar préstamos de equipos, controlar las fechas de devolución y mantener un historial de los movimientos realizados.

## Funcionalidades principales

### Gestión de tickets
- Crear tickets de soporte técnico.
- Consultar los tickets registrados.
- Actualizar el estado de los tickets.
- Manejar estados como:
  - Abierto.
  - En proceso.
  - Resuelto.
  - Cerrado.

### Gestión de préstamos de equipos
- Registrar préstamos de equipos informáticos.
- Asociar préstamos a un ticket.
- Registrar la etiqueta del equipo.
- Identificar a la persona que recibe el equipo.
- Establecer fechas esperadas de devolución.
- Evitar préstamos duplicados de un mismo equipo mientras continúe prestado.

### Control de devoluciones
- Registrar la devolución de equipos.
- Identificar a la persona que recibe el equipo.
- Registrar la condición del equipo al momento de la devolución.
- Agregar observaciones.
- Consultar el historial de préstamos.

### Panel de control
- Visualizar estadísticas de préstamos.
- Consultar equipos activos.
- Identificar préstamos vencidos.
- Filtrar préstamos por estado.

## Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python | Lenguaje de programación |
| FastAPI | Desarrollo de la API y aplicación web |
| SQLAlchemy | ORM y gestión de base de datos |
| SQLite | Almacenamiento de información |
| Pydantic | Validación de datos |
| HTML | Estructura de la interfaz |
| CSS | Diseño visual |
| JavaScript | Interactividad de la aplicación |
| Uvicorn | Servidor de desarrollo |

## Requisitos

Antes de ejecutar el proyecto, se necesita:

- Python 3.10 o superior.
- pip (administrador de paquetes de Python).
- Un navegador web actualizado.

## Instalación

### 1. Clonar o descargar el proyecto

Ubicarse en la carpeta del proyecto:

```bash
cd helpdesk
```

### 2. Crear un entorno virtual (opcional)

```bash
python -m venv venv
```

Activarlo en Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Instalar las dependencias

```bash
pip install fastapi uvicorn sqlalchemy pydantic
```

## Ejecución del sistema

Desde la carpeta principal del proyecto, ejecutar:

```bash
python -m uvicorn main:app --reload
```

Cuando el servidor esté iniciado, abrir el navegador y acceder a:

**Aplicación web:**

http://127.0.0.1:8000

**Documentación de la API:**

http://127.0.0.1:8000/docs

Para detener el servidor, presionar `Ctrl + C` en la terminal.

## Base de datos

El proyecto utiliza SQLite para almacenar la información.

Archivo de base de datos:

```text
helpdesk_local.db
```

La aplicación utiliza SQLAlchemy para interactuar con la base de datos.

## Estructura del proyecto

```text
helpdesk/
│
├── main.py
├── models.py
├── database.py
├── migrar_db.py
├── helpdesk_local.db
└── README.md
```

**Descripción de archivos:**

- `main.py`: contiene las rutas, lógica de negocio y la interfaz web.
- `models.py`: define los modelos y relaciones de la base de datos.
- `database.py`: configura la conexión y las sesiones de SQLite.
- `migrar_db.py`: permite actualizar la estructura de la base de datos existente.
- `helpdesk_local.db`: almacena los datos del sistema.
- `README.md`: documentación del proyecto.

## Seguridad y permisos

La aplicación incorpora una validación básica de roles para controlar el acceso a determinadas operaciones.

**Nota:** La autenticación utilizada actualmente es temporal y debe reemplazarse por un sistema de autenticación real antes de utilizar la aplicación en producción.

## Objetivo del proyecto

Desarrollar una herramienta que permita mejorar el control de los equipos informáticos, facilitar el seguimiento de los préstamos y optimizar la gestión de solicitudes de soporte técnico dentro de una institución educativa.

## Autor

Desarrollado como parte de la **Ficha 08 – HelpDesk EDU**.

---

**HelpDesk EDU – Sistema de gestión de tickets y préstamos de equipos.**
