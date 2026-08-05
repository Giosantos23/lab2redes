"""
Banco de pruebas - Laboratorio 2 (CC3067 Redes)

Simula la cadena completa emisor -> ruido -> receptor SIN sockets, para poder
ejecutar miles de repeticiones. El emisor en Python es un espejo exacto del
emisor en C++ (validado bit a bit, ver seccion de validacion cruzada del reporte).

Genera tres archivos CSV:
  1. pruebas_fletcher.csv   -> malla tamano x probabilidad x bloque
  2. pruebas_flips.csv      -> deteccion segun numero exacto de bits alterados
  3. pruebas_overhead.csv   -> overhead de cada algoritmo segun el tamano
"""

import csv
import os
import random
import string
import sys

# los modulos de la capa de enlace viven en la raiz del repositorio
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from algFletcherRe import EmisorFletcher, ReceptorFletcher
from alghammingRe import ReceptorHamming

SEMILLA = 2026
REPETICIONES = 300
REPETICIONES_FLIPS = 5000

TAMANOS = [5, 20, 50, 100]          # mismos tamanos usados en las pruebas de Hamming
PROBABILIDADES = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3]
BLOQUES = [8, 16, 32]


# ---------------------------------------------------------------- utilidades
def mensaje_aleatorio(n_chars):
    """Texto ASCII imprimible, como el JSON que envia el cajero."""
    alfabeto = string.ascii_letters + string.digits + '{}":, .'
    return "".join(random.choice(alfabeto) for _ in range(n_chars))


def codificar_ascii(texto):
    """Capa de presentacion: cada caracter a 8 bits."""
    return "".join(format(ord(c), "08b") for c in texto)


def aplicar_ruido(trama, prob):
    """Capa de ruido: cada bit se voltea de forma independiente con probabilidad prob."""
    bits = list(trama)
    flips = 0
    for i in range(len(bits)):
        if random.random() < prob:
            bits[i] = "1" if bits[i] == "0" else "0"
            flips += 1
    return "".join(bits), flips


def voltear_n_bits(trama, n):
    """Voltea exactamente n posiciones distintas elegidas al azar."""
    bits = list(trama)
    for i in random.sample(range(len(bits)), n):
        bits[i] = "1" if bits[i] == "0" else "0"
    return "".join(bits)


# ------------------------------------------------- emisor Hamming en Python
def codificar_hamming(data):
    """Espejo de SenderHamming::codificarHamming (algHammingSnd.hpp)."""
    m = len(data)
    r = 1
    while 2 ** r < m + r + 1:
        r += 1
    n = m + r

    codigo = [0] * (n + 1)
    idx = 0
    for i in range(1, n + 1):
        if i & (i - 1) != 0:          # no es potencia de 2
            codigo[i] = int(data[idx])
            idx += 1

    for i in range(r):
        pos = 2 ** i
        paridad = 0
        for j in range(1, n + 1):
            if (j & pos) != 0 and j != pos:
                paridad ^= codigo[j]
        codigo[pos] = paridad

    return "".join(str(codigo[i]) for i in range(1, n + 1)), r


# ------------------------------------------- experimento A: malla principal
def experimento_malla():
    filas = []
    for bloque in BLOQUES:
        emisor = EmisorFletcher(bloque)
        receptor = ReceptorFletcher(bloque)

        for n_chars in TAMANOS:
            for prob in PROBABILIDADES:
                random.seed(SEMILLA + n_chars * 1000 + int(prob * 10000) + bloque)

                sin_error = detectado = no_detectado = 0
                total_flips = 0
                bits_datos = redundancia = 0

                for _ in range(REPETICIONES):
                    texto = mensaje_aleatorio(n_chars)
                    binario = codificar_ascii(texto)
                    trama = emisor.codificar_fletcher(binario)

                    bits_datos = len(emisor.aplicar_padding(binario))
                    redundancia = 2 * bloque

                    trama_ruido, flips = aplicar_ruido(trama, prob)
                    total_flips += flips

                    resultado = receptor.decodificar_fletcher(trama_ruido)
                    acepta = resultado["status"] == "no_error"

                    if flips == 0:
                        sin_error += 1
                    elif acepta:
                        no_detectado += 1      # falso negativo: datos corruptos aceptados
                    else:
                        detectado += 1

                con_error = detectado + no_detectado
                tasa_det = (detectado / con_error * 100) if con_error else 100.0

                filas.append({
                    "algoritmo": f"Fletcher-{2*bloque}",
                    "bloque_bits": bloque,
                    "tamano_chars": n_chars,
                    "bits_datos": bits_datos,
                    "bits_redundancia": redundancia,
                    "overhead_pct": round(redundancia / (bits_datos + redundancia) * 100, 2),
                    "prob_error": prob,
                    "repeticiones": REPETICIONES,
                    "sin_error": sin_error,
                    "detectado": detectado,
                    "no_detectado": no_detectado,
                    "tasa_deteccion_pct": round(tasa_det, 2),
                    "tasa_entrega_pct": round(sin_error / REPETICIONES * 100, 2),
                    "tasa_integridad_pct": round((sin_error + detectado) / REPETICIONES * 100, 2),
                    "flips_promedio": round(total_flips / REPETICIONES, 2),
                })
    return filas


# ------------------------ experimento B: deteccion segun cantidad de flips
def experimento_flips(n_chars=50, max_flips=12):
    filas = []
    binario_base = codificar_ascii(mensaje_aleatorio(n_chars))

    # --- Fletcher, los tres tamanos de bloque ---
    for bloque in BLOQUES:
        emisor = EmisorFletcher(bloque)
        receptor = ReceptorFletcher(bloque)

        for k in range(1, max_flips + 1):
            random.seed(SEMILLA + bloque * 100 + k)
            detectado = no_detectado = 0

            for _ in range(REPETICIONES_FLIPS):
                texto = mensaje_aleatorio(n_chars)
                trama = emisor.codificar_fletcher(codificar_ascii(texto))
                trama_ruido = voltear_n_bits(trama, k)
                if receptor.decodificar_fletcher(trama_ruido)["status"] == "no_error":
                    no_detectado += 1
                else:
                    detectado += 1

            filas.append({
                "algoritmo": f"Fletcher-{2*bloque}",
                "bits_alterados": k,
                "repeticiones": REPETICIONES_FLIPS,
                "detectado_o_corregido": detectado,
                "fallo_silencioso": no_detectado,
                "tasa_pct": round(detectado / REPETICIONES_FLIPS * 100, 4),
            })

    # --- Hamming, para comparar ---
    receptor_h = ReceptorHamming()
    for k in range(1, max_flips + 1):
        random.seed(SEMILLA + 999 + k)
        ok = fallo_silencioso = 0

        for _ in range(REPETICIONES_FLIPS):
            texto = mensaje_aleatorio(n_chars)
            binario = codificar_ascii(texto)
            trama, _ = codificar_hamming(binario)
            trama_ruido = voltear_n_bits(trama, k)

            codigo, sindrome, n = receptor_h.calcular_integridad(trama_ruido)
            chequeo = receptor_h.verificar_integridad(sindrome, n)

            if not chequeo["corregible"]:
                ok += 1                                   # error detectado, trama descartada
            else:
                recuperado = receptor_h.corregir_mensaje(codigo, sindrome, n)
                if recuperado == binario:
                    ok += 1                               # error corregido correctamente
                else:
                    fallo_silencioso += 1                 # entrego datos incorrectos

        filas.append({
            "algoritmo": "Hamming",
            "bits_alterados": k,
            "repeticiones": REPETICIONES_FLIPS,
            "detectado_o_corregido": ok,
            "fallo_silencioso": fallo_silencioso,
            "tasa_pct": round(ok / REPETICIONES_FLIPS * 100, 4),
        })

    return filas


# ------------------------------------------- experimento C: overhead teorico
def experimento_overhead():
    filas = []
    for n_chars in [5, 10, 20, 50, 100, 200, 400]:
        m = n_chars * 8

        _, r = codificar_hamming("0" * m)
        filas.append({
            "algoritmo": "Hamming", "tamano_chars": n_chars, "bits_datos": m,
            "bits_redundancia": r, "overhead_pct": round(r / (m + r) * 100, 2),
        })

        for bloque in BLOQUES:
            emisor = EmisorFletcher(bloque)
            padded = len(emisor.aplicar_padding("0" * m))
            red = 2 * bloque
            filas.append({
                "algoritmo": f"Fletcher-{2*bloque}", "tamano_chars": n_chars,
                "bits_datos": padded, "bits_redundancia": red,
                "overhead_pct": round(red / (padded + red) * 100, 2),
            })
    return filas


def guardar(nombre, filas):
    with open(nombre, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        writer.writeheader()
        writer.writerows(filas)
    print(f"  -> {nombre} ({len(filas)} filas)")


if __name__ == "__main__":
    print("Experimento A: malla tamano x probabilidad x bloque ...")
    guardar("pruebas_fletcher.csv", experimento_malla())

    print("Experimento B: deteccion segun numero exacto de bits alterados ...")
    guardar("pruebas_flips.csv", experimento_flips())

    print("Experimento C: overhead por algoritmo ...")
    guardar("pruebas_overhead.csv", experimento_overhead())

    print("Listo.")
