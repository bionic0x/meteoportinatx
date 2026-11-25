#!/usr/bin/env python3
"""Genera src/pirineo_orografia.json: tablas estáticas de relieve para el Pirineo Nowcast.

Fuera del núcleo (necesita numpy y scipy). El núcleo (pirineo_orografia.py) solo lee el JSON.

Contenido:
  1. Precipitación orográfica lineal de Smith y Barstad (2004) por punto de control y por muestra
     de carretera, para 16 direcciones del flujo a 700 hPa con U = 14 m/s, y el signo del
     ascenso forzado (barlovento/sotavento). Parámetros de humedad por sector: HIPÓTESIS.
  2. Índice de cubeta fría (CPI) por punto y por muestra de carretera: hundimiento respecto al
     percentil 75 del relieve en ~13 km × log10 del área que drena aire frío (D8).
  3. Red viaria aproximada (puntos de paso ±1–2 km) con perfil ajustado al fondo de valle.

Uso:
  python3 scripts/build_orografia_pirineo.py --dem-npz dem.npz [--roads-cache roads_cache.json]
  python3 scripts/build_orografia_pirineo.py            # descarga el DEM de la API de elevación de Open-Meteo

El DEM de la API de Open-Meteo es Copernicus GLO-90. Nada de esto está calibrado con observaciones.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, generic_filter, uniform_filter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import pirineo  # noqa: E402

OUT = ROOT / "src" / "pirineo_orografia.json"
DOMAIN = {"lat_s": 42.15, "lat_n": 43.05, "lon_w": 1.15, "lon_e": 2.65, "step": 0.01}
DIRS = [i * 22.5 for i in range(16)]
U_REF = 14.0
NM = 0.004
TAU = 1000.0
# Humedad por sector (Cw kg m-3, Hw m): aire atlántico/polar más seco, mediterráneo más húmedo. HIPÓTESIS.
SECTOR_MOIST = {0: (0.0030, 1800), 45: (0.0035, 2000), 90: (0.0060, 2500), 135: (0.0070, 3000),
                180: (0.0065, 3000), 225: (0.0060, 3000), 270: (0.0040, 2500), 315: (0.0035, 2000)}

def _v(*pts):
    """Puntos intermedios sin nombre (trazado por el fondo de valle, camino de menor coste en malla de 0,0025°)."""
    return [("·", la, lo) for la, lo in pts]


V_HOSP_MERENS = _v((42.5939, 1.805), (42.6014, 1.81), (42.6089, 1.815), (42.6164, 1.82), (42.6239, 1.8225), (42.6314, 1.825),
                   (42.6389, 1.83), (42.6464, 1.8325))
V_MERENS_AX = _v((42.6608, 1.8364), (42.6683, 1.8364), (42.6758, 1.8364), (42.6833, 1.8289), (42.6883, 1.8239), (42.6933, 1.8314),
                 (42.7008, 1.8339), (42.7083, 1.8364), (42.7158, 1.8364))
V_PUYMORENS_N = _v((42.5825, 1.7950), (42.5750, 1.7900), (42.5675, 1.7925), (42.5675, 1.8000))      # L'Hospitalet → collado
V_PUYMORENS_S = _v((42.5550, 1.8150), (42.5475, 1.8225))                                          # collado → Porté
V_PORTE_LATOUR = _v((42.545, 1.8295), (42.5375, 1.8245), (42.53, 1.822)) + [("Porta", 42.5260, 1.8253)] + _v(
    (42.521, 1.822), (42.5135, 1.8245), (42.506, 1.832), (42.501, 1.8395), (42.496, 1.847), (42.4885, 1.8545), (42.481, 1.862),
    (42.4735, 1.8695), (42.471, 1.877), (42.4635, 1.8845))
V_AX_TARASCON = _v((42.7227, 1.835), (42.7252, 1.8275), (42.7277, 1.82), (42.7277, 1.8125), (42.7302, 1.805), (42.7352, 1.7975),
                   (42.7402, 1.79), (42.7427, 1.7825), (42.7502, 1.775), (42.7577, 1.7675)) + [("Luzenac", 42.7636, 1.7625)] + _v(
    (42.7661, 1.749), (42.7686, 1.7415), (42.7736, 1.734), (42.7736, 1.7265), (42.7736, 1.719), (42.7736, 1.7115), (42.7736, 1.704),
    (42.7811, 1.6965)) + [("Les Cabannes", 42.7861, 1.6865)] + _v(
    (42.7886, 1.6806), (42.7961, 1.6731), (42.7986, 1.6656), (42.7986, 1.6581), (42.8036, 1.6506), (42.8086, 1.6431),
    (42.8136, 1.6356), (42.8161, 1.6281), (42.8236, 1.6206), (42.8311, 1.6131), (42.8386, 1.6056))
V_PAILHERES = _v((42.7202, 1.8444), (42.7202, 1.8519)) + [("Ascou", 42.7214, 1.8619)] + _v(
    (42.7189, 1.8669), (42.7189, 1.8744), (42.7214, 1.8819), (42.7239, 1.8894), (42.7214, 1.8969), (42.7214, 1.9044), (42.7189, 1.9119),
    (42.7164, 1.9194), (42.7164, 1.9269), (42.7189, 1.9344), (42.7239, 1.9419), (42.7289, 1.9494), (42.7289, 1.9569), (42.7289, 1.9644),
    (42.7289, 1.9719), (42.7314, 1.9794)) + [("Col de Pailhères", 42.7314, 1.9889)] + _v(
    (42.7279, 1.9939), (42.7279, 2.0014), (42.7279, 2.0089), (42.7279, 2.0164), (42.7254, 2.0239), (42.7229, 2.0314), (42.7229, 2.0389),
    (42.7254, 2.0464))

# Trazados aproximados (±0,5–2 km donde no hay puntos de valle). Coordenadas de núcleos: geocodificador de Open-Meteo (GeoNames).
ROADS = {
    "cg2": ("CG-2 Encamp–Envalira–Pas de la Casa", "AD", [("Encamp", 42.5345, 1.5803), ("Canillo", 42.5667, 1.5985), ("El Tarter", 42.5795, 1.6536),
            ("Soldeu", 42.5767, 1.6672), ("Grau Roig", 42.5333, 1.7006), ("Port d'Envalira", 42.5404, 1.7199), ("Pas de la Casa", 42.5423, 1.7334)]),
    "cg3": ("CG-3 Ordino–Arcalís", "AD", [("Ordino", 42.5560, 1.5333), ("La Cortinada", 42.5742, 1.5185), ("El Serrat", 42.6180, 1.5390), ("Arcalís", 42.6290, 1.5060)]),
    "rn22": ("RN22 Pas de la Casa–cruce RN20", "FR", [("Pas de la Casa", 42.5423, 1.7334), ("·", 42.5560, 1.7600),
             ("Cruce RN22/RN20", 42.5750, 1.7900)]),
    "rn20_ariege": ("RN20 Tarascon–Ax-les-Thermes–Mérens–L'Hospitalet", "FR",
                    [("Tarascon-sur-Ariège", 42.8471, 1.6056)] + V_AX_TARASCON[::-1] + [("Ax-les-Thermes", 42.7202, 1.8394)]
                    + V_MERENS_AX[::-1] + [("Mérens-les-Vals", 42.6579, 1.8363)] + V_HOSP_MERENS[::-1]
                    + [("L'Hospitalet-près-l'Andorre", 42.5883, 1.7983)]),
    "rn20_puymorens": ("RN20 L'Hospitalet–Col du Puymorens–Porté–Latour-de-Carol–Bourg-Madame", "FR",
                       [("L'Hospitalet-près-l'Andorre", 42.5883, 1.7983)] + V_PUYMORENS_N + [("Col du Puymorens", 42.5600, 1.8075)]
                       + V_PUYMORENS_S + [("Porté-Puymorens", 42.5480, 1.8350)] + V_PORTE_LATOUR
                       + [("Latour-de-Carol", 42.4649, 1.8900), ("Enveitg", 42.4605, 1.9129), ("Bourg-Madame", 42.4350, 1.9450)]),
    "rn116": ("RN116 Bourg-Madame–Col de la Perche–Mont-Louis–Thuès", "FR", [("Bourg-Madame", 42.4350, 1.9450), ("Saillagouse", 42.4580, 2.0360),
              ("Col de la Perche", 42.4952, 2.0884), ("Mont-Louis", 42.5085, 2.1217), ("Fontpédrouse", 42.5120, 2.1900), ("Thuès", 42.5270, 2.2260)]),
    "d618": ("D618 Ur–Targasonne–Odeillo–Font-Romeu–Col de la Perche", "FR", [("Ur", 42.4622, 1.9377), ("Targasonne", 42.4999, 1.9971),
             ("Odeillo", 42.4977, 2.0339), ("Font-Romeu", 42.5050, 2.0350), ("Bolquère", 42.4970, 2.0720), ("Col de la Perche", 42.4952, 2.0884)]),
    "d118": ("D118 Mont-Louis–La Llagonne–Les Angles–Formiguères–Puyvalador (Capcir)", "FR", [("Mont-Louis", 42.5085, 2.1217),
             ("La Llagonne", 42.5271, 2.1195), ("Cruce Les Angles", 42.5700, 2.0850), ("Matemale", 42.5850, 2.1100),
             ("Formiguères", 42.6147, 2.1044), ("Puyvalador", 42.6466, 2.1202)]),
    "d613_pailheres": ("D613/D25 Ax–Ascou–Col de Pailhères–Mijanès (cerrada en invierno)", "FR",
                       [("Ax-les-Thermes", 42.7202, 1.8394)] + V_PAILHERES + [("Mijanès", 42.7304, 2.0563)]),
    "n260_toses": ("N-260 Ribes–Collada de Toses–Alp–Puigcerdà", "CAT", [("Planoles", 42.3167, 2.1000), ("Toses", 42.3216, 2.0158), ("Collada de Toses", 42.3335, 1.9865),
                   ("Cruce La Molina", 42.3450, 1.9550), ("Alp", 42.3730, 1.8860), ("Puigcerdà", 42.4319, 1.9283)]),
    "n260_seu": ("N-260 Puigcerdà–Bellver–Martinet–La Seu d'Urgell", "CAT", [("Puigcerdà", 42.4319, 1.9283), ("Bellver", 42.3700, 1.7770)]
                 + _v((42.3696, 1.7683), (42.3696, 1.7583), (42.3671, 1.7483), (42.3671, 1.7383), (42.3671, 1.7283), (42.3646, 1.7183),
                      (42.3646, 1.7083)) + [("Martinet", 42.3596, 1.6958)]
                 + _v((42.3605, 1.688), (42.3655, 1.678), (42.363, 1.668), (42.363, 1.658), (42.3655, 1.648), (42.373, 1.6405),
                      (42.373, 1.6305), (42.3705, 1.6205), (42.3705, 1.6105), (42.3705, 1.6005), (42.3655, 1.5905), (42.358, 1.5805),
                      (42.358, 1.5705), (42.358, 1.5605), (42.358, 1.5505), (42.3555, 1.5405), (42.3555, 1.5305), (42.3555, 1.5205),
                      (42.3555, 1.5105), (42.3555, 1.5005), (42.3555, 1.4905), (42.358, 1.4805), (42.358, 1.4705))
                 + [("La Seu d'Urgell", 42.3580, 1.4580)]),
    "c16": ("C-16 Túnel del Cadí–Das–Puigcerdà (trazado aproximado)", "CAT", [("Boca norte del Cadí (aprox.)", 42.3200, 1.8350),
            ("Urús", 42.3513, 1.8534), ("Das", 42.3800, 1.8660), ("Puigcerdà", 42.4319, 1.9283)]),
    "acc_estaciones": ("Accesos Alp–Masella (aproximado)", "CAT", [("Alp", 42.3730, 1.8860), ("Masella", 42.3500, 1.9000)]),
    "n154": ("N-154 Puigcerdà–Llívia", "CAT", [("Puigcerdà", 42.4319, 1.9283), ("Llívia", 42.4650, 1.9800)]),
}
PASSES = {"Port d'Envalira": 2408, "Col du Puymorens": 1915, "Col de la Perche": 1581, "Collada de Toses": 1800, "Pas de la Casa": 2085,
          "Col de Pailhères": 2001}

# ── Puntos de control adicionales (no piden previsión por punto: usan el perfil de su vertiente y la tabla de relieve) ──
# tipo: cima | collado | pueblo | estacion_esqui. Coordenadas y altitud: geocodificador de Open-Meteo (GeoNames) salvo
# Ax 3 Domaines (Wikipedia). Estaciones: punto de referencia y rango esquiable publicado (fuente en «fuente»).
EXTRA = [
    # Ariège y Donezan (vertiente norte)
    ("tarascon", "Tarascon-sur-Ariège", 42.8471, 1.6056, "pueblo", "Ariège", "norte", 479),
    ("les_cabannes", "Les Cabannes", 42.7861, 1.6865, "pueblo", "Ariège", "norte", 537),
    ("luzenac", "Luzenac", 42.7636, 1.7625, "pueblo", "Ariège", "norte", 609),
    ("ax", "Ax-les-Thermes", 42.7202, 1.8394, "pueblo", "Ariège", "norte", 727),
    ("orlu", "Orlu", 42.7020, 1.8882, "pueblo", "Ariège", "norte", 847),
    ("ascou", "Ascou", 42.7214, 1.8619, "pueblo", "Ariège", "norte", 1032),
    ("merens", "Mérens-les-Vals", 42.6579, 1.8363, "pueblo", "Ariège", "norte", 1064),
    ("hospitalet", "L'Hospitalet-près-l'Andorre", 42.5883, 1.7983, "pueblo", "Ariège", "norte", 1433),
    ("camurac", "Camurac", 42.7986, 1.9155, "pueblo", "Donezan / Pays de Sault", "norte", 1218),
    ("mijanes", "Mijanès", 42.7304, 2.0563, "pueblo", "Donezan / Pays de Sault", "norte", 1142),
    ("querigut", "Quérigut", 42.6988, 2.0983, "pueblo", "Donezan / Pays de Sault", "norte", 1225),
    ("col_pailheres", "Col de Pailhères", 42.7314, 1.9889, "collado", "Ariège", "norte", 2001),
    ("pic_st_barthelemy", "Pic de Saint-Barthélemy", 42.8187, 1.7705, "cima", "Ariège", "norte", 2348),
    ("pic_soularac", "Pic de Soularac", 42.8170, 1.7800, "cima", "Ariège", "norte", 2368),
    ("mont_fourcat", "Mont Fourcat", 42.8550, 1.7161, "cima", "Ariège", "norte", 2001),
    ("pic_tarbesou", "Pic de Tarbésou", 42.7138, 1.9707, "cima", "Ariège", "norte", 2364),
    ("pic_rulhe", "Pic de Rulhe", 42.6271, 1.7390, "cima", "Ariège", "norte", 2783),
    ("pic_thoumasset", "Pic de Thoumasset", 42.6538, 1.5827, "cima", "Ariège", "norte", 2741),
    ("pic_baxouillade", "Pic de Baxouillade", 42.6619, 1.9993, "cima", "Ariège", "norte", 2546),
    ("pic_nerassol", "Pic de Nérassol", 42.6011, 1.7635, "cima", "Ariège", "norte", 2633),
    # Divisoria Ariège–Andorra–Carol
    ("pic_cabaneta", "Pic de la Cabaneta", 42.5886, 1.7276, "cima", "Andorra", "divisoria", 2818),
    ("pic_fontargente", "Pic de Fontargente", 42.6219, 1.6921, "cima", "Andorra", "divisoria", 2618),
    ("pic_escobes", "Pic d'Escobes", 42.6091, 1.7357, "cima", "Andorra", "divisoria", 2779),
    ("pic_serrera", "Pic de la Serrera", 42.6256, 1.6010, "cima", "Andorra", "divisoria", 2912),
    ("pic_font_blanca", "Pic de Font Blanca", 42.6499, 1.5342, "cima", "Andorra", "divisoria", 2903),
    ("pic_tristaina", "Pic de Tristaina", 42.6534, 1.4924, "cima", "Andorra", "divisoria", 2878),
    ("puig_pedros_n", "Puig Pedrós (Lanós)", 42.5900, 1.8736, "cima", "Puymorens", "divisoria", 2842),
    ("pic_mina", "Pic de la Mina", 42.5368, 1.7722, "cima", "Puymorens", "divisoria", 2682),
    ("puig_peric", "Puig Peric", 42.6135, 1.9844, "cima", "Capcir", "divisoria", 2810),
    ("pic_montcalm", "Pic de Montcalm", 42.6726, 1.4064, "cima", "Ariège", "divisoria", 3077),
    ("pica_estats", "Pica d'Estats", 42.6672, 1.3976, "cima", "Ariège", "divisoria", 3143),
    ("pic_medecourbe", "Pic de Medécourbe", 42.6037, 1.4426, "cima", "Andorra", "divisoria", 2914),
    ("puig_coma_dor", "Puig de Coma d'Or", 42.5834, 1.8736, "cima", "Puymorens", "divisoria", 2826),
    # Andorra
    ("pic_estanyo", "Pic de l'Estanyó", 42.6088, 1.5923, "cima", "Andorra", "sur", 2915),
    ("la_cortinada", "La Cortinada", 42.5742, 1.5185, "pueblo", "Andorra", "sur", 1335),
    ("pic_coma_pedrosa", "Pic de Coma Pedrosa", 42.5912, 1.4428, "cima", "Andorra", "sur", 2943),
    ("pic_casamanya", "Pic de Casamanya", 42.5874, 1.5704, "cima", "Andorra", "sur", 2749),
    ("pic_envalira", "Pic d'Envalira (nombre y cota de GeoNames, por verificar)", 42.5167, 1.7333, "cima", "Andorra", "divisoria", 2664),
    ("pic_pessons", "Pic dels Pessons", 42.5078, 1.6653, "cima", "Andorra", "sur", 2864),
    ("el_tarter", "El Tarter", 42.5795, 1.6536, "pueblo", "Andorra", "sur", 1721),
    ("arinsal", "Arinsal", 42.5720, 1.4845, "pueblo", "Andorra", "sur", 1465),
    # Cerdanya, Cerdagne, Puigmal y Cadí (vertiente sur)
    ("puigpedros", "Puigpedrós", 42.4876, 1.7619, "cima", "Cerdanya", "sur", 2915),
    ("tossa_plana_lles", "Tossa Plana de Lles", 42.4681, 1.6571, "cima", "Cerdanya", "sur", 2905),
    ("pic_calm_colomer", "Pic de Calm Colomer", 42.4925, 1.7300, "cima", "Cerdanya", "sur", 2869),
    ("roc_colom", "Roc Colom", 42.4958, 1.7579, "cima", "Cerdanya", "sur", 2680),
    ("pic_noufonts", "Pic de Noufonts", 42.4198, 2.1741, "cima", "Cerdagne", "sur", 2851),
    ("pic_infern", "Pic de l'Infern", 42.4239, 2.2138, "cima", "Cerdagne", "sur", 2868),
    ("gra_fajol", "Gra de Fajol", 42.4155, 2.2477, "cima", "Ripollès", "sur", 2714),
    ("puig_redon", "Puig Redon", 42.4653, 2.2055, "cima", "Cerdagne", "sur", 2677),
    ("pic_orri", "Pic de l'Orri", 42.4603, 2.1599, "cima", "Cerdagne", "sur", 2561),
    ("comabona", "Comabona (Cadí)", 42.2837, 1.7263, "cima", "Cerdanya", "sur", 2548),
    ("pedraforca", "Pedraforca", 42.2399, 1.7029, "cima", "Berguedà", "sur", 2506),
    ("martinet", "Martinet", 42.3596, 1.6958, "pueblo", "Cerdanya", "sur", 965),
    ("prullans", "Prullans", 42.3788, 1.7377, "pueblo", "Cerdanya", "sur", 1082),
    ("lles", "Lles de Cerdanya", 42.3903, 1.6869, "pueblo", "Cerdanya", "sur", 1475),
    ("urus", "Urús", 42.3513, 1.8534, "pueblo", "Cerdanya", "sur", 1277),
    ("bolvir", "Bolvir", 42.4177, 1.8799, "pueblo", "Cerdanya", "sur", 1114),
    ("guils", "Guils de Cerdanya", 42.4474, 1.8801, "pueblo", "Cerdanya", "sur", 1367),
    ("latour_carol", "Latour-de-Carol", 42.4649, 1.8900, "pueblo", "Carol", "sur", 1254),
    ("enveitg", "Enveitg", 42.4605, 1.9129, "pueblo", "Cerdagne", "sur", 1267),
    ("porta", "Porta", 42.5260, 1.8253, "pueblo", "Carol", "sur", 1514),
    ("ur", "Ur", 42.4622, 1.9377, "pueblo", "Cerdagne", "sur", 1211),
    ("estavar", "Estavar", 42.4677, 1.9955, "pueblo", "Cerdagne", "sur", 1218),
    ("targasonne", "Targasonne", 42.4999, 1.9971, "pueblo", "Cerdagne", "sur", 1610),
    ("odeillo", "Odeillo", 42.4977, 2.0339, "pueblo", "Cerdagne", "sur", 1590),
    ("err", "Err", 42.4416, 2.0331, "pueblo", "Cerdagne", "sur", 1369),
    ("llo", "Llo", 42.4546, 2.0613, "pueblo", "Cerdagne", "sur", 1418),
    ("eyne", "Eyne", 42.4737, 2.0818, "pueblo", "Cerdagne", "sur", 1573),
    ("st_pierre_forcats", "Saint-Pierre-dels-Forcats", 42.4941, 2.1187, "pueblo", "Cerdagne", "sur", 1580),
    ("mont_louis", "Mont-Louis", 42.5085, 2.1217, "pueblo", "Haut-Conflent", "divisoria", 1585),
    ("la_llagonne", "La Llagonne", 42.5271, 2.1195, "pueblo", "Haut-Conflent", "divisoria", 1678),
    ("real", "Réal", 42.6312, 2.1334, "pueblo", "Capcir", "norte", 1444),
    ("puyvalador", "Puyvalador", 42.6466, 2.1202, "pueblo", "Capcir", "norte", 1471),
    ("pic_madres", "Pic de Madres", 42.6511, 2.1883, "cima", "Capcir", "norte", 2469),
    ("puig_tossa", "Puig de la Tossa", 42.5308, 2.1498, "cima", "Capcir", "norte", 2034),
    ("canigo", "Pic du Canigou", 42.5188, 2.4568, "cima", "Conflent", "sur", 2784),   # contexto: sin perfil propio
    ("toses_poble", "Toses", 42.3216, 2.0158, "pueblo", "Ripollès", "sur", 1447),
    ("planoles", "Planoles", 42.3167, 2.1000, "pueblo", "Ripollès", "sur", 1142),
    ("nuria", "Vall de Núria", 42.3971, 2.1534, "pueblo", "Ripollès", "sur", 2180),
    ("ribes", "Ribes de Freser", 42.3042, 2.1676, "pueblo", "Ripollès", "sur", 1077),
]
# Estaciones de esquí: (id, nombre, punto de referencia (lat, lon), vertiente, zona, base_m, techo_m, estado, fuente)
ESTACIONES = [
    ("est_ax3d", "Ax 3 Domaines", (42.7008, 1.8139), "norte", "Ariège", 1400, 2400, "abierta", "Wikipedia / skiinfo"),
    ("est_ascou", "Ascou-Pailhères", (42.7289, 1.9569), "norte", "Ariège", 1500, 2060, "abierta",
     "alti-mag; referencia: punto de la D613 a ~1.500 m bajo Pailhères (aproximada)"),
    ("est_mijanes", "Mijanès-Donezan", (42.7279, 2.0164), "norte", "Donezan / Pays de Sault", 1530, 2000, "abierta",
     "alti-mag; referencia: punto de la D25 a ~1.540 m bajo Pailhères (aproximada)"),
    ("est_camurac", "Camurac", (42.7986, 1.9155), "norte", "Donezan / Pays de Sault", 1219, 1800, "abierta", "alti-mag; base = altitud del pueblo (aproximada, no la cota inferior de pistas)"),
    ("est_les_angles", "Les Angles", (42.5784, 2.0748), "norte", "Capcir", 1640, 2360, "abierta", "alti-mag"),
    ("est_formigueres", "Formiguères", (42.6147, 2.1044), "norte", "Capcir", 1500, 2300, "abierta", "alti-mag; base = altitud del pueblo (aproximada, no la cota inferior de pistas)"),
    ("est_puyvalador", "Puyvalador", (42.6500, 2.0900), "norte", "Capcir", 1700, 2382, "cerrada", "remontees-mecaniques.net / skiinfo; referencia: snow-forecast (42,65 N 2,09 E)"),
    ("est_font_romeu", "Font-Romeu", (42.5050, 2.0350), "sur", "Cerdagne", 1750, 2200, "abierta", "alti-mag"),
    ("est_pyrenees2000", "Pyrénées 2000 (Bolquère)", (42.4970, 2.0720), "sur", "Cerdagne", 1800, 2200, "abierta", "alti-mag"),
    ("est_cambre_aze", "Cambre d'Aze", (42.4941, 2.1187), "sur", "Cerdagne", 1640, 2400, "abierta", "skiinfo / tourisme-pyreneesorientales"),
    ("est_porte", "Porté-Puymorens", (42.5480, 1.8350), "divisoria", "Puymorens", 1640, 2470, "abierta", "alti-mag"),
    ("est_la_molina", "La Molina", (42.3400, 1.9400), "sur", "Cerdanya", 1700, 2537, "abierta", "dato de memoria, sin verificar"),
    ("est_masella", "Masella", (42.3500, 1.9000), "sur", "Cerdanya", 1600, 2535, "abierta", "dato de memoria, sin verificar"),
    ("est_gv_pas", "Grandvalira – Pas de la Casa / Grau Roig", (42.5423, 1.7334), "divisoria", "Andorra", 2050, 2640, "abierta",
     "j2ski (base del sector) / skiresort.info (techo del dominio)"),
    ("est_gv_soldeu", "Grandvalira – Soldeu / El Tarter", (42.5795, 1.6536), "sur", "Andorra", 1710, 2640, "abierta",
     "skiresort.info (base y techo del dominio)"),
    ("est_arcalis", "Ordino Arcalís", (42.6290, 1.5060), "divisoria", "Andorra", 1940, 2600, "abierta", "skiresort.info / j2ski"),
    ("est_pal_arinsal", "Pal Arinsal", (42.5720, 1.4845), "sur", "Andorra", 1550, 2560, "abierta", "palarinsal.com / skiresort.info"),
]
BASIN_ZONES = ("Cerdanya", "Cerdagne", "Capcir")
BASIN_KM = 6.0


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))


def elevation_api(points):
    out = []
    for i in range(0, len(points), 100):
        ch = points[i:i + 100]
        q = urllib.parse.urlencode({"latitude": ",".join(f"{a:.5f}" for a, _ in ch), "longitude": ",".join(f"{b:.5f}" for _, b in ch)})
        for k in range(8):
            try:
                with urllib.request.urlopen("https://api.open-meteo.com/v1/elevation?" + q, timeout=60) as r:
                    out += json.loads(r.read())["elevation"]
                break
            except Exception:
                time.sleep(15 * (k + 1))
        else:
            raise SystemExit("API de elevación no disponible")
        time.sleep(2)
    return out


def load_dem(path):
    if path:
        d = np.load(path)
        return d["lats"], d["lons"], d["z"]
    lats = np.round(np.arange(DOMAIN["lat_s"], DOMAIN["lat_n"] + 1e-9, DOMAIN["step"]), 4)
    lons = np.round(np.arange(DOMAIN["lon_w"], DOMAIN["lon_e"] + 1e-9, DOMAIN["step"]), 4)
    pts = [(a, b) for a in lats for b in lons]
    return lats, lons, np.array(elevation_api(pts), float).reshape(len(lats), len(lons))


def moisture(d):
    """Cw y Hw interpolados entre los ocho sectores."""
    a = (d // 45) * 45 % 360
    b = (a + 45) % 360
    f = (d - (d // 45) * 45) / 45
    ca, ha = SECTOR_MOIST[int(a)]
    cb, hb = SECTOR_MOIST[int(b)]
    return ca + (cb - ca) * f, ha + (hb - ha) * f


def smith_barstad(z, dx, dy, wdir, U, Cw, Hw, pad=60):
    h = np.pad(np.clip(z - 300.0, 0, None), pad, mode="linear_ramp", end_values=0)
    ny, nx = h.shape
    K, L = np.meshgrid(2 * np.pi * np.fft.fftfreq(nx, dx), 2 * np.pi * np.fft.fftfreq(ny, dy))
    th = math.radians(wdir)
    u, v = -U * math.sin(th), -U * math.cos(th)
    sig = u * K + v * L
    s2 = np.where(sig == 0, 1e-18, sig ** 2)
    m2 = (NM ** 2 - s2) / s2 * (K ** 2 + L ** 2)
    m = np.where(m2 >= 0, np.sign(sig) * np.sqrt(np.abs(m2)), 1j * np.sqrt(np.abs(m2)))
    P = Cw * 1j * sig * np.fft.fft2(h) / ((1 - 1j * m * Hw) * (1 + 1j * sig * TAU) * (1 + 1j * sig * TAU))
    return np.clip(np.real(np.fft.ifft2(P))[pad:-pad, pad:-pad] * 3600, 0, None)      # mm/h


def d8_accumulation(z, dx_km, dy_km):
    zs = gaussian_filter(z, 0.7)
    ny, nx = zs.shape
    rec = -np.ones(ny * nx, int)
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for i in range(ny):
        for j in range(nx):
            best, bk = 0.0, -1
            for a, b in nb:
                ii, jj = i + a, j + b
                if 0 <= ii < ny and 0 <= jj < nx:
                    s = (zs[i, j] - zs[ii, jj]) / math.hypot(a * dy_km, b * dx_km)
                    if s > best:
                        best, bk = s, ii * nx + jj
            rec[i * nx + j] = bk
    acc = np.ones(ny * nx)
    for c in np.argsort(-zs.ravel()):
        if rec[c] >= 0:
            acc[rec[c]] += acc[c]
    return acc.reshape(ny, nx) * dx_km * dy_km


def bilinear(lats, lons, f, lat, lon):
    i = np.clip(np.searchsorted(lats, lat) - 1, 0, len(lats) - 2)
    j = np.clip(np.searchsorted(lons, lon) - 1, 0, len(lons) - 2)
    ty = (lat - lats[i]) / (lats[i + 1] - lats[i])
    tx = (lon - lons[j]) / (lons[j + 1] - lons[j])
    return float((1 - ty) * (1 - tx) * f[i, j] + (1 - ty) * tx * f[i, j + 1] + ty * (1 - tx) * f[i + 1, j] + ty * tx * f[i + 1, j + 1])


def road_profiles(cache_path):
    """Perfil por carretera: muestras cada ~0,5 km, ajustado al fondo de valle (mínimo lateral ±0,4 km + 30 m) y con las
    cotas de puerto forzadas. Caché por carretera y huella de sus puntos de paso: solo se consultan las que cambian."""
    import hashlib
    cache = {}
    if cache_path and Path(cache_path).exists():
        cache = json.loads(Path(cache_path).read_text())
    out = {}
    for rid, (_, _, wps) in ROADS.items():
        sig = hashlib.sha256(json.dumps(wps).encode()).hexdigest()[:16]
        if cache.get(rid, {}).get("sig") == sig:
            out[rid] = cache[rid]
            continue
        pts, lab = [], []
        for a, b in zip(wps, wps[1:]):
            n = max(1, int(hav(a[1:], b[1:]) / 0.5))
            lab.append((len(pts), a[0]))
            pts += [(a[1] + (b[1] - a[1]) * k / n, a[2] + (b[2] - a[2]) * k / n) for k in range(n)]
        pts.append(wps[-1][1:])
        lab.append((len(pts) - 1, wps[-1][0]))
        P = np.array(pts)
        dd = np.gradient(P, axis=0)
        nrm = np.stack([-dd[:, 1] * math.cos(math.radians(42.6)), dd[:, 0] / math.cos(math.radians(42.6))], 1)
        nrm /= np.maximum(np.linalg.norm(nrm * [111.32, 82.0], axis=1)[:, None], 1e-9)
        el = np.array(elevation_api([tuple(x) for x in np.concatenate([P, P - 0.4 * nrm, P + 0.4 * nrm])]), float).reshape(3, len(P))
        el = np.minimum(el[0], el[1:].min(axis=0) + 30)
        for idx, nm in lab:
            if nm in PASSES:
                el[idx] = max(el[idx], PASSES[nm])
        out[rid] = {"sig": sig, "pts": pts, "el": el.tolist(), "labels": [(i, n) for i, n in lab if n != "·"]}
    if cache_path:
        Path(cache_path).write_text(json.dumps(out))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dem-npz", help="npz con lats, lons, z a 0,01° (si falta, se descarga)")
    ap.add_argument("--dem-origen", help="procedencia del npz (p. ej. «Copernicus GLO-90 vía API de elevación de Open-Meteo, 2026-11-24»)")
    ap.add_argument("--roads-cache", help="caché de perfiles de carretera (se lee y se reescribe)")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    lats, lons, z = load_dem(a.dem_npz)
    dx = DOMAIN["step"] * 111320 * math.cos(math.radians(42.5))
    dy = DOMAIN["step"] * 111320
    gy, gx = np.gradient(gaussian_filter(z, 2), dy, dx)
    fields, lift = [], []
    for d in DIRS:
        cw, hw = moisture(d)
        fields.append(smith_barstad(z, dx, dy, d, U_REF, cw, hw))
        th = math.radians(d)
        lift.append(gaussian_filter(-U_REF * math.sin(th) * gx - U_REF * math.cos(th) * gy, 1.5))   # m/s, >0 ascenso
    acc = d8_accumulation(z, dx / 1000, dy / 1000)
    p75 = generic_filter(z, lambda w: np.percentile(w, 75), size=(13, 15))
    cpi = np.clip(p75 - z, 0, None) / 100 * np.clip(gaussian_filter(np.log10(acc), 1.0), 0, None)
    tpi = z - uniform_filter(z, size=(7, 9))

    def sample(lat, lon):
        return {"p_oro_mmh": [round(bilinear(lats, lons, f, lat, lon), 2) for f in fields],
                "ascenso_ms": [round(bilinear(lats, lons, w, lat, lon), 2) for w in lift],
                "cpi": round(bilinear(lats, lons, cpi, lat, lon), 2), "tpi_m": round(bilinear(lats, lons, tpi, lat, lon))}

    # La escala de cubeta solo se aplica en los fondos de cuenca anchos (Cerdanya, Cerdagne, Capcir). En los valles
    # estrechos de Andorra, del Carol y del Ariège el índice crece con la profundidad del valle y sobrestima el enfriamiento.
    basin = [(lat, lon) for _, _, lat, lon, tipo, zona, _ in pirineo.POIS if tipo == "pueblo" and zona in BASIN_ZONES]
    basin += [(lat, lon) for _, _, lat, lon, tipo, zona, _, _ in EXTRA if tipo == "pueblo" and zona in BASIN_ZONES]
    pois = {}
    for pid, name, lat, lon, tipo, zona, alt in pirineo.POIS:
        pois[pid] = {"nombre": name, "lat": lat, "lon": lon, "tipo": tipo, "zona": zona, "alt_ref": alt, "fuente": "pirineo.POIS",
                     **sample(lat, lon), "cubeta_calibrable": tipo == "pueblo" and zona in BASIN_ZONES}
    for pid, name, lat, lon, tipo, zona, vert, alt in EXTRA:
        assert pid not in pois, pid
        pois[pid] = {"nombre": name, "lat": lat, "lon": lon, "tipo": tipo, "zona": zona, "vertiente": vert, "alt_ref": alt,
                     "fuente": "geocodificador Open-Meteo (GeoNames)", **sample(lat, lon),
                     "cubeta_calibrable": tipo == "pueblo" and zona in BASIN_ZONES}
    for pid, name, (lat, lon), vert, zona, base, top, estado, fuente in ESTACIONES:
        pois[pid] = {"nombre": name, "lat": lat, "lon": lon, "tipo": "estacion_esqui", "zona": zona, "vertiente": vert,
                     "base_m": base, "techo_m": top, "estado_estacion": estado, "fuente": fuente,
                     **sample(lat, lon), "cubeta_calibrable": False}
    cpi_ref = pois["das"]["cpi"]

    def in_basin(lat, lon):
        return min((hav((lat, lon), q) for q in basin), default=99) <= BASIN_KM
    roads = {}
    for rid, prof in road_profiles(a.roads_cache).items():
        name, country, _ = ROADS[rid]
        pts, el = prof["pts"], prof["el"]
        dist = [0.0]
        for p, q in zip(pts, pts[1:]):
            dist.append(dist[-1] + hav(p, q))
        roads[rid] = {"nombre": name, "pais": country, "etiquetas": [[i, n] for i, n in prof["labels"]],
                      "muestras": [{"lat": round(p[0], 4), "lon": round(p[1], 4), "km": round(d, 2), "z": round(e),
                                    **{k: v for k, v in sample(*p).items() if k != "ascenso_ms"}, "cuenca": in_basin(*p)}
                                   for p, e, d in zip(pts, el, dist)]}
    doc = {"schema": 1, "generado": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "estado": "EXPERIMENTAL",
           "fuente_dem": ("Copernicus GLO-90 vía API de elevación de Open-Meteo, muestreado en malla 0,01° (~1 km)" if not a.dem_npz
                          else f"npz local ({Path(a.dem_npz).name}; origen: {a.dem_origen or 'no declarado'}), malla 0,01° (~1 km)"),
           "dominio": DOMAIN,
           "modelo": {"nombre": "Smith y Barstad (2004), lineal", "U_ref_ms": U_REF, "Nm_s": NM, "tau_s": TAU,
                      "direcciones": DIRS, "humedad_por_sector": {str(k): {"Cw": v[0], "Hw_m": v[1]} for k, v in SECTOR_MOIST.items()},
                      "nota": "mm/h forzados solo por el relieve; comparables entre direcciones y puntos, no absolutos; sin calibrar (HIPÓTESIS)"},
           "cubeta": {"cpi_ref_das": cpi_ref, "dtmax_ref_c": 20.0,
                      "nota": "ΔTmax = 20 °C × CPI/CPI(Das), con tope en 20 °C; solo en fondos de cuenca de la Cerdanya, la Cerdagne y el Capcir (cubeta_calibrable / cuenca). Sin calibrar con observaciones (HIPÓTESIS)"},
           "puntos": pois, "carreteras": roads, "puertos": PASSES,
           "tipos": {"cima": "cumbre (geocodificada; el DEM de ~1 km rebaja las cimas)", "collado": "collado o puerto",
                     "pueblo": "núcleo", "estacion": "zona de esquí ya en pirineo.POIS",
                     "estacion_esqui": "estación de esquí: punto de referencia y rango esquiable publicado (base_m–techo_m)"}}
    Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print(f"{a.out}: {len(pois)} puntos, {len(roads)} carreteras, CPI(Das) {cpi_ref}, {Path(a.out).stat().st_size // 1024} kB")


if __name__ == "__main__":
    main()
