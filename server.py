import socket
import json
from alghammingRe import ReceptorHamming, ReceptorCapaPresentacion

ACCOUNTS = {
    "4111111111111111": {"pin": "1234", "balance": 5000.00},
    "5500005555555559": {"pin": "0000", "balance": 12000.50},
    "22523": {"pin": "4444", "balance": 30000.00},
}

HOST = "127.0.0.1"
PORT = 5050

def send_msg(conn, action, data):
    message = {"action": action, "data": data}
    conn.sendall(json.dumps(message).encode("utf-8"))

def manejar_cliente(conn):
    tarjeta_autenticada = None
    capa_hamming = ReceptorHamming()
    presentation_layer = ReceptorCapaPresentacion()
 
    while True:
        raw = conn.recv(4096)
        if not raw:
            print("Cliente desconectado.")
            break
 
        frame_recibido = raw.decode("utf-8")
        print(f"\n Trama cruda recibida: {frame_recibido}")

        codigo_hamming, error_syn, n = capa_hamming.calcular_integridad(frame_recibido)
        chequeo = capa_hamming.verificar_integridad(error_syn, n)

        if chequeo['corregible']:
            data_original = capa_hamming.corregir_mensaje(codigo_hamming, error_syn, n)
            has_error = False
        else:
            data_original = None
            has_error = True

        if chequeo['hay_error'] and chequeo['corregible']:
            print(f"Error detectado y corregido en posición {error_syn}")
        elif has_error:
            print(f"Error detectado, no corregible (síndrome={error_syn})")

        binary_data = data_original if data_original else ""
        pres_result = presentation_layer.decodificar_mensaje(binary_data, has_error)

        if not pres_result['success']:
            print(f"Trama descartada: {pres_result['error_msg']}")
            send_msg(conn, "error", {"message": pres_result['error_msg']})
            continue

        try:
            message = json.loads(pres_result['data'])
            action = message.get("action")
            data = message.get("data", {})
            print(f"Procesando: {message}")
            
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
        except json.JSONDecodeError:
            print("Error no detectado .")
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