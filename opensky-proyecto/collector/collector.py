
import requests
import json
import paho.mqtt.client as mqtt
import time

url = "https://opensky-network.org/api/states/all"

cliente = mqtt.Client()
cliente.connect("mosquitto", 1883)
cliente.loop_start()

while True:
    try:
        respuesta = requests.get(url, timeout=30)

        if respuesta.status_code == 429:
            espera = int(
                respuesta.headers.get(
                    "x-rate-limit-retry-after-seconds", 60
                )
            )

            print("OpenSky ha limitado las peticiones (429).")
            print("Esperando", espera, "segundos antes de reintentar...")

            time.sleep(espera)
            continue

        respuesta.raise_for_status()
        datos = respuesta.json()

        if datos.get("states") is None:
            print("OpenSky no ha devuelto aviones.")
            time.sleep(60)
            continue

        aviones_validos = [
            avion for avion in datos["states"]
            if avion[5] is not None and avion[6] is not None
        ]

        aviones_seleccionados = aviones_validos[:100]

        print("Aviones recibidos:", len(datos["states"]))
        print("Aviones seleccionados:", len(aviones_seleccionados))

        for avion in aviones_seleccionados:
            mensaje = {
                "icao24": avion[0],
                "pais": avion[2],
                "longitud": avion[5],
                "latitud": avion[6],
                "altitud": avion[7],
                "velocidad": avion[9],
                "direccion": avion[10]
            }

            resultado = cliente.publish(
                "aviones/opensky",
                json.dumps(mensaje)
            )

            print(
                "ICAO:", avion[0],
                "| País:", avion[2],
                "| Latitud:", avion[6],
                "| Longitud:", avion[5],
                "| MQTT resultado:", resultado.rc
            )

        time.sleep(60)

    except requests.exceptions.RequestException as e:
        print("Error al consultar OpenSky:", e)
        print("Reintentando en 60 segundos...")
        time.sleep(60)

    except (ValueError, KeyError, TypeError) as e:
        print("Error al procesar los datos de OpenSky:", e)
        time.sleep(60)
