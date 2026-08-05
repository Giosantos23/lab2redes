"""
Genera las graficas del reporte a partir de los CSV de pruebas.
Requiere: pruebas_fletcher.csv, pruebas_flips.csv, pruebas_overhead.csv, pruebas_hamming.csv
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

fletcher = pd.read_csv("pruebas_fletcher.csv")
flips = pd.read_csv("pruebas_flips.csv")
overhead = pd.read_csv("pruebas_overhead.csv")
hamming = pd.read_csv("pruebas_hamming.csv")

COLORES = {"Fletcher-16": "#1f77b4", "Fletcher-32": "#2ca02c",
           "Fletcher-64": "#9467bd", "Hamming": "#d62728"}

plt.rcParams.update({"figure.dpi": 150, "font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False,
                     "axes.spines.right": False})


# --- Figura 1: entrega correcta vs probabilidad de error ------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

for ax, n_chars in zip(axes, [20, 100]):
    sub_h = hamming[hamming.tamano_chars == n_chars]
    ax.plot(sub_h.prob_error, sub_h.tasa_exito_pct, "o-",
            color=COLORES["Hamming"], label="Hamming (corrige)")
    for alg in ["Fletcher-16", "Fletcher-32", "Fletcher-64"]:
        sub = fletcher[(fletcher.algoritmo == alg) & (fletcher.tamano_chars == n_chars)]
        ax.plot(sub.prob_error, sub.tasa_entrega_pct, "s--",
                color=COLORES[alg], label=alg, alpha=0.8, markersize=4)
    ax.set_xscale("log")
    ax.set_xlabel("Probabilidad de error por bit")
    ax.set_ylabel("Tramas entregadas correctamente (%)")
    ax.set_title(f"Mensaje de {n_chars} caracteres ({n_chars*8} bits)")
    ax.legend(fontsize=8)

fig.suptitle("Figura 1. Capacidad de entrega: correccion vs. deteccion", y=1.0)
fig.tight_layout()
fig.savefig("fig1_entrega.png", bbox_inches="tight")
plt.close(fig)


# --- Figura 2: fallos silenciosos (datos corruptos aceptados) -------------
fig, ax = plt.subplots(figsize=(7.5, 4.5))

for n_chars, marker in zip([5, 20, 50, 100], ["o", "s", "^", "D"]):
    sub_h = hamming[hamming.tamano_chars == n_chars]
    ax.plot(sub_h.prob_error, sub_h.miscorrected / sub_h.repeticiones * 100,
            marker + "-", color=COLORES["Hamming"], alpha=0.4 + 0.15 * [5, 20, 50, 100].index(n_chars),
            label=f"Hamming, {n_chars} chars", markersize=4)

sub_f = fletcher[fletcher.bloque_bits == 8].groupby("prob_error").agg(
    {"no_detectado": "sum", "repeticiones": "sum"}).reset_index()
ax.plot(sub_f.prob_error, sub_f.no_detectado / sub_f.repeticiones * 100,
        "*-", color=COLORES["Fletcher-16"], markersize=10,
        label="Fletcher-16 (todos los tamanos)", linewidth=2)

ax.set_xscale("log")
ax.set_xlabel("Probabilidad de error por bit")
ax.set_ylabel("Tramas corruptas aceptadas como validas (%)")
ax.set_title("Figura 2. Fallos silenciosos: el riesgo de corregir a ciegas")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("fig2_fallos_silenciosos.png", bbox_inches="tight")
plt.close(fig)


# --- Figura 3: deteccion segun numero exacto de bits alterados ------------
fig, (ax, ax_zoom) = plt.subplots(1, 2, figsize=(11.5, 4.5))

marcadores = {"Fletcher-16": "s", "Fletcher-32": "^", "Fletcher-64": "v"}
for alg in ["Fletcher-16", "Fletcher-32", "Fletcher-64", "Hamming"]:
    sub = flips[flips.algoritmo == alg]
    if alg == "Hamming":
        ax.plot(sub.bits_alterados, sub.tasa_pct, "o-", color=COLORES[alg],
                label=alg, markersize=5, linewidth=2)
    else:
        ax.plot(sub.bits_alterados, sub.tasa_pct, marcadores[alg] + "--",
                color=COLORES[alg], label=alg, markersize=5, alpha=0.85)
        ax_zoom.plot(sub.bits_alterados, sub.tasa_pct, marcadores[alg] + "--",
                     color=COLORES[alg], label=alg, markersize=6, alpha=0.85)

ax.set_xlabel("Numero exacto de bits alterados en la trama")
ax.set_ylabel("Tramas manejadas sin corrupcion silenciosa (%)")
ax.set_title("Vista general")
ax.set_ylim(-5, 105)
ax.set_xticks(range(1, 13))
ax.legend(fontsize=8, loc="center right")

ax_zoom.set_xlabel("Numero exacto de bits alterados en la trama")
ax_zoom.set_ylabel("Tasa de deteccion (%)")
ax_zoom.set_title("Zoom sobre las variantes de Fletcher")
ax_zoom.set_ylim(99.9, 100.02)
ax_zoom.set_xticks(range(1, 13))
ax_zoom.legend(fontsize=8, loc="lower left")

fig.suptitle("Figura 3. Robustez segun la cantidad de bits alterados "
             "(50 caracteres, 5000 repeticiones por punto)", y=1.02)
fig.tight_layout()
fig.savefig("fig3_flips.png", bbox_inches="tight")
plt.close(fig)


# --- Figura 4: overhead ---------------------------------------------------
fig, ax = plt.subplots(figsize=(7.5, 4.5))

for alg in ["Hamming", "Fletcher-16", "Fletcher-32", "Fletcher-64"]:
    sub = overhead[overhead.algoritmo == alg]
    ax.plot(sub.tamano_chars, sub.overhead_pct, "o-", color=COLORES[alg],
            label=alg, markersize=5)

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Tamano del mensaje (caracteres)")
ax.set_ylabel("Overhead (% de la trama que es redundancia)")
ax.set_title("Figura 4. Costo en redundancia de cada algoritmo")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("fig4_overhead.png", bbox_inches="tight")
plt.close(fig)


# --- Figura 5: integridad (mapa de calor) --------------------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4))

pivot_f = fletcher[fletcher.bloque_bits == 8].pivot(
    index="tamano_chars", columns="prob_error", values="tasa_integridad_pct")
hamming["integridad_pct"] = (hamming.no_error + hamming.corrected_ok +
                             hamming.uncorrectable_detected) / hamming.repeticiones * 100
pivot_h = hamming.pivot(index="tamano_chars", columns="prob_error", values="integridad_pct")

for ax, pivot, titulo in zip(axes, [pivot_h, pivot_f], ["Hamming", "Fletcher-16"]):
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, fontsize=8)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_xlabel("Probabilidad de error")
    ax.set_ylabel("Tamano (caracteres)")
    ax.set_title(titulo)
    ax.grid(False)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            ax.text(j, i, f"{pivot.values[i, j]:.0f}", ha="center", va="center",
                    fontsize=7, color="black")

fig.colorbar(im, ax=axes, label="Integridad (%)", fraction=0.025)
fig.suptitle("Figura 5. Integridad: tramas que no terminaron en corrupcion silenciosa", y=1.02)
fig.savefig("fig5_integridad.png", bbox_inches="tight")
plt.close(fig)

print("Graficas generadas: fig1..fig5")
