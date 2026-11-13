"""Shared, terrain-aware atmospheric diagnostics; no geography or alert authority.

Only declared units are used. Scalars remain missing when either their measurements,
units or terrain context are missing. Composite scores are experimental ingredients,
not calibrated probabilities. Pressure velocity is never relabelled as geometric w.
"""
import math
from datetime import datetime
from weather_core import number, wet_bulb_psychro

LEVELS = (1000, 925, 850, 700, 500, 300)
PROFILE_VARIABLES = [f'{v}_{p}hPa' for p in LEVELS for v in
                     ('temperature','relative_humidity','wind_speed','wind_direction','geopotential_height')]
PROFILE_VARIABLES += ['temperature_2m','dew_point_2m','surface_pressure','pressure_msl',
                     'wind_speed_10m','wind_direction_10m','cape','convective_inhibition',
                     'lifted_index','freezing_level_height','total_column_integrated_water_vapour',
                     'boundary_layer_height','precipitation','vertical_velocity_850hPa',
                     'vertical_velocity_700hPa','vertical_velocity_500hPa']
FIELDS = ('cape','cin','li','ki','tt','lr75','thetae850','tcwv','fzl','shr01','shr03','shr06',
          'w850','w700','w500','mw','flux850','blh','tw2m','wbz','u925','div925','div850',
          'vort850','vort500','froude','t2m','td2m','pmsl','pr')
COMPOSITES = {
    'icc': {'weights': {'inestabilidad':.30,'humedad':.30,'ascenso':.20,'organizacion':.20},
            'ranges': {'inestabilidad':('cape',0,2000),'humedad':('tcwv',20,40),
                       'ascenso':('w700',0,.3),'organizacion':('shr06',5,25)},
            'penalty':('cin',0,200,.5)},
    'ipp': {'weights': {'humedad':.30,'alimentacion':.30,'lentitud':.25,'inestabilidad':.15},
            'ranges': {'humedad':('tcwv',20,40),'alimentacion':('flux850',50,250),
                       'lentitud':('mw',20,5),'inestabilidad':('cape',0,1500)},'penalty':None},
}


def _num(value):
    return float(value) if number(value) else None


def _round(value, digits=2):
    return round(value,digits) if number(value) else None


def dewpoint(t, rh):
    if not number(t) or not -100<=t<=70 or not number(rh) or not 0<rh<=100:
        return None
    g=math.log(rh/100)+17.625*t/(243.04+t)
    return 243.04*g/(17.625-g)


def thetae(t, td, p):
    if not all(number(v) for v in (t,td,p)) or not -100<=td<=t<=70 or not 100<=p<=1100:
        return None
    tk,tdk=t+273.15,td+273.15
    e=6.112*math.exp(17.67*td/(td+243.5))
    if e>=p:return None
    r=622*e/(p-e)
    tl=1/(1/(tdk-56)+math.log(tk/tdk)/800)+56
    return tk*(1000/p)**(.2854*(1-.00028*r))*math.exp((3.376/tl-.00254)*r*(1+.00081*r))


def specific_humidity(t, td, p):
    if not all(number(v) for v in (td,p)) or not -100<=td<=70 or not 100<=p<=1100:
        return None
    e=6.112*math.exp(17.67*td/(td+243.5))
    return 622*e/(p-.378*e) if e<p else None


def uv(speed, direction):
    if not number(speed) or speed<0 or not number(direction) or not 0<=direction<=360:return None
    angle=math.radians(direction)
    return -speed*math.sin(angle),-speed*math.cos(angle)


def composite(name, row, *, upward_verified=False, weights=None):
    spec=COMPOSITES[name];parts={};missing=[]
    weights=spec['weights'] if weights is None else weights
    if not isinstance(weights,dict) or set(weights)!=set(spec['weights']) or any(not number(v) or v<0 for v in weights.values()) or sum(weights.values())<=0:
        raise ValueError('invalid composite weights')
    for key,(field,lo,hi) in spec['ranges'].items():
        value=row.get(field)
        parts[key]=max(0,min(1,(value-lo)/(hi-lo))) if number(value) else None
        if parts[key] is None:missing.append(field)
    penalty=None
    if spec['penalty']:
        field,lo,hi,factor=spec['penalty'];value=row.get(field)
        if number(value):penalty=max(0,min(1,(value-lo)/(hi-lo)))
        else:missing.append(field)
    if name=='icc' and not upward_verified:missing.append('signo w700 no verificado')
    result=None
    if not missing:
        result=sum(weights[key]*value for key,value in parts.items())/sum(weights.values())
        if penalty is not None:result*=1-factor*penalty
    return {'value':_round(result,3),'components':{k:_round(v,3) for k,v in parts.items()},
            'penalty':_round(penalty,3),'missing':missing,'status':'EXPERIMENTAL_UNCALIBRATED'}


def _reader(source, times):
    h=source.get('hourly') or {};units=source.get('units',source.get('hourly_units')) or {}
    def get(key,i):
        a=h.get(key)
        if not isinstance(a,list) or len(a)!=len(times) or i>=len(a) or not number(a[i]):return None
        value=float(a[i]);unit=units.get(key)
        if key.startswith(('temperature','dew_point')):
            if unit not in ('°C','C','celsius'):return None
            return value if -100<=value<=70 else None
        if key.startswith('relative_humidity'):
            return value if unit=='%' and 0<value<=100 else None
        if key.startswith('wind_speed'):
            if unit=='km/h':value/=3.6
            elif unit!='m/s':return None
            return value if value>=0 else None
        if key.startswith('wind_direction'):
            return value if unit in ('°','degrees') and 0<=value<=360 else None
        if key.startswith('geopotential_height') or key in ('freezing_level_height','boundary_layer_height'):
            return value if unit=='m' else None
        if key in ('surface_pressure','pressure_msl'):
            if unit=='Pa':value/=100
            elif unit!='hPa':return None
            return value if 100<=value<=1100 else None
        if key in ('cape','convective_inhibition'):
            return value if unit=='J/kg' and (key!='cape' or value>=0) else None
        if key=='lifted_index':return value if unit in ('°C','K') else None
        if key=='total_column_integrated_water_vapour':
            return value if unit in ('kg/m²','kg/m2','mm') and value>=0 else None
        if key=='precipitation':return value if unit=='mm' and value>=0 else None
        if key.startswith('vertical_velocity'):return value if unit=='m/s' else None
        return None
    return get


def _profile(source,times,i):
    get=_reader(source,times);ground=_num(source.get('elevation'));sp=get('surface_pressure',i)
    result={}
    for p in LEVELS:
        z=get(f'geopotential_height_{p}hPa',i)
        valid=ground is not None and sp is not None and z is not None and z>ground+10 and p<sp
        t=get(f'temperature_{p}hPa',i) if valid else None
        result[p]={'T':t,'Td':dewpoint(t,get(f'relative_humidity_{p}hPa',i)) if valid else None,
                   'ws':get(f'wind_speed_{p}hPa',i) if valid else None,
                   'wd':get(f'wind_direction_{p}hPa',i) if valid else None,'z':z if valid else None}
    return result,get,ground,sp


def _stencil_derivatives(stencil,geometry,times,i):
    if not isinstance(stencil,dict) or not isinstance(geometry,dict):return {}
    lat=geometry.get('latitude');dlat=geometry.get('delta_lat_deg');dlon=geometry.get('delta_lon_deg')
    if not all(number(x) for x in (lat,dlat,dlon)) or abs(lat)>=85 or not 0<dlat<=2 or not 0<dlon<=2:return {}
    profiles={}
    for side in ('N','S','E','W'):
        source=stencil.get(side)
        if not isinstance(source,dict) or source.get('hourly',{}).get('time')!=times:return {}
        profiles[side]=_profile(source,times,i)[0]
    # Derivatives must use the returned grid cells, not the requested spacing:
    # Open-Meteo may snap each request to a different model coordinate.
    locations={side:stencil[side].get('ubicacion') for side in profiles}
    if any(not isinstance(loc,dict) or not number(loc.get('lat')) or not number(loc.get('lon'))
           or abs(loc['lat'])>=85 or abs(loc['lon'])>180 for loc in locations.values()):return {}
    n,s,e,w=(locations[side] for side in ('N','S','E','W'))
    if not 0<n['lat']-s['lat']<=4 or not 0<e['lon']-w['lon']<=4:return {}
    if abs(n['lon']-s['lon'])>.001 or abs(e['lat']-w['lat'])>.001:return {}
    if any(abs(loc['lat']-lat)>2*dlat+.01 for loc in locations.values()):return {}
    center_lon=geometry.get('longitude')
    if not number(center_lon) or any(abs(loc['lon']-center_lon)>2*dlon+.01 for loc in locations.values()):return {}
    dx=(e['lon']-w['lon'])*111000*math.cos(math.radians((e['lat']+w['lat'])/2))
    dy=(n['lat']-s['lat'])*111000
    result={}
    for p in (925,850,500):
        winds={side:uv(profiles[side][p]['ws'],profiles[side][p]['wd']) for side in profiles}
        if all(winds.values()):
            n,s,e,w=(winds[side] for side in ('N','S','E','W'))
            result['div'+str(p)]=((e[0]-w[0])/dx+(n[1]-s[1])/dy)*1e5
            result['vort'+str(p)]=((e[1]-w[1])/dx-(n[0]-s[0])/dy)*1e5
    return result


def derive(source, stencil=None, geometry=None, terrain_top=None):
    """Canonical source: hourly, units/hourly_units, elevation, ubicacion, model.

    Output heights are MSL except shear_by_height (km AGL). Named shear indices
    retain legacy pressure-level approximations, not exact geometric layer shear.
    Stencil neighbors use the same source schema and exact matching time axis.
    terrain_top is an explicitly supplied obstacle height above model ground (m).
    """
    if not isinstance(source,dict):raise ValueError('atmospheric source must be an object')
    h=source.get('hourly') or {}
    if not isinstance(h,dict) or not isinstance(source.get('units',source.get('hourly_units',{})),dict):
        raise ValueError('hourly data and units must be objects')
    times=h.get('time') or []
    if not isinstance(times,list) or any(not isinstance(t,str) for t in times) or len(set(times))!=len(times) or times!=sorted(times):
        raise ValueError('invalid atmospheric time axis')
    for timestamp in times:
        datetime.fromisoformat(timestamp.replace('Z','+00:00'))
    indices={k:[] for k in FIELDS};levels={str(p):{k:[] for k in ('T','Td','ws','wd','z')} for p in LEVELS}
    physics={'thetae':{str(p):[] for p in LEVELS},'tw':{str(p):[] for p in LEVELS},'shear_by_height':[]}
    composites={'icc':[],'ipp':[]};wind10={'ws':[],'wd':[]};coverage=[]
    def paired(*values):return all(v is not None for v in values)
    for i in range(len(times)):
        L,get,ground,sp=_profile(source,times,i)
        for p in LEVELS:
            for k,v in L[p].items():levels[str(p)][k].append(_round(v))
        ws10,wd10=get('wind_speed_10m',i),get('wind_direction_10m',i)
        wind10['ws'].append(ws10);wind10['wd'].append(wd10);v10=uv(ws10,wd10)
        def shear(p):
            other=uv(L[p]['ws'],L[p]['wd'])
            return math.hypot(other[0]-v10[0],other[1]-v10[1]) if other and v10 else None
        a,b,c=L[850],L[700],L[500]
        t2,d2=get('temperature_2m',i),get('dew_point_2m',i)
        tw2=wet_bulb_psychro(t2,d2,sp) if paired(t2,d2,sp) and d2<=t2 else None
        wet={}
        for p in LEVELS:
            te=thetae(L[p]['T'],L[p]['Td'],p)
            wet[p]=wet_bulb_psychro(L[p]['T'],L[p]['Td'],p)
            physics['thetae'][str(p)].append(_round(te,1));physics['tw'][str(p)].append(_round(wet[p],1))
        column=[(ground,tw2)] if paired(ground,tw2) else []
        column+= [(L[p]['z'],wet[p]) for p in LEVELS if paired(L[p]['z'],wet[p])];column.sort()
        wbz=None
        for low,high in zip(column,column[1:]):
            if low[1]>0>=high[1] and high[0]>low[0]:
                wbz=low[0]+(high[0]-low[0])*low[1]/(low[1]-high[1]);break
        winds=[uv(L[p]['ws'],L[p]['wd']) for p in (850,700,500,300)]
        mw=math.hypot(sum(v[0] for v in winds)/4,sum(v[1] for v in winds)/4) if all(winds) else None
        q=specific_humidity(a['T'],a['Td'],850)
        row={'cape':get('cape',i),'cin':get('convective_inhibition',i),'li':get('lifted_index',i),
             'ki':a['T']-c['T']+a['Td']-(b['T']-b['Td']) if paired(a['T'],c['T'],a['Td'],b['T'],b['Td']) else None,
             'tt':a['T']+a['Td']-2*c['T'] if paired(a['T'],a['Td'],c['T']) else None,
             'lr75':(b['T']-c['T'])/((c['z']-b['z'])/1000) if paired(b['T'],c['T'],b['z'],c['z']) and c['z']>b['z'] else None,
             'thetae850':thetae(a['T'],a['Td'],850),'tcwv':get('total_column_integrated_water_vapour',i),
             'fzl':get('freezing_level_height',i),'shr01':shear(925),'shr03':shear(700),'shr06':shear(500),
             'mw':mw,'flux850':q*a['ws'] if paired(q,a['ws']) else None,'blh':get('boundary_layer_height',i),
             'tw2m':tw2,'wbz':wbz,'u925':L[925]['ws'],'t2m':t2,'td2m':d2,'pmsl':get('pressure_msl',i),'pr':get('precipitation',i)}
        if row['cin'] is not None:row['cin']=abs(row['cin'])
        for p in (850,700,500):row['w'+str(p)]=get(f'vertical_velocity_{p}hPa',i) if L[p]['z'] is not None else None
        row.update(_stencil_derivatives(stencil,geometry,times,i))
        if number(terrain_top) and terrain_top>0 and paired(L[1000]['T'],a['T'],L[1000]['z'],a['z'],L[925]['ws']) and a['z']>L[1000]['z']:
            lo=L[1000]['T']+273.15;hi=(a['T']+273.15)*(1000/850)**.2854
            n2=9.81/((lo+hi)/2)*(hi-lo)/(a['z']-L[1000]['z'])
            if n2>0:row['froude']=L[925]['ws']/(math.sqrt(n2)*terrain_top)
        for key in FIELDS:indices[key].append(_round(row.get(key),3 if key.startswith('w') and key!='wbz' else 2))
        physics['shear_by_height'].append([[_round((L[p]['z']-ground)/1000),_round(shear(p),1)] for p in LEVELS if ground is not None and L[p]['z'] is not None and shear(p) is not None])
        for name in composites:composites[name].append(composite(name,row,upward_verified=source.get('vertical_velocity_positive')=='up'))
        coverage.append({'usable_levels':[p for p in LEVELS if L[p]['z'] is not None],
                         'surface_pressure_hpa':sp,'surface_thermodynamics':tw2 is not None})
    return {'time':times,'indices':indices,'levels':levels,'physics':physics,'composites':composites,'wind10':wind10,
            'modelo':source.get('model','best_match (Open-Meteo)'),'ubicacion':source.get('ubicacion'),
            'elevacion_m':_num(source.get('elevation')),
            'quality':{'engine':'atmospheric-core-v1','basis':'MODEL_DIAGNOSTIC','units':'explicit canonical conversions; missing units remain UNKNOWN',
                       'vertical_velocity_positive':source.get('vertical_velocity_positive','UNVERIFIED'),
                       'height_reference':'levels/WBZ MSL; shear_by_height AGL',
                       'shear_basis':'surface-to-pressure-level proxies; not exact 1/3/6 km layers',
                       'coverage':coverage,'calibrated':False}}
