"""Regional observations, warning feeds and radar tiles; no territorial globals."""
import base64
from datetime import datetime, timezone
import hashlib
import math
import re
import struct
import unicodedata
import zlib
import urllib.parse
import xml.etree.ElementTree as ET

from weather_core import number

UTC = timezone.utc


def time_utc(value):
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        return datetime.fromtimestamp(value,UTC)
    result = datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if result.tzinfo is None:
        raise ValueError('source timestamp requires timezone')
    return result.astimezone(UTC)


def distance_km(a,b):
    lat1,lat2=map(math.radians,(a['latitude'],b['latitude']))
    dl=math.radians(b['longitude']-a['longitude'])
    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dl/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(h)))


def validate_sources(profile):
    sources=profile.get('sources',{})
    if not isinstance(sources,dict) or set(sources)-{'metar','warning_feeds'}:
        raise ValueError('unknown source configuration')
    stations=sources.get('metar',[])
    if not isinstance(stations,list) or len(stations)>25 or any(not isinstance(x,str) or not re.fullmatch('[A-Z0-9]{4}',x) for x in stations):
        raise ValueError('invalid METAR stations')
    feeds=sources.get('warning_feeds',[])
    if not isinstance(feeds,list) or len(feeds)>5:
        raise ValueError('invalid warning feeds')
    for feed in feeds:
        if not isinstance(feed,dict) or set(feed)!={'country','areas'} or not isinstance(feed['country'],str) or not re.fullmatch('[a-z]{2,30}',feed['country']):
            raise ValueError('invalid warning feed country')
        if not isinstance(feed['areas'],list) or not 1<=len(feed['areas'])<=20 or any(not isinstance(x,str) or not 3<=len(x)<=120 for x in feed['areas']):
            raise ValueError('explicit warning area names required')
    if 'observations' in profile['modules'] and not stations:
        raise ValueError('observations requires sources.metar station identifiers')
    if 'warnings' in profile['modules'] and not feeds:
        raise ValueError('warnings requires sources.warning_feeds and named areas')


def urls(module,profile):
    sources=profile.get('sources',{})
    if module=='observations':
        return ['https://aviationweather.gov/api/data/metar?'+urllib.parse.urlencode({'ids':','.join(sources['metar']),'format':'json','hours':24})]
    if module=='warnings':
        return ['https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-'+f['country'] for f in sources['warning_feeds']]
    if module=='radar':
        return ['https://api.rainviewer.com/public/weather-maps.json']
    raise ValueError('unknown source module')


def observations(raw,point,stations,now):
    if not isinstance(raw,list):
        raise ValueError('invalid METAR response')
    rows=[]
    for item in raw:
        if not isinstance(item,dict) or item.get('icaoId') not in stations:
            continue
        try:
            when=time_utc(item.get('obsTime') or item.get('reportTime'))
            lat,lon=item.get('lat'),item.get('lon')
            if not number(lat) or not number(lon) or abs(lat)>90 or abs(lon)>180:
                continue
            dist=distance_km(point,{'latitude':lat,'longitude':lon})
            age=(now-when).total_seconds()/60
            if dist>100 or age < -5 or age>1440:
                continue
            def val(key,factor=1):
                return item[key]*factor if number(item.get(key)) else None
            rows.append({'station':item['icaoId'],'observed_at':when.isoformat(),
                         'latitude':lat,'longitude':lon,'elevation_m':val('elev'),
                         'distance_km':round(dist,3),'age_minutes':round(age,1),
                         'freshness':'fresh' if age<=120 else 'stale',
                         'temperature_c':val('temp'),'dew_point_c':val('dewp'),
                         'wind_kmh':val('wspd',1.852),'gust_kmh':val('wgst',1.852),
                         'wind_direction_deg':val('wdir'),'pressure_hpa':val('altim')})
        except (ValueError,TypeError,OverflowError):
            continue
    unique={(r['station'],r['observed_at']):r for r in rows}
    return {'schema':1,'kind':'observations','records':sorted(unique.values(),key=lambda r:r['observed_at']),
            'coverage':'nearby stations within 100 km; not necessarily local or altitude matched',
            'status':'AVAILABLE' if rows else 'UNKNOWN'}


def _normal(value):
    return ''.join(x for x in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(x))


def warnings(raw,feed,now):
    xml=raw.get('xml') if isinstance(raw,dict) else None
    if not isinstance(xml,str) or '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
        raise ValueError('invalid warning XML')
    root=ET.fromstring(xml)
    if root.tag.split('}')[-1]!='feed':
        raise ValueError('expected Atom warning feed')
    def tag(node,name):
        return next((e.text or '' for e in node.iter() if e.tag.split('}')[-1]==name),'')
    output=[]
    for entry in root:
        if entry.tag.split('}')[-1]!='entry':
            continue
        area=tag(entry,'areaDesc')
        if not any(_normal(key) in _normal(area) for key in feed['areas']):
            continue
        try:
            start,end=time_utc(tag(entry,'onset')),time_utc(tag(entry,'expires'))
        except (ValueError,TypeError):
            continue
        if end<=now or end<=start:
            continue
        output.append({'id':tag(entry,'id'),'country':feed['country'],'area':area,
                       'event':tag(entry,'event') or tag(entry,'title'), 'severity':tag(entry,'severity') or 'unknown',
                       'certainty':tag(entry,'certainty') or 'unknown', 'onset':start.isoformat(),'expires':end.isoformat(),
                       'state':'active' if start<=now else 'future','source_type':'official-feed'})
    updated=tag(root,'updated')
    try:
        age=(now-time_utc(updated)).total_seconds()/3600
        feed_state='fresh' if -0.1<=age<=24 else 'stale'
    except (ValueError,TypeError):
        feed_state='unknown'
    return {'records':output,'feed_updated':updated,'feed_state':feed_state,'areas':feed['areas'],'country':feed['country']}


def radar(raw,point,getter,now):
    host=raw.get('host') if isinstance(raw,dict) else None
    if host!='https://tilecache.rainviewer.com':
        raise ValueError('unsupported radar tile host')
    lat=point['latitude'];lon=point['longitude'];zoom=7
    if abs(lat)>85:
        raise ValueError('outside supported Mercator latitude')
    x=(lon+180)/360*2**zoom
    y=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*2**zoom
    frames=[]
    radar_data=raw.get('radar')
    if not isinstance(radar_data,dict) or not isinstance(radar_data.get('past'),list):
        raise ValueError('invalid radar metadata')
    candidates=[f for f in radar_data['past'] if isinstance(f,dict) and number(f.get('time'))]
    for frame in sorted(candidates,key=lambda f:f['time'])[-3:]:
        if not isinstance(frame,dict) or not re.fullmatch(r'/v2/radar/[0-9]+',str(frame.get('path'))):
            continue
        when=time_utc(frame.get('time'))
        age=(now-when).total_seconds()/60
        if age < -5 or age>120:
            continue
        url=f'{host}{frame["path"]}/256/{zoom}/{int(x)%2**zoom}/{int(y)}/2/0_0.png'
        tile=getter(url)
        image=tile.get('png_base64') if isinstance(tile,dict) else None
        blob=validate_png(image)
        frames.append({'observed_at':when.isoformat(),'age_minutes':round(age,1),
                       'freshness':'fresh' if age<=20 else 'stale','url':url,'png_base64':image,
                       'sha256':hashlib.sha256(blob).hexdigest(), 'zoom':zoom,
                       'point_pixel':[round((x%1)*256,2),round((y%1)*256,2)]})
    if not frames:
        raise ValueError('no radar frames in collection window')
    return {'schema':1,'kind':'radar','frames':frames,
            'coverage':'UNVERIFIED: transparent or blank tiles do not prove dry weather',
            'frame_time_semantics':'composite frame time; individual radar observations may be older or unknown',
            'interpretation':'radar image only; no calibrated local rain rate or warning'}


def validate_png(value):
    if not isinstance(value,str) or len(value)>3_000_000:
        raise ValueError('invalid radar tile')
    blob=base64.b64decode(value,validate=True)
    if not blob.startswith(b'\x89PNG\r\n\x1a\n') or len(blob)<33 or blob[12:16]!=b'IHDR' or struct.unpack('>II',blob[16:24])!=(256,256):
        raise ValueError('expected 256 pixel PNG tile')
    offset=8
    ended=False
    while offset+12<=len(blob):
        length=struct.unpack('>I',blob[offset:offset+4])[0]
        end=offset+12+length
        if end>len(blob):
            raise ValueError('truncated PNG')
        chunk=blob[offset+4:end-4]
        if zlib.crc32(chunk)!=struct.unpack('>I',blob[end-4:end])[0]:
            raise ValueError('PNG checksum mismatch')
        offset=end
        if chunk[:4]==b'IEND':
            ended=True
            break
    if not ended or offset!=len(blob):
        raise ValueError('incomplete PNG')
    return blob


def fetch(module,point,profile,getter,now=None):
    now=now or datetime.now(UTC)
    endpoints=urls(module,profile)
    if module=='observations':
        result=observations(getter(endpoints[0]),point,profile['sources']['metar'],now)
        if result['status']=='UNKNOWN':
            raise ValueError('no usable nearby observations')
        return result
    if module=='radar':
        return radar(getter(endpoints[0]),point,getter,now)
    feeds=[];failures=[]
    for endpoint,config in zip(endpoints,profile['sources']['warning_feeds']):
        try:
            feeds.append(warnings(getter(endpoint),config,now))
        except (OSError,ValueError,ET.ParseError):
            failures.append(config['country'])
    if not feeds:
        raise ValueError('no usable warning feeds')
    return {'schema':1,'kind':'warnings','records':[r for f in feeds for r in f['records']],
            'feeds':feeds,'failed_feeds':failures,'coverage':'PARTIAL' if failures else 'configured area names only',
            'interpretation':'empty feed matches do not certify absence of official warnings'}


def validate_data(module,data):
    if not isinstance(data,dict) or data.get('schema')!=1 or data.get('kind')!=module:
        raise ValueError('invalid regional source data')
    if module=='radar':
        if not isinstance(data.get('frames'),list) or not 1<=len(data['frames'])<=3:
            raise ValueError('invalid radar frames')
        for frame in data['frames']:
            blob=validate_png(frame.get('png_base64'))
            if hashlib.sha256(blob).hexdigest()!=frame.get('sha256'):
                raise ValueError('radar checksum mismatch')
            time_utc(frame['observed_at'])
            if not isinstance(frame.get('point_pixel'),list) or len(frame['point_pixel'])!=2 or any(not number(x) or not 0<=x<=256 for x in frame['point_pixel']):
                raise ValueError('invalid point pixel')
    else:
        if not isinstance(data.get('records'),list):
            raise ValueError('records required')
        for row in data['records']:
            if not isinstance(row,dict):
                raise ValueError('invalid source record')
            if module=='observations':
                time_utc(row['observed_at'])
                for field in ('temperature_c','dew_point_c','wind_kmh','gust_kmh','wind_direction_deg','pressure_hpa','distance_km'):
                    if row.get(field) is not None and not number(row[field]):
                        raise ValueError('invalid observation number')
            else:
                time_utc(row['onset']);time_utc(row['expires'])
