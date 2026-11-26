"""Sensibilidad de la señal post hoc de transiciones NW<->E/SE (fase 02): umbral húmedo, giro de sectores, consistencia."""
import json, glob, warnings, numpy as np, pandas as pd, xarray as xr
from scipy import stats
import os
os.chdir(os.environ.get("SEPI_DATA", "."))  # datos y salidas fuera del repo (ver scripts/sepi/README.md)
warnings.filterwarnings("ignore")
P={}
for c in ["Z3","Z9","DG","ZC"]:
    d=pd.DataFrame(json.load(open(f"xema/P_{c}.json"))); d["d"]=pd.to_datetime(d["d"]); d=d.set_index("d")
    s=d.p.astype(float); s[d.n.astype(int)<40]=np.nan; s[s>250]=np.nan; P[c]=s
P=pd.DataFrame(P); com=P.loc["2011-12-01":"2026-03-31"]; com=com[com.index.month.isin([12,1,2,3])]
pE=(P/com.mean()*com.mean().mean()).mean(axis=1); pE[P.notna().sum(axis=1)<2]=np.nan
parts=[]
for f in sorted(glob.glob("mf/66067402_PUIGMAL-NIVOSE_MTO_1H_*.nc")):
    d=xr.open_dataset(f)
    if "wd" in d: parts.append(pd.DataFrame({"wd":d.wd.values,"ws":d.ws.values},index=pd.to_datetime(d.time.values)))
w=pd.concat(parts).sort_index(); w=w[~w.index.duplicated()].dropna()
u=-w.ws*np.sin(np.radians(w.wd)); v=-w.ws*np.cos(np.radians(w.wd))
g=pd.DataFrame({"u":u,"v":v,"ws":w.ws}).resample("D").mean(); g[w.ws.resample("D").count()<16]=np.nan
dirn=(np.degrees(np.arctan2(-g.u,-g.v))+360)%360; cons=np.hypot(g.u,g.v)/g.ws
cat=pd.read_csv("out_catalogo.csv",index_col=0)
def run(WET,rot,cmin):
    a=(dirn-rot)%360
    sec=pd.Series(np.select([a.isna()|(cons<cmin),(a>=270)|(a<45),a<180],["x","NW","ESE"],"SW"),index=a.index).replace("x",np.nan)
    rows=[]
    for y in range(2010,2027):
        idx=pd.date_range(f"{y-1}-12-01",f"{y}-03-31"); p=pE.reindex(idx); s=sec.reindex(idx); wet=p>=WET
        es=[]
        for k,gr in wet.groupby((wet!=wet.shift()).cumsum()):
            if gr.iloc[0]:
                ss=s.loc[gr.index].dropna()
                if len(ss): es.append(ss.mode().iloc[0])
        es2=[e for e in es if e in("NW","ESE")]  # variante: ignorar episodios SW
        rows.append(dict(season=y,Pt=p.sum(),tr=sum(1 for x,z in zip(es,es[1:]) if {x,z}=={"NW","ESE"}),
                         tr2=sum(1 for x,z in zip(es2,es2[1:]) if x!=z)))
    T=pd.DataFrame(rows).set_index("season").join(cat.E_acum)
    out=[]
    for m in ["tr","tr2"]:
        r=T[[m,"E_acum","Pt"]].rank()
        ra=r[m]-np.polyval(np.polyfit(r.Pt,r[m],1),r.Pt); rb=r.E_acum-np.polyval(np.polyfit(r.Pt,r.E_acum,1),r.Pt)
        out+= [stats.spearmanr(T[m],T.E_acum)[0], *stats.pearsonr(ra,rb)]
    return out
res=[]
for WET in [1,2,3,5]:
    for rot in [-22.5,0,22.5]:
        for cmin in [0,0.5]:
            r=run(WET,rot,cmin); res.append([WET,rot,cmin,*r])
R=pd.DataFrame(res,columns=["WET","giro","cons_min","rho_tr","parc_tr","p_tr","rho_tr2","parc_tr2","p_tr2"])
print(R.round(2).to_string()); R.to_csv("out_sens_transiciones.csv",index=False)
print("\nparcial tr: mediana %.2f, rango [%.2f, %.2f], p<0.05 en %d/%d"%(R.parc_tr.median(),R.parc_tr.min(),R.parc_tr.max(),(R.p_tr<0.05).sum(),len(R)))
print("parcial tr2: mediana %.2f, rango [%.2f, %.2f], p<0.05 en %d/%d"%(R.parc_tr2.median(),R.parc_tr2.min(),R.parc_tr2.max(),(R.p_tr2<0.05).sum(),len(R)))
