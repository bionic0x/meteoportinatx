"""SEPI F05: modelos de referencia, métricas y contraste (Python puro, probado en el CI).

Implementa docs/SEPI-P-PROTOCOLO.md (congelado en 1ae92c1) §5–§7, con las concreciones C1–C19 de
docs/SEPI-F05-CONCRECIONES.md. Una predicción es una distribución empírica ponderada: lista de (valor, peso).
"""
import math
import random

KS = (3, 5, 7)
WEIGHTINGS = ("uniforme", "inversa")
INNER_INITIAL = 15
B = 2000
BLOCK = 5
SEED = 20261128


# ---------- distribuciones y métricas ----------

def uniform(values):
    n = len(values)
    return [(v, 1.0 / n) for v in values]


def mean(dist):
    return sum(v * w for v, w in dist)


def crps(dist, y):
    """CRPS exacto de la distribución empírica ponderada (C10)."""
    a = sum(w * abs(v - y) for v, w in dist)
    b = sum(wi * wj * abs(vi - vj) for vi, wi in dist for vj, wj in dist)
    return a - 0.5 * b


def tercile_probs(dist, edges):
    lo, hi = edges
    p = [0.0, 0.0, 0.0]
    for v, w in dist:
        p[0 if v <= lo else (2 if v > hi else 1)] += w
    return p


def rps(probs, y, edges):
    lo, hi = edges
    k = 0 if y <= lo else (2 if y > hi else 1)
    obs = [1.0 if i == k else 0.0 for i in range(3)]
    cp, co, s = 0.0, 0.0, 0.0
    for i in range(3):
        cp += probs[i]
        co += obs[i]
        s += (cp - co) ** 2
    return s / 2


def quantile7(xs, q):
    xs = sorted(xs)
    h = (len(xs) - 1) * q
    lo = int(math.floor(h))
    return xs[lo] + (h - lo) * (xs[min(lo + 1, len(xs) - 1)] - xs[lo])


def truncate(dist, low=None, high=None):
    """Coherencia física (C9): trunca los miembros. Devuelve (dist, fracción de peso truncada)."""
    out, cut = [], 0.0
    for v, w in dist:
        nv = v
        if low is not None and nv < low:
            nv = low
        if high is not None and nv > high:
            nv = high
        if nv != v:
            cut += w
        out.append((nv, w))
    return out, cut


# ---------- modelos ----------

def ols(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        return None
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    return my - b * mx, b


def m0(train_y):
    return uniform(train_y)


def regression_model(train_x, train_y, x_test):
    """M0b (x = año) y M0c-R (x = SWE₀): ajuste + residuos del entrenamiento (C5, C6). None = sin varianza."""
    fit = ols(train_x, train_y)
    if fit is None:
        return None
    a, b = fit
    res = [yy - (a + b * xx) for xx, yy in zip(train_x, train_y)]
    pred = a + b * x_test
    return uniform([pred + r for r in res])


def zscore_params(rows):
    """Media y desviación por predictor; las columnas sin varianza se excluyen (§5)."""
    p = len(rows[0])
    out = []
    for j in range(p):
        col = [r[j] for r in rows]
        m = sum(col) / len(col)
        sd = math.sqrt(sum((c - m) ** 2 for c in col) / (len(col) - 1)) if len(col) > 1 else 0.0
        out.append((m, sd) if sd > 0 else None)
    return out


def _neighbours(train_x, train_y, x_test, params):
    """Vecinos ordenados por distancia (d, y), con los predictores sin varianza excluidos. None si no queda ninguno."""
    cols = [j for j, pr in enumerate(params) if pr is not None]
    if not cols:
        return None
    zt = [(x_test[j] - params[j][0]) / params[j][1] for j in cols]
    d = []
    for xi, yi in zip(train_x, train_y):
        d.append((math.sqrt(sum(((xi[j] - params[j][0]) / params[j][1] - zt[c]) ** 2
                                for c, j in enumerate(cols))), yi))
    d.sort(key=lambda t: t[0])
    return d


def _weights(nb, weighting):
    k = len(nb)
    if weighting == "uniforme":
        return [(y, 1.0 / k) for _, y in nb]
    zeros = [y for dd, y in nb if dd == 0]
    if zeros:
        return [(y, 1.0 / len(zeros)) for y in zeros]
    inv = [1.0 / dd for dd, _ in nb]
    s = sum(inv)
    return [(y, w / s) for (_, y), w in zip(nb, inv)]


def analog_dist(train_x, train_y, x_test, k, weighting, params):
    """Distribución de los k análogos más próximos. None si la configuración no es válida."""
    if len(train_x) < k:
        return None
    nb = _neighbours(train_x, train_y, x_test, params)
    return None if nb is None else _weights(nb[:k], weighting)


def analog_predict(seasons, xs, ys, test_season, x_test, select=True):
    """M0d-R con selección interna (C8). `seasons`, `xs` e `ys` son el entrenamiento, en orden cronológico.

    Devuelve (dist, config). Excluye del conjunto de análogos el invierno inmediatamente anterior al evaluado,
    también en los pliegues internos. Si todos los predictores carecen de varianza, devuelve M0.
    """
    def pool(target_season, upto):
        return [(x, y) for s, x, y in zip(seasons[:upto], xs[:upto], ys[:upto]) if s != target_season - 1]

    def fold(target_season, upto, xt):
        pl = pool(target_season, upto)
        pr = zscore_params([x for x, _ in pl])
        if all(p is None for p in pr):
            return None, [y for _, y in pl]
        return _neighbours([x for x, _ in pl], [y for _, y in pl], xt, pr), [y for _, y in pl]

    configs = [(k, w) for k in KS for w in WEIGHTINGS]
    best = (7, "uniforme")
    if select and len(seasons) > INNER_INITIAL:
        tot = {c: 0.0 for c in configs}
        valid = {c: True for c in configs}
        n = 0
        for t in range(INNER_INITIAL, len(seasons)):
            nb, ys_pool = fold(seasons[t], t, xs[t])
            for c in configs:
                if nb is None:
                    dist = m0(ys_pool)
                elif len(nb) < c[0]:
                    valid[c] = False
                    continue
                else:
                    dist = _weights(nb[:c[0]], c[1])
                tot[c] += crps(dist, ys[t])
            n += 1
        scores = {c: tot[c] / n for c in configs if valid[c] and n}
        if scores:
            m = min(scores.values())
            ties = [c for c in configs if c in scores and abs(scores[c] - m) <= 1e-12]
            best = sorted(ties, key=lambda c: (-c[0], WEIGHTINGS.index(c[1])))[0]
    nb, ys_pool = fold(test_season, len(seasons), x_test)
    if nb is None:
        return m0(ys_pool), "M0 (predictores sin varianza)"
    if len(nb) < best[0]:
        return None, "no válida"
    return _weights(nb[:best[0]], best[1]), f"k={best[0]},{best[1]}"


# ---------- contraste ----------

def block_indices(n, b=B, block=BLOCK, seed=SEED):
    """Índices del bootstrap circular por bloques; los mismos para todo un periodo (C13)."""
    rnd = random.Random(seed)
    out = []
    nb = math.ceil(n / block)
    for _ in range(b):
        idx = []
        for _ in range(nb):
            s = rnd.randrange(n)
            idx.extend((s + i) % n for i in range(block))
        out.append(idx[:n])
    return out


def paired_test(crps_ref, crps_mod, boot):
    """p unilateral de D̄ > 0 con el bootstrap centrado, CRPSS e IC percentil al 90 % (§7)."""
    d = [a - b for a, b in zip(crps_ref, crps_mod)]
    n = len(d)
    dbar = sum(d) / n
    cen = [x - dbar for x in d]
    ge = sum(1 for idx in boot if sum(cen[i] for i in idx) / n >= dbar)
    p = (1 + ge) / (len(boot) + 1)
    sref, smod = sum(crps_ref), sum(crps_mod)
    crpss = 1 - smod / sref if sref > 0 else None
    bs = []
    for idx in boot:
        r = sum(crps_ref[i] for i in idx)
        if r > 0:
            bs.append(1 - sum(crps_mod[i] for i in idx) / r)
    ci = (quantile7(bs, 0.05), quantile7(bs, 0.95)) if bs else (None, None)
    return {"n": n, "d_media": dbar, "p": p, "crpss": crpss, "ic90_inf": ci[0], "ic90_sup": ci[1]}


def holm(pvals):
    """p ajustados de Holm (monótonos), en el orden de entrada."""
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    adj = [0.0] * m
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * pvals[i]))
        adj[i] = run
    return adj


def classify(p_holm, crpss, ic90_sup, stable, components_ok):
    """Estado de aceptación (§7, C14, C15)."""
    if p_holm is None or crpss is None:
        return "UNKNOWN", "datos insuficientes"
    if p_holm < 0.05 and crpss > 0 and stable:
        if components_ok:
            return "PASS-R", "criterios 1–3"
        return "UNKNOWN", "habilidad del balance neto sin habilidad demostrada en sus componentes"
    if ic90_sup is not None and ic90_sup < 0.05:
        return "REJECT", "cota superior del IC90 del CRPSS < 0,05"
    if p_holm < 0.05 and crpss > 0 and not stable:
        return "UNKNOWN", "signo distinto antes y después de 2002"
    return "UNKNOWN", "evidencia insuficiente"


def spearman(a, b):
    def rank(x):
        o = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
                j += 1
            for t in range(i, j + 1):
                r[o[t]] = (i + j) / 2 + 1
            i = j + 1
        return r
    if len(a) < 3:
        return None
    ra, rb = rank(a), rank(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else None
