"""SEPI-GEO-01: núcleo de los derivados topográficos, en Python puro y probado en el CI con superficies sintéticas.

Contiene los algoritmos de referencia. `build_terrain_derivatives.py` usa versiones vectorizadas (numpy/scipy),
y `verify_terrain.py` comprueba que coinciden con estas sobre ventanas del DEM real.

Convenciones:
- Una rejilla es una lista de filas `z[i][j]`, con la fila 0 al NORTE, en metros, con celdas cuadradas de lado `dx`.
- NODATA es `None` y **nunca se sustituye por cero**: un derivado que lo necesite devuelve `None`.
- Los azimuts son grados desde el norte en sentido horario. El viento se da como dirección DE PROCEDENCIA.
"""
import math

NB8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _ok(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def slope_aspect(z, dx, i, j):
    """Pendiente (grados) y orientación (azimut hacia el que mira la ladera) por el método de Horn (3×3).

    Devuelve (None, None) si falta algún vecino. En terreno llano la orientación es None.
    """
    if not (0 < i < len(z) - 1 and 0 < j < len(z[0]) - 1):
        return None, None
    w = [[z[i + a][j + b] for b in (-1, 0, 1)] for a in (-1, 0, 1)]
    if not all(_ok(v) for row in w for v in row):
        return None, None
    dzdx = ((w[0][2] + 2 * w[1][2] + w[2][2]) - (w[0][0] + 2 * w[1][0] + w[2][0])) / (8 * dx)   # hacia el este
    dzdy = ((w[0][0] + 2 * w[0][1] + w[0][2]) - (w[2][0] + 2 * w[2][1] + w[2][2])) / (8 * dx)   # hacia el norte
    slope = math.degrees(math.atan(math.hypot(dzdx, dzdy)))
    if dzdx == 0 and dzdy == 0:
        return slope, None
    return slope, math.degrees(math.atan2(-dzdx, -dzdy)) % 360   # dirección de máxima bajada


def tpi(z, i, j, r):
    """Índice de posición topográfica: z − media de la ventana cuadrada de semilado `r` celdas (sin NODATA)."""
    if not _ok(z[i][j]):
        return None
    vals = [z[a][b] for a in range(max(0, i - r), min(len(z), i + r + 1))
            for b in range(max(0, j - r), min(len(z[0]), j + r + 1)) if _ok(z[a][b])]
    return z[i][j] - sum(vals) / len(vals)


def d8_accumulation(z, dx):
    """Área drenada (m²) por D8: cada celda vierte al vecino de mayor pendiente descendente. NODATA no drena."""
    ny, nx = len(z), len(z[0])
    rec = {}
    for i in range(ny):
        for j in range(nx):
            if not _ok(z[i][j]):
                continue
            best, bk = 0.0, None
            for a, b in NB8:
                ii, jj = i + a, j + b
                if 0 <= ii < ny and 0 <= jj < nx and _ok(z[ii][jj]):
                    s = (z[i][j] - z[ii][jj]) / (dx * math.hypot(a, b))
                    if s > best:
                        best, bk = s, (ii, jj)
            rec[(i, j)] = bk
    acc = {c: 1.0 for c in rec}
    for c in sorted(rec, key=lambda c: -z[c[0]][c[1]]):
        if rec[c] is not None:
            acc[rec[c]] += acc[c]
    return [[acc[(i, j)] * dx * dx if (i, j) in acc else None for j in range(nx)] for i in range(ny)]


def cold_pool_index(z_point, p75_surroundings, acc_km2):
    """Índice de cubeta fría (potencial geomorfológico, no predicción de inversión): hundimiento sobre el P75 del
    entorno (hm) × log10 del área drenada (km²), ambos ≥ 0. Misma forma que build_orografia_pirineo.py."""
    if not (_ok(z_point) and _ok(p75_surroundings) and _ok(acc_km2)) or acc_km2 <= 0:
        return None
    return max(p75_surroundings - z_point, 0.0) / 100 * max(math.log10(acc_km2), 0.0)


def ray(sampler, x0, y0, azimuth, max_dist, step):
    """Muestras (distancia, z) a lo largo de un rayo. `sampler(x, y)` devuelve z en metros o None (x al este, y al norte)."""
    a = math.radians(azimuth)
    out = []
    d = step
    while d <= max_dist + 1e-9:
        out.append((d, sampler(x0 + d * math.sin(a), y0 + d * math.cos(a))))
        d += step
    return out


def horizon_angle(sampler, x0, y0, z0, azimuth, max_dist, step):
    """Ángulo del horizonte (grados, ≥ 0) en un azimut. None si una muestra es NODATA antes de alcanzar max_dist."""
    best = 0.0
    for d, z in ray(sampler, x0, y0, azimuth, max_dist, step):
        if not _ok(z):
            return None
        best = max(best, math.degrees(math.atan2(z - z0, d)))
    return best


def sky_view_factor(sampler, x0, y0, z0, n_az=32, max_dist=10000.0, step=30.0):
    """Factor de vista del cielo isótropo: media de cos²(horizonte) en `n_az` azimuts (1 = cielo libre)."""
    hs = [horizon_angle(sampler, x0, y0, z0, k * 360.0 / n_az, max_dist, step) for k in range(n_az)]
    if any(h is None for h in hs):
        return None
    return sum(math.cos(math.radians(h)) ** 2 for h in hs) / n_az


def directional_exposure(sampler, x0, y0, z0, wind_from, max_dist=20000.0, step=90.0):
    """Exposición orográfica hacia la procedencia del flujo `wind_from` (grados).

    Devuelve un dict con:
    - barrera_m: altura del obstáculo más alto a barlovento sobre el punto (≥ 0);
    - dist_barrera_m: distancia a ese obstáculo;
    - angulo_abrigo_grados: elevación angular máxima a barlovento (≥ 0);
    - pendiente_barlovento: desnivel medio por unidad de distancia hacia el punto (positivo = el terreno sube hacia el punto).

    Es la base estática de la interacción flujo–orografía (GEO-07). No es una predicción.
    """
    samples = ray(sampler, x0, y0, wind_from, max_dist, step)
    if any(not _ok(z) for _, z in samples):
        return None
    zmax_d, zmax = max(samples, key=lambda s: s[1])
    shelter = max(max(math.degrees(math.atan2(z - z0, d)) for d, z in samples), 0.0)
    far_d, far_z = samples[-1]
    return {"barrera_m": max(zmax - z0, 0.0), "dist_barrera_m": zmax_d if zmax > z0 else None,
            "angulo_abrigo_grados": shelter, "pendiente_barlovento": (z0 - far_z) / far_d}


def froude(U, N, h):
    """Número de Froude de la montaña Fr = U/(N·h). Fr < 1 favorece el bloqueo o rodeo; Fr > 1, el paso por encima.

    Herramienta del módulo GEO-07; los umbrales prácticos son HIPÓTESIS hasta validarlos con observaciones.
    """
    if not (_ok(U) and _ok(N) and _ok(h)) or N <= 0 or h <= 0:
        return None
    return U / (N * h)


def bilinear(z, fi, fj):
    """Valor bilineal en coordenadas fraccionarias de fila y columna. None si algún vértice es NODATA."""
    i, j = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i < len(z) - 1 and 0 <= j < len(z[0]) - 1):
        return None
    c = [z[i][j], z[i][j + 1], z[i + 1][j], z[i + 1][j + 1]]
    if not all(_ok(v) for v in c):
        return None
    ty, tx = fi - i, fj - j
    return (1 - ty) * (1 - tx) * c[0] + (1 - ty) * tx * c[1] + ty * (1 - tx) * c[2] + ty * tx * c[3]


def max_within(z, fi, fj, radius_cells):
    """Máximo en un radio (celdas) alrededor de una posición fraccionaria. Sirve para diagnosticar errores de
    geolocalización y suavizado; no sustituye la altitud del punto."""
    ci, cj = round(fi), round(fj)
    r = int(math.ceil(radius_cells))
    vals = [z[a][b] for a in range(ci - r, ci + r + 1) for b in range(cj - r, cj + r + 1)
            if 0 <= a < len(z) and 0 <= b < len(z[0]) and math.hypot(a - fi, b - fj) <= radius_cells and _ok(z[a][b])]
    return max(vals) if vals else None


def _rank(xs):
    order = sorted(range(len(xs)), key=lambda k: xs[k])
    r = [0.0] * len(xs)
    k = 0
    while k < len(order):
        m = k
        while m + 1 < len(order) and xs[order[m + 1]] == xs[order[k]]:
            m += 1
        for t in range(k, m + 1):
            r[order[t]] = (k + m) / 2 + 1
        k = m + 1
    return r


def spearman(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if _ok(x) and _ok(y)]
    if len(pairs) < 3:
        return None
    ra, rb = _rank([p[0] for p in pairs]), _rank([p[1] for p in pairs])
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return cov / (va * vb) if va and vb else None


def change_stats(ref, new):
    """Sesgo, MAE, RMSE, mediana, P95 y máximo de |Δ| y Spearman entre dos variantes (pares sin NODATA)."""
    d = [y - x for x, y in zip(ref, new) if _ok(x) and _ok(y)]
    if not d:
        return {"n": 0}
    ad = sorted(abs(v) for v in d)

    def q(p):
        h = (len(ad) - 1) * p
        lo = int(math.floor(h))
        return ad[lo] + (h - lo) * (ad[min(lo + 1, len(ad) - 1)] - ad[lo])
    return {"n": len(d), "sesgo": sum(d) / len(d), "mae": sum(ad) / len(ad),
            "rmse": math.sqrt(sum(v * v for v in d) / len(d)), "mediana_abs": q(0.5), "p95_abs": q(0.95),
            "max_abs": ad[-1], "spearman": spearman(ref, new)}
