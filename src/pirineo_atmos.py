"""Perfil modelizado por vertiente; niveles bajo terreno y datos ausentes se descartan."""
import math
import urllib.parse
import portinatx_degen as physics

LEVELS = (1000, 925, 850, 700, 500, 300)
FIELDS = ('cape','cin','li','ki','tt','lr75','thetae850','tcwv','fzl','shr01','shr03','shr06','w850','w700','w500','mw','flux850','blh','tw2m','wbz','u925','div925','div850','vort850','vort500')
POINTS = {'norte': (42.62, 1.80), 'sur': (42.40, 1.90)}

def fetch_profiles():
    variables = [f'{v}_{p}hPa' for p in LEVELS for v in ('temperature','relative_humidity','wind_speed','wind_direction','geopotential_height')]
    variables += ['temperature_2m','dew_point_2m','surface_pressure','wind_speed_10m','wind_direction_10m','cape','convective_inhibition','lifted_index','freezing_level_height','total_column_integrated_water_vapour','boundary_layer_height','vertical_velocity_850hPa','vertical_velocity_700hPa','vertical_velocity_500hPa']
    result = {}
    for side, (lat, lon) in POINTS.items():
        q = {'latitude': lat, 'longitude': lon, 'models': 'best_match', 'wind_speed_unit': 'ms', 'timezone': 'UTC', 'forecast_hours': 48, 'past_hours': 12, 'hourly': ','.join(variables)}
        try:
            raw = physics.get_json('https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(q), timeout=30)
            if not isinstance(raw, dict) or not isinstance(raw.get('hourly'), dict) or not raw['hourly'].get('time'):
                continue
            result[side] = {'hourly': raw['hourly'], 'elevation': raw.get('elevation'), 'ubicacion': {'lat': lat, 'lon': lon}, 'units': raw.get('hourly_units', {})}
        except Exception:
            continue
    if not result:
        raise ValueError('perfiles Open-Meteo no disponibles')
    return result

def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None

def derive(source):
    h = source.get('hourly') or {}; times = h.get('time') or []; z0 = _num(source.get('elevation')); n = len(times)
    def get(k, i):
        a = h.get(k); return _num(a[i]) if isinstance(a, list) and i < len(a) else None
    lv = {str(p): {k: [] for k in ('T','Td','ws','wd','z')} for p in LEVELS}
    idx = {k: [] for k in FIELDS}; theta = {str(p): [] for p in LEVELS}; wet = {str(p): [] for p in LEVELS}; shear = []; comp = {'icc': [], 'ipp': []}; wind10 = {'ws': [], 'wd': []}
    for i in range(n):
        levels = {}; sp = get('surface_pressure', i)
        for p in LEVELS:
            z = get(f'geopotential_height_{p}hPa', i)
            # Both height and surface pressure are required to reject subterranean extrapolation.
            valid = z0 is not None and sp is not None and z is not None and z > z0 + 10 and p < sp
            t = get(f'temperature_{p}hPa', i) if valid else None; rh = get(f'relative_humidity_{p}hPa', i) if valid else None
            td = physics._dewpoint(t, rh) if t is not None and rh is not None and 0 < rh <= 100 else None
            ws = get(f'wind_speed_{p}hPa', i) if valid else None; wd = get(f'wind_direction_{p}hPa', i) if valid else None
            x = {'T':t,'Td':td,'ws':ws,'wd':wd,'z':z if valid else None}; levels[p] = x
            for k, v in x.items(): lv[str(p)][k].append(round(v,2) if v is not None else None)
            theta[str(p)].append(round(physics._thetae(t,td,p),1) if t is not None and td is not None else None)
            w = physics.wet_bulb(t,td,p) if t is not None and td is not None else None; wet[str(p)].append(round(w,1) if w is not None else None)
        ws10, wd10 = get('wind_speed_10m',i), get('wind_direction_10m',i); wind10['ws'].append(ws10); wind10['wd'].append(wd10)
        u10 = physics._uv(ws10,wd10); l85,l70,l50=levels[850],levels[700],levels[500]
        def diff(p):
            u=physics._uv(levels[p]['ws'],levels[p]['wd']); return math.hypot(u[0]-u10[0],u[1]-u10[1]) if u and u10 else None
        def paired(*v): return all(x is not None for x in v)
        ki = l85['T']-l50['T']+l85['Td']-(l70['T']-l70['Td']) if paired(l85['T'],l50['T'],l85['Td'],l70['T'],l70['Td']) else None
        tt = l85['T']+l85['Td']-2*l50['T'] if paired(l85['T'],l85['Td'],l50['T']) else None
        lr = (l70['T']-l50['T'])/((l50['z']-l70['z'])/1000) if paired(l70['T'],l50['T'],l70['z'],l50['z']) and l50['z']>l70['z'] else None
        t2,d2=get('temperature_2m',i),get('dew_point_2m',i); tw2=physics.wet_bulb(t2,d2,sp) if paired(t2,d2,sp) else None
        winds=[physics._uv(levels[p]['ws'],levels[p]['wd']) for p in (850,700,500,300)]; mw=math.hypot(sum(v[0] for v in winds)/4,sum(v[1] for v in winds)/4) if all(winds) else None
        q=physics._q(l85['T'],l85['Td'],850) if l85['Td'] is not None else None
        profile=[{'z':z0,'Tw':tw2}] if paired(z0,tw2) else []
        profile += [{'z':levels[p]['z'],'Tw':wet[str(p)][i]} for p in LEVELS if levels[p]['z'] is not None and wet[str(p)][i] is not None]; profile.sort(key=lambda x:x['z'])
        wbz=None
        for a,b in zip(profile,profile[1:]):
            if a['Tw']>0>=b['Tw'] and b['Tw']!=a['Tw']: wbz=a['z']+(b['z']-a['z'])*a['Tw']/(a['Tw']-b['Tw']);break
        r={'cape':get('cape',i),'cin':get('convective_inhibition',i),'li':get('lifted_index',i),'ki':ki,'tt':tt,'lr75':lr,'thetae850':theta['850'][i],'tcwv':get('total_column_integrated_water_vapour',i),'fzl':get('freezing_level_height',i),'shr01':diff(925),'shr03':diff(700),'shr06':diff(500),'mw':mw,'flux850':q*l85['ws'] if q is not None and l85['ws'] is not None else None,'blh':get('boundary_layer_height',i),'tw2m':tw2,'wbz':wbz,'u925':levels[925]['ws']}
        # Do not infer ascent or convert pressure velocity: expose only geometric m/s with explicit unit.
        units = source.get('units') or {}
        for level in (850, 700, 500):
            key = f'vertical_velocity_{level}hPa'
            if levels[level]['z'] is not None and units.get(key) == 'm/s':
                r[f'w{level}'] = get(key, i)
        if r['cin'] is not None: r['cin']=abs(r['cin'])
        for k in FIELDS: idx[k].append(round(r[k],2) if r.get(k) is not None else None)
        shear.append([[round((levels[p]['z']-z0)/1000,2),round(diff(p),1)] for p in LEVELS if z0 is not None and levels[p]['z'] is not None and diff(p) is not None])
        # Composite scores require all inputs; missing components never become zero.
        for name in comp:
            spec=physics.COMPOSITES[name]; required=[v[0] for v in spec['ranges'].values()]; penalty=spec.get('penalty'); required += [penalty[0]] if penalty else []
            # ICC requires a verified upward-positive convention, not just a numeric velocity.
            missing = [k for k in required if r.get(k) is None]
            if name == 'icc' and 'w700' not in missing: missing.append('signo w700 no verificado')
            comp[name].append(physics.composite(name,r) if not missing else {'value':None,'components':{},'missing':missing})
    return {'modelo':'best_match (Open-Meteo)','ubicacion':source.get('ubicacion'),'elevacion_m':z0,'time':times,'levels':lv,'indices':idx,'wind10':wind10,'physics':{'thetae':theta,'tw':wet,'shear_by_height':shear},'composites':comp}
