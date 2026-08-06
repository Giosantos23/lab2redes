#include <iostream>
#include <string>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include "algHammingSnd.hpp"
#include "algFletcherSnd.hpp"

using namespace std;

string loginJson(string tarjeta, string pin) {
    return "{\"action\": \"login\", \"data\": {\"tarjeta\": \"" + tarjeta + "\", \"pin\": \"" + pin + "\"}}";
}

string retiroJson(double cantidad) {
    return "{\"action\": \"retiro\", \"data\": {\"cantidad\": " + to_string(cantidad) + "}}";
}

string buildLogoutJson() {
    return "{\"action\": \"logout\", \"data\": {}}";
}

// Capa de TRANSMISION: lee del socket hasta encontrar '\n'
string recibirInformacion(int sock) {
    string acumulado = "";
    char c;
    while (true) {
        int n = read(sock, &c, 1);
        if (n <= 0) return "";
        if (c == '\n') break;
        acumulado += c;
    }
    return acumulado;
}

// Capa de TRANSMISION: envia la trama delimitada por '\n'
void enviarInformacion(int sock, const string& cabecera, const string& trama) {
    string paquete = cabecera + "|" + trama + "\n";
    send(sock, paquete.c_str(), paquete.length(), 0);
}

int main() {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in serv_addr;
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(5050);
    inet_pton(AF_INET, "127.0.0.1", &serv_addr.sin_addr);

    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        cout << "Error de conexión al servidor." << endl;
        return -1;
    }

    SenderCapaPresentacion presentation;
    SenderHamming hamming;
    SenderFletcher fletcher(16);
    CapaRuido noise;

    // --- Capa de APLICACION: solicitar_mensaje pide algoritmo y tasa de error ---
    int opcionAlg = 0;
    cout << "=== CAJERO AUTOMATICO ===" << endl;
    cout << "Algoritmo de integridad:\n  1) Hamming (corrección)\n  2) Fletcher checksum (detección)\nOpción: ";
    cin >> opcionAlg;

    string cabecera = "HAM";
    if (opcionAlg == 2) {
        int bloque = 0;
        cout << "Tamaño de bloque Fletcher (8, 16 o 32): ";
        cin >> bloque;
        try {
            fletcher.setBlockSize(bloque);
        } catch (const invalid_argument& e) {
            cout << "Bloque inválido, se usará 16 por defecto." << endl;
            fletcher.setBlockSize(16);
        }
        cabecera = "FLE" + to_string(fletcher.getBlockSize());
    }
    
    double error_prob;
    cout << "Ingrese la probabilidad de error en la red (ej. 0.01 para 1%): ";
    cin >> error_prob;

    bool logged_in = false;
    
    while (true) {
        string json_msg = "";
        
        if (!logged_in) {
            string card, pin;
            cout << "\n Ingrese número de tarjeta: ";
            cin >> card;
            cout << "Ingrese PIN: ";
            cin >> pin;
            json_msg = loginJson(card, pin);
        } else {
            cout << "\n--- MENU ---\n1) Retirar dinero\n2) Logout\nElige una opción: ";
            string choice;
            cin >> choice;
            if (choice == "1") {
                double cantidad;
                cout << "Cantidad de retiro: ";
                cin >> cantidad;
                json_msg = retiroJson(cantidad);
            } else if (choice == "2") {
                json_msg = buildLogoutJson();
            } else {
                continue;
            }
        }

        string bin_msg = presentation.codificarMensaje(json_msg);

        // Capa de ENLACE
        string frame;
        if (opcionAlg == 2) {
            frame = fletcher.codificarFletcher(bin_msg);
        } else {
            frame = hamming.codificarHamming(bin_msg);
        }

        // Capa de RUIDO (afecta tambien a los bits de redundancia)
        string frame_ruido = noise.aplicarRuido(frame, error_prob);

        int flips = 0;
        for (size_t i = 0; i < frame.length(); i++) {
            if (frame[i] != frame_ruido[i]) flips++;
        }
        cout << "[enlace] trama de " << frame.length() << " bits ("
             << (frame.length() - bin_msg.length()) << " de redundancia) | "
             << "[ruido] " << flips << " bit(s) alterados" << endl;

        // Capa de TRANSMISION
        enviarInformacion(sock, cabecera, frame_ruido);

        string response = recibirInformacion(sock);
        if (response.empty()) {
            cout << "Conexión cerrada por el servidor." << endl;
            break;
        }

        cout << ">> Respuesta del servidor: " << response << endl;
        if (response.find("login_ok") != string::npos) {
            logged_in = true;
        } else if (response.find("logout_ok") != string::npos) {
            break;
        }
    }

    close(sock);
    return 0;
}