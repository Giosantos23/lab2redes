#ifndef FLETCHERSEND_HPP
#define FLETCHERSEND_HPP

#include <iostream>
#include <string>
#include <cstdint>
#include <stdexcept>

using namespace std;

/*
 * Capa de ENLACE (emisor) - Algoritmo de DETECCION de errores: Fletcher checksum.
 *
 * Bloques configurables de 8, 16 o 32 bits:
 *   - bloque de  8 bits -> Fletcher-16 (checksum de 16 bits, modulo 255)
 *   - bloque de 16 bits -> Fletcher-32 (checksum de 32 bits, modulo 65535)
 *   - bloque de 32 bits -> Fletcher-64 (checksum de 64 bits, modulo 4294967295)
 *
 * Si la trama no es multiplo del tamano de bloque se agregan 0s de padding al final.
 * La trama resultante es: [datos + padding] + [checksum de 2*bloque bits]
 */
class SenderFletcher {
private:
    int blockSize;

public:
    SenderFletcher(int b = 16) { setBlockSize(b); }

    void setBlockSize(int b) {
        if (b != 8 && b != 16 && b != 32) {
            throw invalid_argument("El tamano de bloque debe ser 8, 16 o 32 bits.");
        }
        blockSize = b;
    }

    int getBlockSize() const { return blockSize; }

    // Agrega 0s al final hasta que la longitud sea multiplo del tamano de bloque
    string aplicarPadding(const string& data) const {
        string padded = data;
        while (padded.length() % blockSize != 0) {
            padded += '0';
        }
        return padded;
    }

    // calcular_integridad: devuelve los 2*blockSize bits de checksum
    string calcularIntegridad(const string& data) const {
        string padded = aplicarPadding(data);
        uint64_t modulo = (1ULL << blockSize) - 1ULL;
        uint64_t sum1 = 0, sum2 = 0;

        for (size_t i = 0; i < padded.length(); i += blockSize) {
            uint64_t bloque = stoull(padded.substr(i, blockSize), nullptr, 2);
            sum1 = (sum1 + bloque) % modulo;
            sum2 = (sum2 + sum1) % modulo;
        }

        // checksum = sum2 concatenado con sum1
        string bits = "";
        for (int i = blockSize - 1; i >= 0; i--) bits += ((sum2 >> i) & 1ULL) ? '1' : '0';
        for (int i = blockSize - 1; i >= 0; i--) bits += ((sum1 >> i) & 1ULL) ? '1' : '0';
        return bits;
    }

    // Concatena la informacion de integridad al mensaje binario original
    string codificarFletcher(const string& data) const {
        return aplicarPadding(data) + calcularIntegridad(data);
    }

    // Overhead en % respecto a la trama total (para las pruebas)
    double overhead(const string& data) const {
        double redundancia = 2.0 * blockSize;
        double total = aplicarPadding(data).length() + redundancia;
        return (redundancia / total) * 100.0;
    }
};

#endif
