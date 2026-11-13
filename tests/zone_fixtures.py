from urllib.parse import urlsplit,parse_qs
from datetime import datetime,timezone,timedelta
import base64,struct,zlib
from weather_core import ENSEMBLE_FAMILIES


def provider(url, *, rain=1, partial_snow=False):
    host = urlsplit(url).hostname
    now=datetime.now(timezone.utc)
    if host=='api.rainviewer.com':
        return {'host':'https://tilecache.rainviewer.com','radar':{'past':[{'path':'/v2/radar/123','time':int(now.timestamp())}]}}
    if host=='tilecache.rainviewer.com':
        def chunk(kind,raw): return struct.pack('>I',len(raw))+kind+raw+struct.pack('>I',zlib.crc32(kind+raw))
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,256,8,6,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+bytes([0,0,0,0])*256)*256))+chunk(b'IEND',b'')
        return {'png_base64':base64.b64encode(png).decode()}
    if host=='aviationweather.gov':
        stations=[('LEIB',39.1153,1.5214),('LESU',42.35,1.90),('LFMP',42.5,2.04)]
        return [{'icaoId':sid,'lat':lat,'lon':lon,'obsTime':int(now.timestamp()),'temp':4,'dewp':2,'wspd':5,'wgst':None,'wdir':180,'altim':1012,'elev':1000} for sid,lat,lon in stations]
    if host=='feeds.meteoalarm.org':
        area='Ibiza; Pirineo de Girona; Pyrénées-Orientales; Andorra'
        return {'xml':f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2"><updated>{now.isoformat()}</updated><entry><id>fixture</id><title>SYNTHETIC WARNING</title><cap:areaDesc>{area}</cap:areaDesc><cap:event>Test</cap:event><cap:severity>Moderate</cap:severity><cap:onset>{(now-timedelta(hours=1)).isoformat()}</cap:onset><cap:expires>{(now+timedelta(hours=1)).isoformat()}</cap:expires></entry></feed>'}

    if '/elevation?' in url:
        return {'elevation':[1600.0]}
    query=parse_qs(urlsplit(url).query)
    if 'surface_pressure' in query.get('hourly',[''])[0]:
        h={'time':[f'2026-11-11T{k:02d}:00' for k in range(24)]};units={}
        for key,unit,v in [('surface_pressure','hPa',850),('temperature_2m','°C',5),('dew_point_2m','°C',2),('wind_speed_10m','m/s',5),('wind_direction_10m','°',270),('cape','J/kg',0),('convective_inhibition','J/kg',0)]:
            h[key]=[v]*24;units[key]=unit
        for pressure,z,t in [(1000,100,18),(925,800,12),(850,1500,5),(700,3000,-5),(500,5500,-20),(300,9000,-45)]:
            for key,unit,v in [('temperature','°C',t),('relative_humidity','%',80),('wind_speed','m/s',10),('wind_direction','°',270),('geopotential_height','m',z)]:
                field=f'{key}_{pressure}hPa';h[field]=[v]*24;units[field]=unit
        return {'hourly':h,'hourly_units':units,'elevation':1600,'latitude':float(query['latitude'][0]),'longitude':float(query['longitude'][0])}
    h = {'time':[f'2026-11-11T{k:02d}:00' for k in range(24)]}
    units = {}
    if host == 'ensemble-api.open-meteo.com':
        for model in ENSEMBLE_FAMILIES:
            for member in range(12):
                for field, unit, val in [('temperature_2m','°C',1),('precipitation','mm',rain),('snowfall','cm',.5)]:
                    name = f'{field}_member{member:02d}_{model}'
                    h[name] = [val]*24
                    units[name] = unit
                    if field=='snowfall' and partial_snow:
                        h[name] = [0]+[None]*23
    elif host == 'marine-api.open-meteo.com':
        for field, unit, val in [('wave_height','m',1.5),('wave_period','s',7),('wave_direction','°',350)]:
            h[field] = [val]*24
            units[field] = unit
        h['wave_direction'] = [350,10]*12
    else:
        for field, unit, val in [('temperature_2m','°C',3),('dew_point_2m','°C',1),('precipitation','mm',rain),
                               ('snowfall','cm',0),('wind_speed_10m','km/h',10),('wind_gusts_10m','km/h',20)]:
            h[field] = [val]*24
            units[field] = unit
        if partial_snow:
            h['snowfall'] = [0]+[None]*23
    return {'hourly':h,'hourly_units':units}
