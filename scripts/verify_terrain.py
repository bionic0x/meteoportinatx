#!/usr/bin/env python3
"""SEPI-GEO-01: comprobaciones de coherencia de los derivados. No sustituye a la verificación independiente.

1. SHA-256 de las teselas frente a sus manifiestos.
2. Pendiente y orientación de Horn vectorizadas frente a geo_terrain_core.slope_aspect, en celdas aleatorias del DEM real.
3. TPI vectorizado frente a geo_terrain_core.tpi.
4. D8 con numba frente a geo_terrain_core.d8_accumulation, en una subventana real de 40×40.
5. NODATA: ninguna celda del núcleo es NaN y ninguna se ha rellenado con 0.
6. Costuras: salto de altitud a través de las juntas entre teselas frente al salto típico entre píxeles vecinos.
Escribe SEPI_DATA/terrain/geo01/verify_report.json y sale con código 1 si algo falla.
"""
import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import rasterio

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import build_terrain_derivatives as bt  # noqa: E402
import geo_terrain_core as gt  # noqa: E402

TERRAIN = Path(os.environ["SEPI_DATA"]).resolve() / "terrain"
DERIVED = TERRAIN / "derived"


def main():
    rnd = random.Random(20261128)
    report, ok = {}, True

    bad = []
    for folder in ("copernicus-glo30", "copernicus-glo90"):
        man = json.loads((TERRAIN / folder / "manifest.json").read_text())
        for t in man["teselas"]:
            if bt.sha256(TERRAIN / folder / t["archivo"]) != t["sha256"]:
                bad.append(t["archivo"])
    report["sha256_teselas"] = {"fallos": bad}
    ok &= not bad

    for name in ("V1", "V3"):
        with rasterio.open(DERIVED / f"{name}_z.tif") as d:
            z = d.read(1).astype(float)
            dx = d.transform.a
        slope, aspect = bt.horn(z, dx)
        tpi = z - bt.box_mean(z, 5, 5)
        ds, da, dt = 0.0, 0.0, 0.0
        for _ in range(300):
            i, j = rnd.randrange(10, z.shape[0] - 10), rnd.randrange(10, z.shape[1] - 10)
            w = z[i - 6:i + 7, j - 6:j + 7].tolist()
            s, a = gt.slope_aspect(w, dx, 6, 6)
            ds = max(ds, abs(s - slope[i, j]))
            if a is not None:
                da = max(da, abs((a - aspect[i, j] + 180) % 360 - 180))
            dt = max(dt, abs(gt.tpi(w, 6, 6, 5) - tpi[i, j]))
        acc_ok = True
        i0, j0 = z.shape[0] // 2, z.shape[1] // 2
        sub = z[i0:i0 + 40, j0:j0 + 40]
        ref = np.array(gt.d8_accumulation(sub.tolist(), dx), float)
        acc_ok = bool(np.allclose(bt.d8_accumulation_nb(sub.copy(), dx), ref))
        inner = z[int(bt.BUFFER_M / dx):-int(bt.BUFFER_M / dx), int(bt.BUFFER_M / dx):-int(bt.BUFFER_M / dx)]
        report[name] = {"max_dif_pendiente_grados": ds, "max_dif_orientacion_grados": da, "max_dif_tpi_m": dt,
                        "d8_igual_que_referencia": acc_ok, "nodata_nucleo": int(np.isnan(inner).sum()),
                        "celdas_cero_nucleo": int((inner == 0).sum()), "z_min_nucleo": float(np.nanmin(inner))}
        ok &= ds < 1e-6 and da < 1e-6 and dt < 1e-6 and acc_ok and report[name]["nodata_nucleo"] == 0 \
            and report[name]["celdas_cero_nucleo"] == 0

    # Costuras en la rejilla original EPSG:4326 (GLO-30): las juntas están en grados enteros.
    z30g, tr, _, _ = bt.mosaic_4326("copernicus-glo30", (0.5, 41.9, 3.0, 43.3))
    inv = ~tr
    seams = {}
    for lon in (1.0, 2.0):
        c = int(round((inv * (lon, 42.5))[0]))
        jump = np.nanmedian(np.abs(z30g[:, c] - z30g[:, c - 1]))
        typical = np.nanmedian(np.abs(z30g[:, c - 50] - z30g[:, c - 51]))
        seams[f"lon_{lon}"] = {"salto_mediano_m": float(jump), "salto_tipico_m": float(typical)}
    for lat in (42.0, 43.0):
        r = int(round((inv * (1.5, lat))[1]))
        jump = np.nanmedian(np.abs(z30g[r, :] - z30g[r - 1, :]))
        typical = np.nanmedian(np.abs(z30g[r - 50, :] - z30g[r - 51, :]))
        seams[f"lat_{lat}"] = {"salto_mediano_m": float(jump), "salto_tipico_m": float(typical)}
    report["costuras_glo30"] = seams
    ok &= all(v["salto_mediano_m"] <= 3 * max(v["salto_tipico_m"], 1.0) for v in seams.values())

    report["resultado"] = "OK" if ok else "FALLO"
    (TERRAIN / "geo01" / "verify_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
