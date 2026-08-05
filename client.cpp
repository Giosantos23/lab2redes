#include <iostream>
#include <string>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include "algHammingSnd.hpp"

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
    CapaRuido noise;

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
        string frame_hamming = hamming.codificarHamming(bin_msg);
        string frame_ruido = noise.aplicarRuido(frame_hamming, error_prob);

        send(sock, frame_ruido.c_str(), frame_ruido.length(), 0);

        char buffer[4096] = {0};
        int valread = read(sock, buffer, 4096);
        if (valread > 0) {
            string response(buffer);
            cout << "\n>> Respuesta del servidor: " << response << endl;
            if (response.find("login_ok") != string::npos) {
                logged_in = true;
            } else if (response.find("logout_ok") != string::npos) {
                break;
            }
        }
    }
    
    close(sock);
    return 0;
}