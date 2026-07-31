import math

class ReceptorCapaPresentacion:
    def decodificar_mensaje(self, binary_string, has_error):
        if has_error:
            return {"success": False, "data": None, "error_msg": "Error no corregible ."}
        
        if not binary_string or len(binary_string) % 8 != 0:
            return {"success": False, "data": None, "error_msg": "Trama incompleta."}

        decoded_chars = []
        try:
            for i in range(0, len(binary_string), 8):
                byte = binary_string[i:i+8]
                char = chr(int(byte, 2))
                decoded_chars.append(char)
            return {"success": True, "data": "".join(decoded_chars), "error_msg": None}
        except Exception as e:
            return {"success": False, "data": None, "error_msg": f"Error ASCII: {str(e)}"}

class ReceptorHamming:
    def __init__(self):
        pass
    
    def es_poder_2(self, n):
        return n > 0 and (n & (n - 1)) == 0
    
    def calcular_bits_paridad(self, total_bits):
        r = 1
        while 2**r < total_bits + 1:
            r += 1
        return r

    def calcular_integridad(self, received_data):
        n = len(received_data)
        r = self.calcular_bits_paridad(n)
        codigo_hamming = [0] + [int(bit) for bit in received_data]
        error_syn = 0

        for i in range(r):
            parity_pos = 2**i
            paridad_calculada = 0
            for j in range(1, n + 1):
                if (j & parity_pos) != 0 and j != parity_pos:
                    paridad_calculada ^= codigo_hamming[j]
            paridad_recibida = codigo_hamming[parity_pos]
            if paridad_recibida != paridad_calculada:
                error_syn += parity_pos

        return codigo_hamming, error_syn, n

    def verificar_integridad(self, error_syn, n):
        if error_syn == 0:
            return {'hay_error': False, 'corregible': True}
        elif error_syn <= n:
            return {'hay_error': True, 'corregible': True}
        else:
            return {'hay_error': True, 'corregible': False}

    def corregir_mensaje(self, codigo_hamming, error_syn, n):
        if error_syn != 0:
            codigo_hamming[error_syn] = 1 - codigo_hamming[error_syn]

        data_og = ""
        for i in range(1, n + 1):
            if not self.es_poder_2(i):
                data_og += str(codigo_hamming[i])
        return data_og

    def decodificar_hamming(self, received_data):
        print(f"Receptor código de Hamming")
        codigo_hamming, error_syn, n = self.calcular_integridad(received_data)
        chequeo = self.verificar_integridad(error_syn, n)

        if not chequeo['hay_error']:
            data_og = self.corregir_mensaje(codigo_hamming, error_syn, n)
            return {'status': 'no_error', 'data_original': data_og, 'posicion_corregida': None}
        elif chequeo['corregible']:
            data_og = self.corregir_mensaje(codigo_hamming, error_syn, n)
            return {'status': 'corrected', 'data_original': data_og, 'posicion_corregida': error_syn}
        else:
            return {'status': 'uncorrectable_error', 'data_original': None, 'posicion_corregida': None}