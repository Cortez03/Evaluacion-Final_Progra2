
from datetime import datetime, timezone
from html import escape

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import engine, get_db, Base
from models import Ticket, PrestamoEquipo

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HelpDesk EDU",
    description="Sistema de gestión de tickets y préstamos de equipo",
    version="2.0.0"
)


# =========================================================
# ESQUEMAS PYDANTIC
# =========================================================

class PrestamoCreate(BaseModel):
    etiqueta_equipo: str = Field(..., min_length=1, max_length=100)
    receptor: str = Field(..., min_length=1, max_length=150)
    devolucion_esperada: datetime


class DevolucionCreate(BaseModel):
    recibido_por: str = Field(..., min_length=1, max_length=150)
    condicion: str = Field(default="Buen estado", max_length=100)
    observaciones: str | None = Field(default=None, max_length=2000)


class PrestamoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    etiqueta_equipo: str
    receptor: str
    devolucion_esperada: datetime
    activo: bool
    devuelto_en: datetime | None
    observaciones: str | None
    condicion_devolucion: str | None
    entregado_por: str | None
    recibido_por: str | None
    creado_en: datetime
    estado: str
    esta_vencido: bool


# =========================================================
# AUTENTICACION TEMPORAL
# =========================================================

def get_current_user_role():
    return {
        "username": "tecnico_gencer",
        "role": "tecnico"
    }


def verificar_permiso(user):
    if user["role"] not in ["tecnico", "supervisor"]:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para realizar esta operación."
        )


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def obtener_ticket(ticket_id, db):
    ticket = db.get(Ticket, ticket_id)

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="El ticket no existe."
        )

    return ticket


def validar_fecha(fecha):
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)

    if fecha <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=422,
            detail="La fecha de devolución debe ser futura."
        )

    return fecha


# =========================================================
# CREAR TICKET
# =========================================================

@app.post("/api/tickets", status_code=201)
def crear_ticket(
    payload: dict,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    verificar_permiso(user)

    titulo = str(payload.get("title", "")).strip()
    descripcion = str(payload.get("description", "")).strip()

    if not titulo or not descripcion:
        raise HTTPException(
            status_code=422,
            detail="El título y la descripción son obligatorios."
        )

    ticket = Ticket(
        title=titulo,
        description=descripcion,
        status="open"
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {
        "mensaje": "Ticket creado correctamente.",
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "status": ticket.status
    }


# =========================================================
# LISTAR TICKETS
# =========================================================

@app.get("/api/tickets")
def listar_tickets(db: Session = Depends(get_db)):
    tickets = db.scalars(
        select(Ticket).order_by(Ticket.id.desc())
    ).all()

    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status
        }
        for t in tickets
    ]


# =========================================================
# REGISTRAR PRESTAMO
# =========================================================

@app.post(
    "/api/tickets/{ticket_id}/equipment-loans",
    response_model=PrestamoResponse,
    status_code=201
)
def crear_prestamo(
    ticket_id: int,
    payload: PrestamoCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    verificar_permiso(user)

    obtener_ticket(ticket_id, db)

    etiqueta = payload.etiqueta_equipo.strip()
    receptor = payload.receptor.strip()

    if not etiqueta or not receptor:
        raise HTTPException(
            status_code=422,
            detail="La etiqueta y el receptor son obligatorios."
        )

    fecha = validar_fecha(payload.devolucion_esperada)

    existente = db.scalar(
        select(PrestamoEquipo).where(
            PrestamoEquipo.etiqueta_equipo == etiqueta,
            PrestamoEquipo.activo.is_(True)
        )
    )

    if existente:
        raise HTTPException(
            status_code=422,
            detail=f"El equipo {etiqueta} ya tiene un préstamo activo."
        )

    nuevo = PrestamoEquipo(
        ticket_id=ticket_id,
        etiqueta_equipo=etiqueta,
        receptor=receptor,
        devolucion_esperada=fecha,
        activo=True,
        entregado_por=user["username"]
    )

    try:
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return nuevo

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar el préstamo."
        )


# =========================================================
# LISTAR PRESTAMOS POR TICKET Y ESTADO
# =========================================================

@app.get(
    "/api/tickets/{ticket_id}/equipment-loans",
    response_model=list[PrestamoResponse]
)
def listar_prestamos(
    ticket_id: int,
    estado: str = Query(default="todos"),
    db: Session = Depends(get_db)
):
    obtener_ticket(ticket_id, db)

    if estado not in ["todos", "activo", "vencido", "devuelto"]:
        raise HTTPException(
            status_code=422,
            detail="Filtro de estado no válido."
        )

    prestamos = db.scalars(
        select(PrestamoEquipo)
        .where(PrestamoEquipo.ticket_id == ticket_id)
        .order_by(PrestamoEquipo.creado_en.desc())
    ).all()

    if estado == "activo":
        prestamos = [p for p in prestamos if p.estado == "activo"]

    elif estado == "vencido":
        prestamos = [p for p in prestamos if p.estado == "vencido"]

    elif estado == "devuelto":
        prestamos = [p for p in prestamos if p.estado == "devuelto"]

    return prestamos


# =========================================================
# LISTAR TODOS LOS PRESTAMOS
# =========================================================

@app.get(
    "/api/prestamos",
    response_model=list[PrestamoResponse]
)
def listar_todos_los_prestamos(
    estado: str = Query(default="todos"),
    db: Session = Depends(get_db)
):
    if estado not in ["todos", "activo", "vencido", "devuelto"]:
        raise HTTPException(
            status_code=422,
            detail="Filtro no válido."
        )

    prestamos = db.scalars(
        select(PrestamoEquipo).order_by(
            PrestamoEquipo.creado_en.desc()
        )
    ).all()

    if estado == "activo":
        prestamos = [p for p in prestamos if p.estado == "activo"]

    elif estado == "vencido":
        prestamos = [p for p in prestamos if p.estado == "vencido"]

    elif estado == "devuelto":
        prestamos = [p for p in prestamos if p.estado == "devuelto"]

    return prestamos


# =========================================================
# DEVOLVER EQUIPO
# =========================================================

@app.put(
    "/api/prestamos/{prestamo_id}/devolver",
    response_model=PrestamoResponse
)
def devolver_equipo(
    prestamo_id: int,
    payload: DevolucionCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    verificar_permiso(user)

    prestamo = db.get(PrestamoEquipo, prestamo_id)

    if not prestamo:
        raise HTTPException(
            status_code=404,
            detail="El préstamo no existe."
        )

    if not prestamo.activo:
        raise HTTPException(
            status_code=422,
            detail="Este equipo ya fue devuelto."
        )

    recibido_por = payload.recibido_por.strip()

    if not recibido_por:
        raise HTTPException(
            status_code=422,
            detail="Debes indicar quién recibe el equipo."
        )

    try:
        prestamo.registrar_devolucion(
            recibido_por=recibido_por,
            condicion=payload.condicion.strip(),
            observaciones=payload.observaciones.strip()
            if payload.observaciones else None
        )

        db.commit()
        db.refresh(prestamo)

        return prestamo

    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error))

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar la devolución."
        )


# =========================================================
# DETALLE DE UN PRESTAMO
# =========================================================

@app.get(
    "/api/prestamos/{prestamo_id}",
    response_model=PrestamoResponse
)
def detalle_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db)
):
    prestamo = db.get(PrestamoEquipo, prestamo_id)

    if not prestamo:
        raise HTTPException(
            status_code=404,
            detail="Préstamo no encontrado."
        )

    return prestamo


# =========================================================
# ESTADISTICAS
# =========================================================

@app.get("/api/estadisticas")
def estadisticas(db: Session = Depends(get_db)):
    prestamos = db.scalars(
        select(PrestamoEquipo)
    ).all()

    activos = sum(1 for p in prestamos if p.estado == "activo")
    vencidos = sum(1 for p in prestamos if p.estado == "vencido")
    devueltos = sum(1 for p in prestamos if p.estado == "devuelto")

    return {
        "total": len(prestamos),
        "activos": activos,
        "vencidos": vencidos,
        "devueltos": devueltos,
        "tickets": db.scalar(
            select(func.count()).select_from(Ticket)
        ) or 0
    }


# =========================================================
# CAMBIAR ESTADO DEL TICKET
# =========================================================

@app.patch("/api/tickets/{ticket_id}/estado")
def cambiar_estado_ticket(
    ticket_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    verificar_permiso(user)

    ticket = obtener_ticket(ticket_id, db)

    nuevo_estado = str(payload.get("status", "")).strip().lower()

    estados = ["open", "in_progress", "resolved", "closed"]

    if nuevo_estado not in estados:
        raise HTTPException(
            status_code=422,
            detail="Estado no válido."
        )

    ticket.status = nuevo_estado
    db.commit()

    return {
        "mensaje": "Estado actualizado.",
        "ticket_id": ticket.id,
        "status": ticket.status
    }


# =========================================================
# INTERFAZ WEB
# =========================================================

@app.get("/", response_class=HTMLResponse)
def inicio():
    return """
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="0;url=/tickets/1">
        <title>HelpDesk EDU</title>
    </head>
    <body>Abriendo HelpDesk...</body>
    </html>
    """


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def vista_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = db.get(Ticket, ticket_id)

    if not ticket:
        ticket = Ticket(
            id=ticket_id,
            title="Préstamo de Equipo",
            description="Gestión de préstamos temporales de equipo.",
            status="open"
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

    titulo = escape(ticket.title)
    descripcion = escape(ticket.description)

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HelpDesk EDU</title>

<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f1f5f9;
    color: #1e293b;
}}

header {{
    background: #142b4a;
    color: white;
    padding: 22px 7%;
}}

header h1 {{
    margin: 0;
    font-size: 25px;
}}

header p {{
    margin-bottom: 0;
    color: #cbd5e1;
}}

.container {{
    max-width: 1150px;
    margin: 30px auto;
    padding: 0 18px;
}}

.ticket-info {{
    background: white;
    padding: 22px;
    border-radius: 12px;
    margin-bottom: 22px;
    box-shadow: 0 2px 10px #0000000a;
}}

.stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit,minmax(150px,1fr));
    gap: 15px;
    margin-bottom: 22px;
}}

.stat {{
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 10px #0000000a;
}}

.stat h2 {{
    margin: 0;
    font-size: 28px;
}}

.stat p {{
    color: #64748b;
    margin-bottom: 0;
}}

.card {{
    background: white;
    padding: 24px;
    border-radius: 12px;
    margin-bottom: 22px;
    box-shadow: 0 2px 10px #0000000a;
}}

.form-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit,minmax(200px,1fr));
    gap: 15px;
}}

label {{
    display: block;
    font-weight: bold;
    margin-bottom: 7px;
}}

input, select, textarea {{
    width: 100%;
    padding: 11px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    font-size: 14px;
}}

textarea {{
    resize: vertical;
}}

button {{
    border: 0;
    padding: 11px 16px;
    border-radius: 7px;
    cursor: pointer;
    font-weight: bold;
    margin-top: 12px;
}}

.primary {{
    background: #2563eb;
    color: white;
}}

.success {{
    background: #15803d;
    color: white;
}}

.danger {{
    background: #dc2626;
    color: white;
}}

.secondary {{
    background: #e2e8f0;
    color: #1e293b;
}}

button:hover {{
    opacity: .85;
}}

.table-wrap {{
    overflow-x: auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 750px;
}}

th, td {{
    padding: 13px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
}}

th {{
    background: #f8fafc;
}}

.estado {{
    padding: 5px 9px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
}}

.activo {{
    background: #dcfce7;
    color: #166534;
}}

.vencido {{
    background: #fee2e2;
    color: #991b1b;
}}

.devuelto {{
    background: #dbeafe;
    color: #1e40af;
}}

#feedback {{
    margin-top: 12px;
    font-weight: bold;
}}

footer {{
    text-align: center;
    padding: 25px;
    color: #64748b;
}}

@media(max-width:600px) {{
    header {{ padding: 20px; }}
    .card {{ padding: 17px; }}
}}
</style>
</head>

<body>

<header>
    <h1>HelpDesk EDU</h1>
    <p>Sistema de gestión de tickets y préstamos de equipo</p>
</header>

<main class="container">

<section class="ticket-info">
    <h2>Ticket #{ticket.id}: {titulo}</h2>
    <p>{descripcion}</p>
    <strong>Estado:</strong> {escape(ticket.status)}
</section>

<section class="stats">
    <div class="stat">
        <h2 id="total">0</h2>
        <p>Total de préstamos</p>
    </div>
    <div class="stat">
        <h2 id="activos">0</h2>
        <p>Préstamos activos</p>
    </div>
    <div class="stat">
        <h2 id="vencidos">0</h2>
        <p>Préstamos vencidos</p>
    </div>
    <div class="stat">
        <h2 id="devueltos">0</h2>
        <p>Equipos devueltos</p>
    </div>
</section>

<section class="card">
    <h2>Registrar préstamo</h2>

    <form id="loan-form">
        <div class="form-grid">

            <div>
                <label>Etiqueta del equipo</label>
                <input id="etiqueta" required
                    maxlength="100" placeholder="Ej. LAP-001">
            </div>

            <div>
                <label>Receptor</label>
                <input id="receptor" required
                    maxlength="150" placeholder="Nombre del receptor">
            </div>

            <div>
                <label>Devolución esperada</label>
                <input type="datetime-local"
                    id="devolucion" required>
            </div>

        </div>

        <button class="primary" type="submit">
            Registrar préstamo
        </button>
    </form>

    <p id="feedback"></p>
</section>

<section class="card">
    <h2>Administración de préstamos</h2>

    <label>Filtrar por estado</label>

    <select id="filtro">
        <option value="todos">Todos los préstamos</option>
        <option value="activo">Activos</option>
        <option value="vencido">Vencidos</option>
        <option value="devuelto">Devueltos</option>
    </select>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Equipo</th>
                    <th>Receptor</th>
                    <th>Devolución esperada</th>
                    <th>Estado</th>
                    <th>Acción</th>
                </tr>
            </thead>
            <tbody id="loans-list">
                <tr><td colspan="6">Cargando...</td></tr>
            </tbody>
        </table>
    </div>
</section>

<section class="card">
    <h2>Historial de devoluciones</h2>
    <div id="historial">Cargando...</div>
</section>

<footer>
    HelpDesk EDU - Sistema de soporte técnico
</footer>

</main>

<script>
const ticketId = {ticket_id};

const feedback = document.getElementById("feedback");

function mostrarMensaje(mensaje, correcto=true) {{
    feedback.textContent = mensaje;
    feedback.style.color = correcto ? "#15803d" : "#dc2626";
}}

function fecha(valor) {{
    if (!valor) return "No registrada";
    return new Date(valor).toLocaleString("es-GT");
}}

async function consultar(url, opciones={{}}) {{
    const respuesta = await fetch(url, opciones);
    const datos = await respuesta.json();

    if (!respuesta.ok) {{
        throw new Error(datos.detail || "Error en la operación");
    }}

    return datos;
}}

async function cargarPrestamos() {{
    const filtro = document.getElementById("filtro").value;

    try {{
        const data = await consultar(
            `/api/tickets/${{ticketId}}/equipment-loans?estado=${{filtro}}`
        );

        const tbody = document.getElementById("loans-list");
        tbody.innerHTML = "";

        if (data.length === 0) {{
            tbody.innerHTML =
                '<tr><td colspan="6">No hay préstamos registrados.</td></tr>';
        }}

        data.forEach(p => {{
            const tr = document.createElement("tr");

            const tdId = document.createElement("td");
            tdId.textContent = p.id;

            const tdEquipo = document.createElement("td");
            tdEquipo.textContent = p.etiqueta_equipo;

            const tdReceptor = document.createElement("td");
            tdReceptor.textContent = p.receptor;

            const tdFecha = document.createElement("td");
            tdFecha.textContent = fecha(p.devolucion_esperada);

            const tdEstado = document.createElement("td");
            const badge = document.createElement("span");
            badge.className = "estado " + p.estado;
            badge.textContent = p.estado.toUpperCase();
            tdEstado.appendChild(badge);

            const tdAccion = document.createElement("td");

            if (p.activo) {{
                const boton = document.createElement("button");
                boton.className = "success";
                boton.textContent = "Devolver";
                boton.onclick = () => abrirDevolucion(p);
                tdAccion.appendChild(boton);
            }} else {{
                tdAccion.textContent = "Finalizado";
            }}

            [
                tdId, tdEquipo, tdReceptor,
                tdFecha, tdEstado, tdAccion
            ].forEach(td => tr.appendChild(td));

            tbody.appendChild(tr);
        }});

    }} catch(error) {{
        mostrarMensaje(error.message, false);
    }}
}}

async function cargarEstadisticas() {{
    try {{
        const data = await consultar("/api/estadisticas");

        document.getElementById("total").textContent = data.total;
        document.getElementById("activos").textContent = data.activos;
        document.getElementById("vencidos").textContent = data.vencidos;
        document.getElementById("devueltos").textContent = data.devueltos;

    }} catch(error) {{
        console.error(error);
    }}
}}

async function cargarHistorial() {{
    try {{
        const data = await consultar(
            `/api/tickets/${{ticketId}}/equipment-loans?estado=devuelto`
        );

        const contenedor = document.getElementById("historial");
        contenedor.innerHTML = "";

        if (data.length === 0) {{
            contenedor.textContent = "Todavía no hay devoluciones registradas.";
            return;
        }}

        data.forEach(p => {{
            const item = document.createElement("div");
            item.style.padding = "12px";
            item.style.borderBottom = "1px solid #e2e8f0";

            const titulo = document.createElement("strong");
            titulo.textContent = p.etiqueta_equipo + " - " + p.receptor;

            const detalle = document.createElement("p");
            detalle.textContent =
                "Devuelto: " + fecha(p.devuelto_en) +
                " | Recibido por: " + (p.recibido_por || "No registrado") +
                " | Condición: " + (p.condicion_devolucion || "Sin especificar");

            const observacion = document.createElement("p");
            observacion.textContent =
                "Observaciones: " + (p.observaciones || "Ninguna");

            item.append(titulo, detalle, observacion);
            contenedor.appendChild(item);
        }});

    }} catch(error) {{
        console.error(error);
    }}
}}

function abrirDevolucion(prestamo) {{
    const recibido = prompt("¿Quién recibe el equipo?");
    if (recibido === null) return;

    if (!recibido.trim()) {{
        alert("Debes indicar quién recibe el equipo.");
        return;
    }}

    const condicion = prompt(
        "Condición del equipo (Buen estado, Dañado, etc.):",
        "Buen estado"
    );

    if (condicion === null) return;

    const observaciones = prompt("Observaciones adicionales:", "");

    if (observaciones === null) return;

    registrarDevolucion(
        prestamo.id,
        recibido.trim(),
        condicion.trim() || "Sin especificar",
        observaciones.trim()
    );
}}

async function registrarDevolucion(
    id, recibido, condicion, observaciones
) {{
    try {{
        await consultar(`/api/prestamos/${{id}}/devolver`, {{
            method: "PUT",
            headers: {{
                "Content-Type": "application/json"
            }},
            body: JSON.stringify({{
                recibido_por: recibido,
                condicion: condicion,
                observaciones: observaciones
            }})
        }});

        mostrarMensaje("¡Equipo devuelto correctamente!");
        await actualizarTodo();

    }} catch(error) {{
        mostrarMensaje(error.message, false);
    }}
}}

document.getElementById("loan-form").addEventListener(
    "submit",
    async (e) => {{
        e.preventDefault();

        const payload = {{
            etiqueta_equipo:
                document.getElementById("etiqueta").value.trim(),
            receptor:
                document.getElementById("receptor").value.trim(),
            devolucion_esperada:
                new Date(
                    document.getElementById("devolucion").value
                ).toISOString()
        }};

        try {{
            await consultar(
                `/api/tickets/${{ticketId}}/equipment-loans`,
                {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/json"
                    }},
                    body: JSON.stringify(payload)
                }}
            );

            mostrarMensaje("¡Préstamo registrado correctamente!");
            e.target.reset();

            await actualizarTodo();

        }} catch(error) {{
            mostrarMensaje(error.message, false);
        }}
    }}
);

document.getElementById("filtro").addEventListener(
    "change",
    cargarPrestamos
);

async function actualizarTodo() {{
    await Promise.all([
        cargarPrestamos(),
        cargarEstadisticas(),
        cargarHistorial()
    ]);
}}

actualizarTodo();
</script>

</body>
</html>
"""
