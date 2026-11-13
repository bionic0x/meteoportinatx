"""One offline, escaped HTML report for every regional profile."""
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from zone_packages import read_pack, analysis

LABELS = {'atmosphere':'Atmósfera', 'forecast':'Previsión', 'ensemble':'Ensembles', 'terrain':'Elevación', 'marine':'Mar', 'radar':'Radar', 'warnings':'Avisos oficiales', 'observations':'Observaciones'}


def text(value):
    return escape(str(value), quote=True)


def point_name(pid):
    return text(pid.replace('_', ' ').title())


def stamp(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')


def value(x, unit=None):
    if x is None:
        return '<span class="missing">Sin datos suficientes</span>'
    suffix = text(unit) if unit else 'unidad no verificada'
    return f'{x:.2f} {suffix}'


def source_sections(pack, pid):
    rows = []
    modules = pack['profile']['modules']
    if 'observations' in modules:
        rows.append('<h3>Observaciones cercanas · METAR</h3><p>Hasta 100 km del punto. La altitud y exposición pueden diferir; no sustituyen una estación local. Frescura calculada en la captura.</p>')
        obs = pack['data'].get((pid,'observations'),{}).get('records',[])
        if not obs:
            rows.append('<p class="missing">Sin observaciones utilizables.</p>')
        for r in obs:
            rows.append(f'<p><b>{text(r["station"])}</b> · {text(stamp(r["observed_at"]))} · {r["distance_km"]:.1f} km · {text(r["freshness"])}<br>Temperatura {value(r.get("temperature_c"),"°C")} · viento {value(r.get("wind_kmh"),"km/h")} · racha {value(r.get("gust_kmh"),"km/h")}</p>')
    if 'warnings' in modules:
        rows.append('<h3>Avisos oficiales · Meteoalarm</h3><p>Selección por nombres de áreas del perfil, no por polígonos. Sin coincidencias no equivale a ausencia de avisos. Consulte el organismo emisor.</p>')
        data=pack['data'].get((pid,'warnings'),{})
        if not data:
            rows.append('<p class="missing">Fuente de avisos no disponible.</p>')
        for feed in data.get('feeds',[]):
            rows.append(f'<p>{text(feed["country"])} · estado del boletín en la captura: {text(feed["feed_state"])} · actualizado {text(feed["feed_updated"])} · áreas: {text(", ".join(feed["areas"]))}</p>')
        if data.get('failed_feeds'):
            rows.append(f'<p class="missing">Cobertura parcial: fallaron {text(", ".join(data["failed_feeds"]))}.</p>')
        for r in data.get('records',[]):
            rows.append(f'<p><b>{text(r["event"])}</b> · {text(r["area"])} · severidad {text(r["severity"])} · certeza {text(r["certainty"])}<br>{text(stamp(r["onset"]))} — {text(stamp(r["expires"]))}</p>')
        if data and not data.get('records'):
            rows.append('<p>No se encontraron coincidencias en los boletines descargados.</p>')
    if 'radar' in modules:
        rows.append('<h3>Radar · RainViewer</h3><p>Composiciones disponibles al descargar; la cruz marca el punto. La hora es la del fotograma compuesto, no garantiza la hora de cada radar que lo integra. Su antigüedad tampoco demuestra que la cobertura local sea reciente. Una imagen vacía o transparente no demuestra ausencia de lluvia. Sin estimación local calibrada de intensidad. Datos: <a href="https://www.rainviewer.com/">RainViewer</a>.</p><div class="frames">')
        frames=pack['data'].get((pid,'radar'),{}).get('frames',[])
        for f in frames:
            x,y=f['point_pixel']
            rows.append(f'<figure><div class="tile"><img width="256" height="256" alt="Tesela del radar; punto señalado con una cruz" src="data:image/png;base64,{f["png_base64"]}"><span aria-hidden="true" style="left:{x/256*100:.3f}%;top:{y/256*100:.3f}%">+</span></div><figcaption>Fotograma: {text(stamp(f["observed_at"]))}<br>Antigüedad del fotograma: {text(f["freshness"])} en la captura</figcaption></figure>')
        if not frames:
            rows.append('<p class="missing">Sin imágenes de radar utilizables.</p>')
        rows.append('</div>')
    return ''.join(rows)


def atmosphere_section(data):
    rows=['<h3>Atmósfera · perfil modelizado</h3><p>Mismo cálculo en Portinatx, Pirineo y zonas personalizadas. Los niveles bajo terreno, sin unidades o sin presión/elevación verificables quedan sin diagnóstico. No son mediciones ni probabilidades de impacto calibradas.</p>']
    if not data or not data.get('time'):
        return ''.join(rows)+'<p class="missing">Perfil atmosférico no disponible.</p>'
    rows.append(f'<p>Elevación de la celda del modelo: {value(data.get("elevacion_m"),"m")}. El perfil puede representar una altitud distinta a la del lugar real.</p>')
    location=data.get('ubicacion') or {}
    if location.get('lat') is not None and location.get('lon') is not None:
        rows.append(f'<p>Celda del modelo: {text(location["lat"])}, {text(location["lon"])}.</p>')
    columns=[('cape','CAPE','J/kg'),('ki','Índice K','°C'),('tw2m','Bulbo húmedo superficial','°C'),('wbz','Nivel de bulbo húmedo 0 °C','m'),('shr06','Cizalladura superficie–500 hPa','m/s'),('w700','Velocidad vertical 700 hPa','m/s')]
    rows.append('<div class="table"><table><caption>Horas UTC · cizalladura entre superficie y nivel de presión, no una capa fija de 6 km</caption><thead><tr><th>Hora UTC</th>'+''.join('<th>'+label+'</th>' for _,label,_ in columns)+'</tr></thead><tbody>')
    for i,t in enumerate(data['time']):
        cells=[]
        for key,_,unit in columns:
            values=data.get('indices',{}).get(key,[])
            cells.append('<td>'+value(values[i] if i<len(values) else None,unit)+'</td>')
        rows.append('<tr><th scope="row">'+text(t)+'</th>'+''.join(cells)+'</tr>')
    rows.append('</tbody></table></div><p>La altura de bulbo húmedo cero se refiere al nivel del mar; las alturas de cizalladura del paquete son sobre el terreno del modelo. No se convierten Pa/s en m/s cambiando el signo. Sin una convención verificada del proveedor no se interpreta el signo como ascenso. Los índices compuestos requieren todos sus componentes y las convenciones verificadas.</p>')
    return ''.join(rows)


def render_report(path):
    pack = read_pack(path)
    profile, manifest = pack['profile'], pack['manifest']
    computed = analysis(pack)
    entries = {(e['point'],e['module']):e for e in manifest['entries']}
    blocks = []
    for point in profile['points']:
        pid = point['id']
        rows = [f'<section class="point" data-point="{text(pid)}"><h2>{point_name(pid)}</h2><p>{point["latitude"]:.4f}, {point["longitude"]:.4f}</p>']
        rows.append('<h3>Fuentes y cobertura</h3><ul>')
        for module in profile['modules']:
            entry = entries[(pid,module)]
            state = 'Descargado' if entry['status'] == 'AVAILABLE' else 'No disponible'
            coverage = ''
            payload = pack['data'].get((pid,module))
            if payload and 'hourly' in payload:
                from weather_core import number
                arrays = [v for k,v in payload['hourly'].items() if k != 'time']
                total = sum(len(v) for v in arrays)
                valid = sum(number(x) for v in arrays for x in v)
                coverage = f' · valores presentes {valid}/{total} (consultar cobertura por variable)'
            rows.append(f'<li><b>{LABELS[module]}</b>: {state}{coverage} · consulta {text(stamp(entry["retrieved_at"]))} · <a rel="noreferrer" href="{text(entry["url"])}">Fuente</a></li>')
            if payload and module == 'terrain':
                rows.append(f'<li>Elevación puntual: {value(payload["elevation"][0],"m")}; no representa un DEM regional.</li>')
        rows.append('</ul>')
        daily = computed[pid].get('forecast', {})
        if 'forecast' in profile['modules']:
            rows.append('<h3>Previsión diaria · UTC</h3><div class="table"><table><caption>Totales y extremos; los huecos no cuentan como cero</caption><thead><tr><th>Día</th><th>Lluvia total</th><th>Nieve nueva</th><th>Racha máxima</th><th>Temperatura mínima</th><th>Bulbo húmedo mínimo</th></tr></thead><tbody>')
            for day, row in sorted(daily.items()):
                cells = []
                for field in ('precipitation','snowfall','wind_gusts_10m','temperature_2m','wet_bulb_min_c'):
                    coverage_key = 'wet_bulb' if field == 'wet_bulb_min_c' else field
                    unit = '°C' if field == 'wet_bulb_min_c' else row['units'].get(field)
                    count = row['coverage'][coverage_key]['valid']
                    cells.append(f'<td>{value(row["values"][field],unit)}<small>{count}/24 horas</small></td>')
                rows.append(f'<tr><th scope="row">{text(day)}</th>{"".join(cells)}</tr>')
            rows.append('</tbody></table></div>')
            if not daily:
                rows.append('<p class="missing">No hay previsión disponible.</p>')
        if 'ensemble' in profile['modules']:
            rows.append('<h3>Escenarios por familias</h3><p>Fracciones de miembros sin calibrar, no probabilidades verificadas. Cada familia institucional pesa lo mismo cuando aporta datos suficientes.</p>')
            ens = computed[pid].get('ensemble', {})
            rows.append('<div class="table"><table><thead><tr><th>Día</th><th>Evento</th><th>Fracción</th><th>Familias con datos</th><th>Miembros válidos / presentes</th></tr></thead><tbody>')
            for day,row in sorted(ens.items()):
                for metric,title in [('rain_ge10','Lluvia ≥10 mm'),('snow_ge5','Nieve ≥5 cm')]:
                    m = row['metrics'][metric]
                    fraction = f'{m["fraction"]*100:.1f}%' if m['fraction'] is not None else 'Sin datos suficientes'
                    counts = '; '.join(f'{f}: {r["members_valid"]}/{r["members_present"]}' for f,r in m['families'].items())
                    rows.append(f'<tr><th scope="row">{text(day)}</th><td>{title}</td><td>{fraction}</td><td>{m["n_families"]}</td><td>{text(counts)}</td></tr>')
            rows.append('</tbody></table></div>')
            if not ens:
                rows.append('<p class="missing">No hay ensemble disponible.</p>')
        if 'marine' in profile['modules']:
            rows.append('<h3>Mar</h3><p>Predicción puntual; no estima rebase, rompiente ni seguridad de navegación.</p><div class="table"><table><thead><tr><th>Día</th><th>Altura máxima</th><th>Periodo máximo</th><th>Dirección media circular</th></tr></thead><tbody>')
            marine = computed[pid].get('marine',{})
            for day,row in sorted(marine.items()):
                cells = ''.join(f'<td>{value(row["values"][field],row["units"].get(field))}</td>' for field in ('wave_height','wave_period','wave_direction'))
                rows.append(f'<tr><th scope="row">{text(day)}</th>{cells}</tr>')
            rows.append('</tbody></table></div>')
            if not marine:
                rows.append('<p class="missing">No hay datos marinos disponibles.</p>')
        if 'atmosphere' in profile['modules']:
            rows.append(atmosphere_section(computed[pid].get('atmosphere')))
        rows.append(source_sections(pack,pid))
        rows.append('</section>')
        blocks.append(''.join(rows))
    options = ''.join(f'<option value="{text(p["id"])}">{point_name(p["id"])}</option>' for p in profile['points'])
    generated = datetime.now(timezone.utc).isoformat()
    state = {'AVAILABLE':'Paquete descargado','PARTIAL':'Paquete parcial','UNKNOWN':'Fuentes no disponibles'}[manifest['status']]
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{text(profile['name'])} · Observatorio de zona</title>
<style>
:root{{font-family:system-ui,sans-serif;color:#172b3a;background:#f4f7f8}}body{{margin:0}}main{{max-width:1200px;margin:auto;padding:24px}}header,section{{background:white;border:1px solid #d2dce2;border-radius:12px;padding:24px;margin:0 0 20px}}h1{{margin:.3em 0}}h2{{color:#145166}}p,li{{line-height:1.6}}.eyebrow{{font-weight:650;color:#145166}}.notice{{border-left:4px solid #ab6500;padding:10px 16px;background:#fff6e5}}select{{font:inherit;padding:10px;max-width:100%;margin-bottom:20px}}table{{border-collapse:collapse;width:100%;font-size:.95rem}}th,td{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #d2dce2}}caption{{text-align:left;padding:10px 0}}.table{{overflow-x:auto}}.frames{{display:flex;flex-wrap:wrap;gap:16px}}figure{{margin:0;max-width:100%}}.tile{{position:relative;width:256px;max-width:100%;background:#d2dce2}}.tile img{{display:block;width:100%;height:auto}}.tile span{{position:absolute;transform:translate(-50%,-50%);font-weight:bold;color:#000;background:white;line-height:1}}figcaption{{font-size:.85rem}}small{{display:block;color:#4e5e67;margin-top:5px}}.missing{{color:#7a4900}}a{{color:#075c83}}code{{overflow-wrap:anywhere}}[hidden]{{display:none}}@media(max-width:600px){{main{{padding:10px}}header,section{{padding:16px}}th,td{{padding:8px}}}}@media print{{select,label{{display:none}}.point[hidden]{{display:block}}}}
</style></head><body><main>
<header><p class="eyebrow">MeteoPortinatx · Observatorio de zona</p><h1>{text(profile['name'])}</h1>
<p>{state} · Captura {text(stamp(manifest['created_at']))}</p>
<p class="notice">Instantánea sin conexión: no se actualiza al abrirla. Descargado no significa vigente ni completo. Cada fuente muestra su cobertura y fecha; consulte su vigencia antes de usarla.</p>
<p>Informe calculado {text(stamp(generated))}. Diagnóstico sin calibración local; consulte fuentes oficiales para decisiones de seguridad.</p>
<details><summary>Procedencia y límites</summary><p>Paquete <code>{pack['sha256']}</code>. Integridad comprobada; los hashes no acreditan la identidad del autor ni la exactitud meteorológica.</p><p>Las cifras diarias requieren cobertura completa de 24 horas UTC. Los escenarios requieren al menos diez miembros completos por familia y unidades verificadas. No se aplican umbrales de aviso de otra zona.</p></details></header>
<label for="point-filter">Punto de consulta</label> <select id="point-filter"><option value="all">Todos los puntos</option>{options}</select>
{''.join(blocks)}
<script>document.getElementById('point-filter').addEventListener('change',function(){{document.querySelectorAll('.point').forEach(section=>{{section.hidden=this.value!=='all'&&section.dataset.point!==this.value;}});}});</script>
</main></body></html>'''


def write_report(pack_path, output):
    document = render_report(pack_path)
    with Path(output).open('x',encoding='utf-8') as f:
        f.write(document)
    return str(output)
