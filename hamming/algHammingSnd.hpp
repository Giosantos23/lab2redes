#ifndef HAMMINGSEND_HPP
#define HAMMINGSEND_HPP

#include <iostream>
#include <string>
#include <vector>
#include <cmath>
#include <bitset>
#include <random>

using namespace std;

class SenderCapaPresentacion {
public:
    string codificarMensaje(const string& text) {
        string binaryString = "";
        for (char c : text) {
            binaryString += bitset<8>(c).to_string();
        }
        return binaryString;
    }
};

class SenderHamming {
private:
    int calcularBitsParidad(int dataBits) {
        int r = 1;
        while (pow(2, r) < dataBits + r + 1) {
            r++;
        }
        return r;
    }
    
    bool isPowerOf2(int n) {
        return n > 0 && (n & (n - 1)) == 0;
    }

public:
    string codificarHamming(string data) {
        int m = data.length();
        int r = calcularBitsParidad(m);
        int n = m + r;
        
        vector<int> hammingCode(n + 1, 0);
        int dataIndex = 0;
        for (int i = 1; i <= n; i++) {
            if (!isPowerOf2(i)) {
                hammingCode[i] = data[dataIndex] - '0';
                dataIndex++;
            }
        }
        
        for (int i = 0; i < r; i++) {
            int parityPos = pow(2, i);
            int parity = 0;
            for (int j = 1; j <= n; j++) {
                if ((j & parityPos) != 0 && j != parityPos) {
                    parity ^= hammingCode[j];
                }
            }
            hammingCode[parityPos] = parity;
        }
        
        string result = "";
        for (int i = 1; i <= n; i++) {
            result += to_string(hammingCode[i]);
        }
        return result;
    }
};

class CapaRuido {
public:
    string aplicarRuido(const string& frame, double errorProbability) {
        string frameRuido = frame;
        random_device rd;
        mt19937 gen(rd());
        uniform_real_distribution<> dis(0.0, 1.0);

        for (char& bit : frameRuido) {
            if (dis(gen) < errorProbability) {
                bit = (bit == '0') ? '1' : '0';
            }
        }
        return frameRuido;
    }
};

#endif