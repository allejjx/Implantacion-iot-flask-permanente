
import os
import psycopg
from flask import Flask, render_template

app = Flask(__name__)

ANCHO = 800
ALTO = 300
MARGEN_X = 55
MARGEN_Y = 35


def conectar():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def obtener_historico():
    conexion = conectar()

    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT
                    fecha_captura,
                    SUM(total_aviones)::INTEGER
                FROM historico_estadisticas
                WHERE fecha_captura >=
                    CURRENT_TIMESTAMP - INTERVAL '7 days'
                GROUP BY fecha_captura
                ORDER BY fecha_captura;
            """)
            return cursor.fetchall()
    finally:
        conexion.close()


def obtener_historico_velocidad():
    conexion = conectar()

    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT fecha_captura, velocidad_media
                FROM historico_velocidad
                WHERE fecha_captura >=
                    CURRENT_TIMESTAMP - INTERVAL '7 days'
                ORDER BY fecha_captura;
            """)
            return cursor.fetchall()
    finally:
        conexion.close()


def preparar_grafica(registros, nombre_valor):
    puntos = []

    if not registros:
        return puntos, 0, 0

    valores = [float(valor) for fecha, valor in registros]
    minimo = min(valores)
    maximo = max(valores)

    # Añadir margen para que los puntos no queden pegados
    # a los bordes, incluso cuando todos los valores coinciden.
    margen = max((maximo - minimo) * 0.25, 1)
    limite_inferior = minimo - margen
    limite_superior = maximo + margen
    diferencia = limite_superior - limite_inferior

    for i, (fecha, valor) in enumerate(registros):
        x = (
            MARGEN_X
            if len(registros) == 1
            else MARGEN_X
            + i * (ANCHO - 2 * MARGEN_X)
            / (len(registros) - 1)
        )

        y = ALTO - MARGEN_Y - (
            (float(valor) - limite_inferior) / diferencia
            * (ALTO - 2 * MARGEN_Y)
        )

        puntos.append({
            "x": round(x, 2),
            "y": round(y, 2),
            "valor": (
                int(valor)
                if nombre_valor == "total"
                else round(float(valor), 2)
            ),
            "fecha": fecha.strftime("%d/%m/%Y %H:%M"),
        })

    return puntos, minimo, maximo


@app.route("/")
def inicio():
    historico_aviones = obtener_historico()
    historico_velocidad = obtener_historico_velocidad()

    puntos_aviones, minimo_aviones, maximo_aviones = (
        preparar_grafica(historico_aviones, "total")
    )

    puntos_velocidad, minimo_velocidad, maximo_velocidad = (
        preparar_grafica(historico_velocidad, "velocidad")
    )

    linea_aviones = " ".join(
        f"{p['x']},{p['y']}" for p in puntos_aviones
    )

    linea_velocidad = " ".join(
        f"{p['x']},{p['y']}" for p in puntos_velocidad
    )

    return render_template(
        "index.html",
        puntos_aviones=puntos_aviones,
        linea_aviones=linea_aviones,
        minimo_aviones=minimo_aviones,
        maximo_aviones=maximo_aviones,
        capturas_aviones=len(puntos_aviones),
        puntos_velocidad=puntos_velocidad,
        linea_velocidad=linea_velocidad,
        minimo_velocidad=round(minimo_velocidad, 2),
        maximo_velocidad=round(maximo_velocidad, 2),
        capturas_velocidad=len(puntos_velocidad),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
