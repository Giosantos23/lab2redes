import socket
import json
from alghammingRe import ReceptorHamming, ReceptorCapaPresentacion
from algFletcherRe import ReceptorFletcher

ACCOUNTS = {
    "4111111111111111": {"pin": "1234", "balance": 5000.00},
    "5500005555555559": {"pin": "0000", "balance": 12000.50},
    "22523": {"pin": "4444", "balance": 30000.00},
    "22246": {"pin": "2222", "balance": 30000.00},
}

HOST = "127.0.0.1"
PORT = 5050

def send_msg(conn, action, data):
    """Capa de TRANSMISION: envia la respuesta delimitada por '\\n'."""
    message = {"action": action, "data": data}
    conn.sendall((json.dumps(message) + "\n").encode("utf-8"))

def recibir_informacion(conn, buffer):
    """
    Capa de TRANSMISION: lee del socket hasta encontrar '\\n'.
    Devuelve (linea, buffer_restante). Si la conexion se cierra, linea es None.
    """
    while b"\n" not in buffer:
        chunk = conn.recv(4096)
        if not chunk:
            return None, buffer
        buffer += chunk
    linea, _, resto = buffer.partition(b"\n")
    return linea.decode("utf-8"), resto


def procesar_enlace(cabecera, trama, capa_hamming, capa_fletcher):
    """
    Capa de ENLACE: despacha al algoritmo indicado por el emisor y devuelve
    (bits_originales, hay_error_no_corregible, texto_de_log).
    """
    if cabecera.startswith("FLE"):
        try:
            bloque = int(cabecera[3:])
            capa_fletcher.set_block_size(bloque)
        except ValueError:
            return None, True, "Cabecera Fletcher inválida."

        resultado = capa_fletcher.decodificar_fletcher(trama)
        if resultado["status"] == "no_error":
            return resultado["data_original"], False, \
                f"Fletcher-{2*bloque}: checksum correcto ({resultado['checksum_recibido']})"
        if resultado["status"] == "error_detected":
            return None, True, (
                f"Fletcher-{2*bloque}: ERROR DETECTADO. "
                f"recibido={resultado['checksum_recibido']} "
                f"calculado={resultado['checksum_calculado']}. "
                "El algoritmo no corrige, la trama se descarta."
            )
        return None, True, "Fletcher: trama mal formada."

    # Por defecto: Hamming
    codigo_hamming, error_syn, n = capa_hamming.calcular_integridad(trama)
    chequeo = capa_hamming.verificar_integridad(error_syn, n)

    if not chequeo["corregible"]:
        return None, True, f"Hamming: error detectado, no corregible (síndrome={error_syn})"

    data_original = capa_hamming.corregir_mensaje(codigo_hamming, error_syn, n)
    if chequeo["hay_error"]:
        return data_original, False, f"Hamming: error corregido en la posición {error_syn}"
    return data_original, False, "Hamming: sin errores"


def manejar_cliente(conn):
    tarjeta_autenticada = None
    capa_hamming = ReceptorHamming()
    capa_fletcher = ReceptorFletcher(16)
    presentation_layer = ReceptorCapaPresentacion()
    buffer = b""

    while True:
        linea, buffer = recibir_informacion(conn, buffer)
        if linea is None:
            print("Cliente desconectado.")
            break

        if "|" not in linea:
            print("Paquete sin cabecera de algoritmo, se descarta.")
            send_msg(conn, "error", {"message": "Paquete mal formado"})
            continue

        cabecera, _, frame_recibido = linea.partition("|")
        print(f"\n[transmision] cabecera={cabecera} | trama de {len(frame_recibido)} bits")

        data_original, has_error, log = procesar_enlace(
            cabecera, frame_recibido, capa_hamming, capa_fletcher
        )
        print(f"[enlace] {log}")

        # Capa de PRESENTACION
        binary_data = data_original if data_original else ""
        pres_result = presentation_layer.decodificar_mensaje(binary_data, has_error)

        if not pres_result["success"]:
            print(f"[aplicacion] Trama descartada: {pres_result['error_msg']}")
            send_msg(conn, "error", {"message": pres_result["error_msg"]})
            continue

        # El padding de Fletcher llega como bytes nulos al final del texto
        texto = pres_result["data"].rstrip("\x00")

        try:
            message = json.loads(texto)
            action = message.get("action")
            data = message.get("data", {})
            print(f"[aplicacion] Procesando: {message}")

            if action == "login":
                tarjeta = data.get("tarjeta")
                pin = data.get("pin")
                account = ACCOUNTS.get(tarjeta)
                if account and account["pin"] == pin:
                    tarjeta_autenticada = tarjeta
                    send_msg(conn, "login_ok", {"message": "Autenticación exitosa"})
                else:
                    send_msg(conn, "login_denegado", {"message": "Tarjeta o PIN incorrectos"})

            elif action == "retiro":
                if tarjeta_autenticada is None:
                    send_msg(conn, "error", {"message": "No autenticado"})
                    continue
                cantidad = data.get("cantidad", 0)
                account = ACCOUNTS[tarjeta_autenticada]
                if cantidad <= 0:
                    send_msg(conn, "error", {"message": "Monto inválido"})
                elif cantidad > account["balance"]:
                    send_msg(conn, "error", {"message": "Fondos insuficientes"})
                else:
                    account["balance"] -= cantidad
                    send_msg(conn, "retiro_ok", {"cantidad": cantidad, "balance": account["balance"]})

            elif action == "logout":
                send_msg(conn, "logout_ok", {"message": "Hasta luego"})
                break
            else:
                send_msg(conn, "error", {"message": "Acción desconocida"})

        except json.JSONDecodeError:
            # Caso critico: el algoritmo NO detecto el error pero el mensaje llego corrupto
            print("[aplicacion] Error NO detectado por la capa de enlace: JSON inválido.")
            send_msg(conn, "error", {"message": "Mensaje corrupto, no se pudo procesar."})


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        print(f"server escuchando en {HOST}:{PORT} ...")
        while True:
            conn, addr = server_socket.accept()
            with conn:
                manejar_cliente(conn)

if __name__ == "__main__":
    main()