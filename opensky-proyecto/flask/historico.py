
import os
import time

import psycopg
from influxdb_client import InfluxDBClient

INTERVALO_SEGUNDOS = 300
RETENCION_DIAS = 7


def conectar():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def obtener_velocidad_media():
    cliente = InfluxDBClient(
        url=os.environ["INFLUX_URL"],
        token=os.environ["INFLUX_TOKEN"],
        org=os.environ["INFLUX_ORG"],
    )

    consulta = """
        from(bucket: "aviones")
            |> range(start: -7d)
            |> filter(fn: (r) => r._field == "velocidad")
            |> group()
            |> mean()
    """

    try:
        tablas = cliente.query_api().query(consulta)
        for tabla in tablas:
            for registro in tabla.records:
                valor = registro.get_value()
                if valor is not None:
                    return float(valor)
        return None
    finally:
        cliente.close()


def guardar_captura():
    velocidad_media = obtener_velocidad_media()

    with conectar() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO historico_estadisticas (
                    pais_id,
                    total_aviones,
                    velocidad_media,
                    altitud_media,
                    fecha_captura
                )
                SELECT
                    pais_id,
                    total_aviones,
                    velocidad_media,
                    altitud_media,
                    CURRENT_TIMESTAMP
                FROM estadisticas_pais;
            """)

            paises_guardados = cursor.rowcount

            if velocidad_media is not None:
                cursor.execute("""
                    INSERT INTO historico_velocidad (
                        velocidad_media,
                        fecha_captura
                    )
                    VALUES (%s, CURRENT_TIMESTAMP);
                """, (velocidad_media,))

            cursor.execute("""
                DELETE FROM historico_estadisticas
                WHERE fecha_captura <
                    CURRENT_TIMESTAMP - INTERVAL '7 days';
            """)

            cursor.execute("""
                DELETE FROM historico_velocidad
                WHERE fecha_captura <
                    CURRENT_TIMESTAMP - INTERVAL '7 days';
            """)

    print(
        f"Captura guardada: {paises_guardados} países. "
        f"Velocidad media: {velocidad_media}",
        flush=True,
    )


if __name__ == "__main__":
    while True:
        try:
            guardar_captura()
        except Exception as error:
            print(f"Error guardando el histórico: {error}", flush=True)

        time.sleep(INTERVALO_SEGUNDOS)
