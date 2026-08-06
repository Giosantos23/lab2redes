"""
Capa de ENLACE (receptor) - Algoritmo de DETECCION de errores: Fletcher checksum.

Servicios implementados:
  - calcular_integridad  : separa datos/checksum y recalcula el checksum localmente
  - verificar_integridad : compara el checksum recibido contra el calculado
  - corregir_mensaje     : Fletcher NO corrige; solo devuelve los datos si no hubo error

Bloques configurables de 8, 16 o 32 bits. El checksum ocupa 2*bloque bits al final
de la trama.
"""


class ReceptorFletcher:
    def __init__(self, block_size=16):
        self.set_block_size(block_size)

    def set_block_size(self, block_size):
        if block_size not in (8, 16, 32):
            raise ValueError("El tamano de bloque debe ser 8, 16 o 32 bits.")
        self.block_size = block_size

    def _fletcher(self, data_bits):
        """Suma de Fletcher sobre una cadena binaria multiplo del tamano de bloque."""
        b = self.block_size
        modulo = (1 << b) - 1
        sum1 = 0
        sum2 = 0
        for i in range(0, len(data_bits), b):
            bloque = int(data_bits[i:i + b], 2)
            sum1 = (sum1 + bloque) % modulo
            sum2 = (sum2 + sum1) % modulo
        return format(sum2, f"0{b}b") + format(sum1, f"0{b}b")

    def calcular_integridad(self, received_frame):
        """
        Separa la trama en [datos] + [checksum] y recalcula el checksum del lado
        del receptor. Devuelve (datos, checksum_recibido, checksum_calculado).
        Si la trama esta mal formada devuelve (None, None, None).
        """
        b = self.block_size
        len_checksum = 2 * b

        if not received_frame or not set(received_frame) <= {"0", "1"}:
            return None, None, None
        if len(received_frame) <= len_checksum:
            return None, None, None

        datos = received_frame[:-len_checksum]
        checksum_recibido = received_frame[-len_checksum:]

        if len(datos) % b != 0:
            return None, None, None

        checksum_calculado = self._fletcher(datos)
        return datos, checksum_recibido, checksum_calculado

    def verificar_integridad(self, checksum_recibido, checksum_calculado):
        """Fletcher detecta pero no corrige: corregible siempre es False."""
        if checksum_recibido is None or checksum_calculado is None:
            return {"hay_error": True, "corregible": False, "trama_valida": False}
        hay_error = checksum_recibido != checksum_calculado
        return {"hay_error": hay_error, "corregible": False, "trama_valida": True}

    def corregir_mensaje(self, datos, hay_error):
        """
        Fletcher no tiene capacidad de correccion. Si hay error se descarta la trama;
        si no hay error se devuelven los datos tal cual (padding incluido, se retira
        en la capa de presentacion).
        """
        if hay_error:
            return None
        return datos

    def decodificar_fletcher(self, received_frame):
        """Servicio completo de la capa de enlace del lado del receptor."""
        datos, recibido, calculado = self.calcular_integridad(received_frame)
        chequeo = self.verificar_integridad(recibido, calculado)

        if not chequeo["trama_valida"]:
            return {"status": "invalid_frame", "data_original": None,
                    "checksum_recibido": None, "checksum_calculado": None}

        if chequeo["hay_error"]:
            return {"status": "error_detected", "data_original": None,
                    "checksum_recibido": recibido, "checksum_calculado": calculado}

        return {"status": "no_error", "data_original": self.corregir_mensaje(datos, False),
                "checksum_recibido": recibido, "checksum_calculado": calculado}


class EmisorFletcher:
    """
    Espejo en Python del emisor implementado en C++ (algFletcherSnd.hpp).
    NO se usa en la aplicacion cajero/servidor (ahi el emisor es C++);
    existe unicamente para el banco de pruebas y para validar que ambas
    implementaciones producen el mismo checksum.
    """

    def __init__(self, block_size=16):
        self.receptor = ReceptorFletcher(block_size)
        self.block_size = block_size

    def aplicar_padding(self, data):
        faltante = (-len(data)) % self.block_size
        return data + "0" * faltante

    def calcular_integridad(self, data):
        return self.receptor._fletcher(self.aplicar_padding(data))

    def codificar_fletcher(self, data):
        padded = self.aplicar_padding(data)
        return padded + self.receptor._fletcher(padded)
