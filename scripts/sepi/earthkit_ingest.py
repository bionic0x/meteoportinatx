"""Adquisición estacional opcional de SEPI (CDS, SEAS5); sin acceso a la red salvo con --download."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATASET = "seasonal-monthly-single-levels"
VARIABLES = ("2m_temperature", "total_precipitation", "mean_sea_level_pressure")


def requests(year, system):
    """Inicio el 1 de noviembre; los plazos 2 y 3 son diciembre y enero."""
    for variable in VARIABLES:
        yield {
            "originating_centre": "ecmwf",
            "system": system,
            "variable": variable,
            "product_type": "monthly_mean",
            "year": str(year),
            "month": "11",
            "leadtime_month": ["2", "3"],
            "data_format": "grib",
        }


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def data_root():
    if not os.environ.get("SEPI_DATA"):
        raise ValueError("Define SEPI_DATA fuera del repositorio")
    root = Path(os.environ["SEPI_DATA"]).resolve()
    repo = Path(__file__).resolve().parents[2]
    if root == repo or repo in root.parents:
        raise ValueError("SEPI_DATA debe estar fuera del repositorio")
    return root / "cds" / "seasonal"


def retrieve(request, root):
    import cdsapi

    key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    root.mkdir(parents=True, exist_ok=True)
    target = root / (key + ".grib")
    manifest = root / (key + ".json")
    if target.exists() or manifest.exists():
        if target.exists() and manifest.exists():
            prior = json.loads(manifest.read_text())
            if prior["sha256"] == digest(target) and prior["request"] == request:
                return
        raise RuntimeError("Artefacto en caché incompleto o incoherente: " + key)
    temporary = target.with_suffix(".part")
    if temporary.exists():
        raise RuntimeError("Revisa y elimina la descarga incompleta: " + str(temporary))
    cdsapi.Client().retrieve(DATASET, request, str(temporary))
    with temporary.open("rb") as stream:
        if stream.read(4) != b"GRIB":
            raise ValueError("Se esperaba un archivo GRIB")
    target_hash = digest(temporary)
    temporary.rename(target)
    manifest.write_text(json.dumps({
        "dataset": DATASET, "request": request, "sha256": target_hash,
        "bytes": target.stat().st_size,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
    }, indent=2) + "\n")


def inspect(path):
    import earthkit.data as ekd

    ds = ekd.from_source("file", str(path)).to_xarray()
    print(ds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", required=True, help="Sistema del CDS comprobado para los años elegidos")
    parser.add_argument("--years", nargs="+", type=int, required=True, help="Años de inicio (noviembre)")
    parser.add_argument("--download", action="store_true", help="Descargar de verdad (por defecto solo muestra las peticiones)")
    parser.add_argument("--inspect", type=Path, help="Inspeccionar un GRIB descargado con earthkit")
    args = parser.parse_args()
    if args.inspect:
        inspect(args.inspect)
        return
    for year in sorted(set(args.years)):
        for request in requests(year, args.system):
            if args.download:
                retrieve(request, data_root())
            else:
                print(json.dumps({"dataset": DATASET, "request": request}))


if __name__ == "__main__":
    main()
