/* Local-only, experimental device measurements and opt-in vibration. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.MeteoDevice=api;})(typeof window!=='undefined'?window:null,function(){
'use strict';
const ranges={presion:[300,1100,300000],temperatura:[-80,80,300000],humedad:[0,100,300000],luz:[0,200000,15000],campo_magnetico:[0,5000,15000],movimiento:[0,200,15000],rumbo:[0,360,15000],altitud:[-500,9000,120000]};
const labels={presion:'Presión',temperatura:'Temperatura',humedad:'Humedad',luz:'Luz',campo_magnetico:'Campo magnético',movimiento:'Movimiento',rumbo:'Rumbo',altitud:'Altitud'};
const units={presion:'hPa',temperatura:'°C',humedad:'%',luz:'lx',campo_magnetico:'µT',movimiento:'m/s²',rumbo:'°',altitud:'m'};
function createStore(now=()=>Date.now()){
 const data={},series={},rejected={};
 function push(k,v,t=now(),source='puente-nativo'){
  const r=ranges[k],n=now();if(!r)return {ok:false,reason:'canal desconocido'};
  if(typeof v!=='number'||!Number.isFinite(v)||v<r[0]||v>r[1]||typeof t!=='number'||!Number.isFinite(t)||t>n+5000||n-t>=r[2]||(data[k]&&t<=data[k].t)){rejected[k]=(rejected[k]||0)+1;return {ok:false,reason:'lectura no válida, antigua o desordenada'};}
  data[k]={value:v,t,source};const a=series[k]||(series[k]=[]);if(!a.length||t-a[a.length-1].t>=10000)a.push({t,value:v});while(a.length>1081||a.length&&t-a[0].t>10800000)a.shift();return {ok:true};
 }
 function read(k){const x=data[k];if(!x)return {estado:'UNKNOWN',value:null,rechazos:rejected[k]||0};return {estado:now()-x.t>=ranges[k][2]?'STALE':'MEASURED',value:now()-x.t>=ranges[k][2]?null:x.value,t:x.t,source:x.source,rechazos:rejected[k]||0};}
 return {push,read,series:k=>(series[k]||[]).slice()};
}
function pressureTendency(series,now=Date.now(),alt=[]){
 const a=series.filter(x=>Number.isFinite(x.t)&&Number.isFinite(x.value)&&x.t<=now&&x.t>=now-10800000).sort((x,y)=>x.t-y.t);const unknown=reason=>({estado:'UNKNOWN',reason});
 if(a.length<6||a[a.length-1].t-a[0].t<1800000||now-a[a.length-1].t>=300000)return unknown('registro insuficiente o antiguo');
 if(a.some((x,i)=>i&&x.t-a[i-1].t>1200000))return unknown('hueco superior a 20 min');
 const al=alt.filter(x=>Number.isFinite(x.value)&&x.t>=a[0].t&&x.t<=now);if(al.length>1&&Math.max(...al.map(x=>x.value))-Math.min(...al.map(x=>x.value))>25)return {estado:'NO_COMPARABLE',reason:'cambio de altitud superior a 25 m'};
 const xx=a.map(x=>(x.t-a[0].t)/3600000),xm=xx.reduce((x,y)=>x+y)/a.length,ym=a.reduce((x,y)=>x+y.value,0)/a.length,den=xx.reduce((s,x)=>s+(x-xm)**2,0);if(!den)return unknown('horas insuficientes');
 const slope=a.reduce((s,x,i)=>s+(xx[i]-xm)*(x.value-ym),0)/den,mag=Math.abs(slope*3);return {estado:'OK',hpa_h:slope,clase:mag<1.6?'estable':mag<3.6?'lento':mag<6?'rapido':'muy_rapido',vertical:al.length>1?'sin cambio detectado':'UNKNOWN'};
}
const ranks={quiet:0,watch:1,alert:2,alarm:3};
function signalFromCore(core,domain,now=Date.now()){
 if(!core||!['portinatx','pirineo'].includes(domain)||typeof core.issued!=='string'||!/(?:Z|[+-]\d\d:\d\d)$/.test(core.issued))return 'unknown';const age=now-Date.parse(core.issued);if(!Number.isFinite(age)||age < -5000||age>(domain==='portinatx'?3600000:21600000))return 'unknown';let found=[];
 if(domain==='portinatx'){
  if(core.official&&core.official.verificado===true&&Object.hasOwn(ranks,core.official.level_now))found.push(core.official.level_now);
  for(const h of Object.values(core.hazard||{}))if(h&&h.estado==='OBSERVED'&&Object.hasOwn(ranks,h.nivel))found.push(h.nivel);
  if(core.precaution&&core.precaution.insufficient===false&&Object.hasOwn(ranks,core.precaution.level))found.push(core.precaution.level);
 }else if(core.fuentes&&/^ok\b/i.test(core.fuentes.avisos||'')&&Array.isArray(core.avisos)){
  found.push('quiet');for(const w of core.avisos){if(!w||typeof w!=='object'||w.error)return 'unknown';const validTime=x=>typeof x==='string'&&/(?:Z|[+-]\d\d:\d\d)$/.test(x)&&Number.isFinite(Date.parse(x));if(!validTime(w.desde)||!validTime(w.hasta))return 'unknown';const start=Date.parse(w.desde),end=Date.parse(w.hasta);if(end<start)return 'unknown';if(start<=now&&now<=end){const c=String(w.color||w.nivel||'').toLowerCase();found.push(/rojo|red/.test(c)?'alarm':/naranja|orange/.test(c)?'alert':'watch');}}
 }
 return found.length?found.reduce((a,b)=>ranks[b]>ranks[a]?b:a):'unknown';
}
function createHaptics(vibrate,now=()=>Date.now()){
 let enabled=false,previous=null,lastLost=-Infinity;const patterns={watch:[120],alert:[180,100,180],alarm:[250,100,250,100,250],lost:[70,100,70]};
 return {enable(v){enabled=!!v;previous=null;},update(level){if(!enabled||!(level==='unknown'||Object.hasOwn(ranks,level)))return;let p=null;if(previous!==null&&level==='unknown'&&previous!=='unknown'&&now()-lastLost>=60000){p='lost';lastLost=now();}else if(previous!==null&&level!=='unknown'&&previous!=='unknown'&&ranks[level]>ranks[previous])p=level;previous=level;if(p&&typeof vibrate==='function')vibrate(patterns[p]);},test(){if(enabled&&typeof vibrate==='function')return vibrate(patterns.watch);return false;},reset(){previous=null;}};
}
return Object.freeze({ranges,labels,units,createStore,pressureTendency,signalFromCore,createHaptics});
});
