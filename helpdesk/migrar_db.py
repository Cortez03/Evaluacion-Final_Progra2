
from sqlalchemy import inspect, text
from database import engine

def agregar_columnas(tabla, columnas):
    inspector = inspect(engine)
    existentes = {
        columna["name"]
        for columna in inspector.get_columns(tabla)
    }

    with engine.begin() as conexion:
        for nombre, definicion in columnas.items():
            if nombre not in existentes:
                conexion.execute(
                    text(
                        f"ALTER TABLE {tabla} "
                        f"ADD COLUMN {nombre} {definicion}"
                    )
                )
                print(f"Columna agregada: {tabla}.{nombre}")

def migrar():
    agregar_columnas("tickets", {
        "creado_en": "DATETIME",
        "actualizado_en": "DATETIME"
    })

    agregar_columnas("prestamos_equipo", {
        "devuelto_en": "DATETIME",
        "observaciones": "TEXT",
        "condicion_devolucion": "VARCHAR(100)",
        "entregado_por": "VARCHAR(150)",
        "recibido_por": "VARCHAR(150)",
        "actualizado_en": "DATETIME"
    })

    print("Migracion completada correctamente.")

if __name__ == "__main__":
    migrar()
