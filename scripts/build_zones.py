"""Stage shared zone reports/downloads using real providers, before Pages upload.

Requires a fresh build_site target. Never imports local observations or archives.
Acquisition is staged separately; failed forecasts leave the existing target intact.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from zone_engine import BUILTINS,load_profile,collect,fetch_json
from zone_report import render_report
from zone_packages import read_pack,analysis


def stage_zones(target,*,getter=fetch_json,application=None):
    target=Path(target)
    if not (target/'index.html').is_file():
        raise ValueError('build the base site first')
    if (target/'zones').exists() or (target/'downloads').exists():
        raise ValueError('requires a fresh base site; refusing to overwrite regional outputs')
    application=Path(application or ROOT/'dist/MeteoPortinatx.pyz')
    if not application.is_file():
        raise ValueError('build the portable application first')
    with tempfile.TemporaryDirectory(prefix='regional-site-',dir=target.parent) as td:
        staging=Path(td);zones=staging/'zones';downloads=staging/'downloads'
        zones.mkdir();downloads.mkdir()
        summary={}
        for name in BUILTINS:
            profile=load_profile(name);folder=zones/name;folder.mkdir()
            pack=folder/'zone.zip'
            manifest=collect(profile,pack,getter=getter)
            parsed=read_pack(pack);computed=analysis(parsed)
            # A useful regional forecast is required for every configured point.
            # Missing complementary feeds remain explicitly unknown in the report.
            for point in profile['points']:
                days=computed[point['id']].get('forecast',{})
                if not any(row['values'].get('temperature_2m') is not None for row in days.values()):
                    entry=next(e for e in manifest['entries'] if e['point']==point['id'] and e['module']=='forecast')
                    detail={k:entry.get(k) for k in ('status','error','http_status','network_reason','coverage')}
                    raise ValueError(name+': no complete daily temperature forecast for '+point['id']+'; '+json.dumps(detail))
            document=render_report(pack)
            navigation='<nav><a href="../../">Observatorios</a> · <a href="zone.zip" download>Descargar datos de esta zona</a> · <a href="zone.json" download>Perfil editable</a> · <a href="../../downloads/">Modelar mi zona</a></nav>'
            (folder/'index.html').write_text(document.replace('<main>','<main>'+navigation,1),encoding='utf-8')
            (folder/'zone.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
            summary[name]={'status':manifest['status'],'created_at':manifest['created_at'],'sha256':parsed['sha256']}
        shutil.copyfile(application,downloads/'MeteoPortinatx.pyz')
        shutil.copyfile(ROOT/'docs/ZONAS-MODULARES.md',downloads/'guia.md')
        shutil.copyfile(ROOT/'docs/FORECAST-LEDGER-P0.md',downloads/'FORECAST-LEDGER-P0.md')
        (downloads/'index.html').write_text('''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Modelar mi zona · MeteoPortinatx</title><style>body{font:17px/1.6 system-ui;max-width:850px;margin:32px auto;padding:16px;color:#172b3a;background:#f4f7f8}pre{overflow:auto;background:white;padding:16px}a{color:#075c83}</style></head><body>
<a href="../">Observatorios</a><h1>Modelar mi zona</h1><p>Descarga el motor común y selecciona únicamente los datos que necesitas. Requiere Python 3.10 o posterior; sin bibliotecas externas. Las descargas de datos necesitan conexión y respetar las condiciones de cada proveedor.</p>
<p><a href="MeteoPortinatx.pyz" download>Descargar MeteoPortinatx.pyz</a> · <a href="guia.md">Guía completa y flujo forense</a></p><p>Plantillas: <a href="../zones/portinatx/zone.json" download>Portinatx</a> · <a href="../zones/pirineo/zone.json" download>Pirineo (sin mar)</a></p>
<pre>python3 MeteoPortinatx.pyz zone init --id mi_zona --name 'Mi zona' --latitude 42.35 --longitude 1.9 --setting inland --modules forecast,ensemble,terrain --output mi-zona.json
python3 MeteoPortinatx.pyz zone fetch mi-zona.json --output mi-zona.zip
python3 MeteoPortinatx.pyz zone report --pack mi-zona.zip --output mi-zona.html</pre>
<p>Para radar, añade <code>radar</code> a los módulos. Para avisos y observaciones, configura países, áreas y estaciones en el perfil según la guía. Los perfiles interiores excluyen el mar. Un módulo descargado puede contener huecos o datos antiguos: consulta cobertura y fechas.</p><p>Los informes HTML y los paquetes se consultan sin conexión. La evaluación forense se ejecuta localmente con pronósticos archivados antes del episodio y medidas revisadas; no sube tus observaciones a esta web.</p></body></html>''',encoding='utf-8')
        (zones/'manifest.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        # Everything has passed before any regional content reaches the upload tree.
        zones.replace(target/'zones')
        try:
            downloads.replace(target/'downloads')
        except BaseException:
            shutil.rmtree(target/'zones')
            raise
        index=target/'index.html'
        index.write_text(index.read_text(encoding='utf-8').replace('id="shared-zones" hidden','id="shared-zones"'),encoding='utf-8')
        return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=ROOT/'site')
    args=parser.parse_args()
    try:
        print(json.dumps(stage_zones(args.target),indent=2))
    except (ValueError,OSError,TypeError) as exc:
        # GitHub's public run view exposes annotations even when logs require login.
        message=str(exc).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print('::error title=Regional acquisition failed::'+message,flush=True)
        raise SystemExit(1)
