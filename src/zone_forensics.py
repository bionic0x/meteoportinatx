"""Frozen forecasts matched to reviewed measurements, by event and region.

No training, automated recalibration or promotion of anecdotes into truth.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

from zone_packages import read_pack, analysis
from zone_sources import distance_km,time_utc
from weather_core import number

VARIABLES={'precipitation':'mm','snowfall':'cm','temperature_2m':'°C','wind_gusts_10m':'km/h',
           'wave_height':'m','wave_period':'s','wave_direction':'°'}
AGGREGATION={'precipitation':'sum','snowfall':'sum','temperature_2m':'min','wind_gusts_10m':'max',
             'wave_height':'max','wave_period':'max','wave_direction':'circular_mean'}


def normalize_observation(row,now):
    required={'event','point','variable','value','unit','aggregation','start','end','observed_at',
              'latitude','longitude','source_url','source_id','review_status'}
    if not isinstance(row,dict) or not required<=row.keys() or set(row)-required-{'baseline'}:
        raise ValueError('observation fields missing or unknown')
    if row['review_status']!='VERIFIED':
        raise ValueError('requires independently reviewed measurements; community leads excluded')
    for field in ('event','point','source_id'):
        if not isinstance(row[field],str) or not re.fullmatch('[A-Za-z0-9_-]{1,100}',row[field]):
            raise ValueError('invalid observation identifier')
    var=row['variable']
    if not isinstance(var,str) or var not in VARIABLES or row['unit']!=VARIABLES[var] or row['aggregation']!=AGGREGATION[var]:
        raise ValueError('variable, unit or accumulation operator mismatch')
    if not number(row['value']) or ('baseline' in row and not number(row['baseline'])):
        raise ValueError('non-finite measurement')
    if var not in ('temperature_2m',) and row['value']<0:
        raise ValueError('negative measurement')
    if var=='wave_direction' and row['value']>360:
        raise ValueError('invalid direction')
    start,end,observed=(time_utc(row[k]) for k in ('start','end','observed_at'))
    if start.hour or start.minute or start.second or start.microsecond or end-start!=timedelta(days=1):
        raise ValueError('requires an exact UTC day matching daily forecast aggregation')
    if not end<=observed<=now:
        raise ValueError('future or premature observation')
    for field,bound in [('latitude',90),('longitude',180)]:
        if not number(row[field]) or abs(row[field])>bound:
            raise ValueError('invalid measurement location')
    url=urlsplit(row['source_url'])
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.fragment or url.query:
        raise ValueError('public HTTPS observation source without credentials or query required')
    return {**row,'start':start.isoformat(),'end':end.isoformat(),'observed_at':observed.isoformat()}


def _error(forecast,observed,var):
    if var=='wave_direction':
        return (forecast-observed+180)%360-180
    return forecast-observed


def evaluate(paths,observations,*,max_distance_km=1.0,now=None):
    now=now or datetime.now(timezone.utc)
    if not number(max_distance_km) or not 0<max_distance_km<=20:
        raise ValueError('distance tolerance must be in (0,20] km')
    if not isinstance(observations,list) or len(observations)>10000:
        raise ValueError('observations must be a bounded list')
    packs=[read_pack(path) for path in paths]
    if not packs or len(packs)>100:
        raise ValueError('supply 1 to 100 frozen forecast packs')
    profile=packs[0]['profile']
    if any(p['profile']!=profile for p in packs):
        raise ValueError('forecast packs must share the exact regional profile')
    points={p['id']:p for p in profile['points']}
    rows=[normalize_observation(r,now) for r in observations]
    seen={};unique=[]
    for row in rows:
        key=(row['point'],row['variable'],row['start'],row['end'])
        if key in seen:
            if seen[key]!=row:
                raise ValueError('conflicting or non-independent duplicate measurement')
            continue
        seen[key]=row;unique.append(row)
    computations={p['sha256']:analysis(p) for p in packs}
    matches=[];exclusions=[]
    for row in unique:
        reason=None
        point=points.get(row['point'])
        if point is None:
            reason='point not in profile'
        elif distance_km(point,row)>max_distance_km:
            reason='observation outside spatial tolerance'
        start=time_utc(row['start'])
        eligible=sorted([p for p in packs if max([time_utc(p['manifest']['created_at'])]+[time_utc(e['retrieved_at']) for e in p['manifest']['entries']])<start],
                        key=lambda p:time_utc(p['manifest']['created_at']),reverse=True)
        if not reason and not eligible:
            reason='no forecast collected before the valid window'
        if reason:
            exclusions.append({'point':row['point'],'event':row['event'],'variable':row['variable'],'reason':reason});continue
        # Latest eligible collection, never cherry-pick the forecast with best error
        # or silently fall back to an older forecast when its current field is absent.
        pack=eligible[0];module='marine' if row['variable'].startswith('wave_') else 'forecast'
        day=start.date().isoformat()
        daily=computations[pack['sha256']][row['point']].get(module,{}).get(day,{})
        value=daily.get('values',{}).get(row['variable'])
        unit=daily.get('units',{}).get(row['variable'])
        if value is None or unit!=row['unit']:
            exclusions.append({'point':row['point'],'event':row['event'],'variable':row['variable'],'reason':'missing forecast, incomplete coverage or unit mismatch'});continue
        item={'event':row['event'],'point':row['point'],'variable':row['variable'],'unit':unit,
              'valid_start':row['start'],'valid_end':row['end'],'collected_at':pack['manifest']['created_at'],
              'forecast_sha256':pack['sha256'],'observed':row['value'],'forecast':value,
              'error':_error(value,row['value'],row['variable']),
              'source_url':row['source_url'],'source_id':row['source_id'],
              'distance_km':round(distance_km(point,row),3),
              'collection_lead_hours':(start-time_utc(pack['manifest']['created_at'])).total_seconds()/3600}
        if 'baseline' in row:
            item['baseline_error']=_error(row['baseline'],row['value'],row['variable'])
        metric={'precipitation':'rain_ge10','snowfall':'snow_ge5'}.get(row['variable'])
        if metric:
            m=computations[pack['sha256']][row['point']].get('ensemble',{}).get(day,{}).get('metrics',{}).get(metric,{})
            if m.get('fraction') is not None:
                y=int(row['value']>=m['threshold'])
                item['ensemble']={'fraction':m['fraction'],'observation':y,'brier':(m['fraction']-y)**2,
                                  'n_families':m['n_families'],'threshold':m['threshold']}
        matches.append(item)
    scores={}
    for variable in sorted({m['variable'] for m in matches}):
        subset=[m for m in matches if m['variable']==variable]
        events=sorted({m['event'] for m in subset})
        means=[]
        for event in events:
            part=[m for m in subset if m['event']==event]
            means.append({'bias':sum(m['error'] for m in part)/len(part),
                          'mae':sum(abs(m['error']) for m in part)/len(part),
                          'mse':sum(m['error']**2 for m in part)/len(part)})
        scores[variable]={'unit':VARIABLES[variable],'n_pairs':len(subset),'n_events':len(events),
                          'bias':sum(m['bias'] for m in means)/len(means),
                          'mae':sum(m['mae'] for m in means)/len(means),
                          'rmse':math.sqrt(sum(m['mse'] for m in means)/len(means))}
        baselines=[m for m in subset if 'baseline_error' in m]
        if baselines:
            diffs=[sum(abs(m['error'])-abs(m['baseline_error']) for m in baselines if m['event']==e)/sum(m['event']==e for m in baselines)
                   for e in sorted({m['event'] for m in baselines})]
            scores[variable]['mae_difference_vs_baseline_on_common_pairs']=sum(diffs)/len(diffs)
            scores[variable]['baseline_pairs']=len(baselines)
        ensembles=[m for m in subset if 'ensemble' in m]
        if ensembles:
            bs=[sum(m['ensemble']['brier'] for m in ensembles if m['event']==e)/sum(m['event']==e for m in ensembles)
                for e in sorted({m['event'] for m in ensembles})]
            scores[variable]['brier']=sum(bs)/len(bs)
    observations_hash=hashlib.sha256(json.dumps(unique,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    return {'schema':1,'zone':profile['id'],'evaluated_at':now.isoformat(),'observation_sha256':observations_hash,
            'forecast_hashes':sorted({p['sha256'] for p in packs}), 'scores':scores,'matches':matches,'excluded':exclusions,
            'weighting':'equal weight per independent user-labelled event; event independence requires review',
            'scope':'daily point verification; collected-before-window gate; model initialization may remain unverified',
            'limitations':['VERIFIED is a human review declaration, not automatic authentication',
                           'spatial tolerance does not validate altitude, exposure or instrument quality',
                           'no learned correction or warning changes; descriptive skill only'],
            'calibration_applied':False}


def save_result(result,path):
    # Do not publish private observations automatically. Local explicit output only.
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    return result


def render_result(result):
    """Local review sheet; observations and exclusions remain visible and private."""
    from html import escape
    def esc(value): return escape(str(value),quote=True)
    rows=[]
    for variable,score in result['scores'].items():
        rows.append('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in (variable,score['unit'],score['n_pairs'],score['n_events'],round(score['bias'],3),round(score['mae'],3),round(score['rmse'],3),score.get('brier','—'),score.get('mae_difference_vs_baseline_on_common_pairs','—')))+'</tr>')
    matches=[]
    for m in result['matches']:
        matches.append('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in (m['event'],m['point'],m['variable'],m['valid_start'],m['forecast'],m['observed'],m['error'],m['source_id']))+'</tr>')
    excluded=''.join('<li>'+esc(f'{r["event"]} / {r["point"]} / {r["variable"]}: {r["reason"]}')+'</li>' for r in result['excluded'])
    hashes=''.join('<li><code>'+esc(h)+'</code></li>' for h in result['forecast_hashes'])
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forense · {esc(result['zone'])}</title>
<style>body{{font:16px/1.6 system-ui;margin:24px;background:#f4f7f8;color:#172b3a}}main{{max-width:1200px;margin:auto}}.table{{overflow-x:auto}}table{{border-collapse:collapse;background:white;width:100%}}td,th{{padding:10px;border-bottom:1px solid #ccd4da;text-align:left}}code{{overflow-wrap:anywhere}}</style></head><body><main>
<h1>Evaluación forense · {esc(result['zone'])}</h1><p>Evaluado {esc(result['evaluated_at'])}. Informe local: puede contener información de observaciones privadas.</p>
<p>Pronósticos recogidos antes del día evaluado; medidas declaradas revisadas. Cada episodio tiene el mismo peso. MAE y RMSE menores indican menos error; sesgo positivo indica sobreestimación. Brier evalúa fracciones ensemble sin calibrar. Diferencia MAE frente a referencia negativa indica mejora sobre pares comunes.</p>
<p>Resultados descriptivos; no demuestran habilidad fuera de esta muestra. No se aplican correcciones aprendidas. Se requiere revisar independencia de episodios, altitud, exposición, instrumentos y fecha de inicialización del modelo.</p>
<h2>Resultados</h2><div class="table"><table><tr><th>Variable</th><th>Unidad</th><th>Pares</th><th>Episodios</th><th>Sesgo</th><th>MAE</th><th>RMSE</th><th>Brier</th><th>Δ MAE referencia</th></tr>{''.join(rows)}</table></div>
<h2>Pares utilizados</h2><div class="table"><table><tr><th>Episodio</th><th>Punto</th><th>Variable</th><th>Día UTC</th><th>Previsión</th><th>Observación</th><th>Error</th><th>Fuente</th></tr>{''.join(matches)}</table></div>
<h2>Exclusiones ({len(result['excluded'])})</h2><ul>{excluded}</ul><h2>Trazabilidad</h2><p>Observaciones SHA-256: <code>{esc(result['observation_sha256'])}</code></p><ul>{hashes}</ul>
<p>El JSON asociado contiene procedencia, distancias, tiempos y denominadores. Los paquetes originales conservan el contexto de radar, avisos y estaciones que se pudo descargar. Los hashes detectan cambios, no autentican por sí solos un archivo histórico.</p></main></body></html>'''
