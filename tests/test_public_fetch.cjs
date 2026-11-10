// Browser-like JS contract tests for the per-domain loader. No network calls.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const JS = fs.readFileSync(path.join(__dirname,'../src/public_fetch.js'),'utf8');
const backend = 'https://meteoportinatx-backend-free.onrender.com';
const gen1 = '20261110T130000Z-aabbccddeeff';
const gen2 = '20261110T130500Z-112233445566';

function response(part, origin, {generation=gen1, freshness='fresh', expose=true, error=false}={}) {
  return {
    ok:!error, status:error?503:200,
    headers:{get(k){
      if (origin==='backend' && !expose) return null; // actual browser would hide non-exposed headers
      if (k==='X-Meteo-Snapshot') return generation;
      if (k==='X-Meteo-Freshness') return freshness;
      return null;
    }},
    async json(){return {part, origin, issued:generation};}
  };
}
async function runCase(label, mapping, shouldSource, shouldOrigin) {
  const requested=[];
  const sandbox={window:{METEO_BACKEND_URL:backend},Set,Promise,Error,Object,
    fetch:async url=>{
      requested.push(url);
      const part=(/\/([a-z_]+)\.json$/.exec(url)||[])[1];
      const origin=url.startsWith(backend+'/')?'backend':'static';
      const options=origin==='backend'?(mapping[part]||{}):{};
      return response(part,origin,options);
    }
  };
  vm.runInNewContext(JS,sandbox,{filename:'public_fetch.js'});
  const packet=await sandbox.window.meteoLoadDomain('portinatx',['core','radar','series'],'api/');
  assert.equal(packet.source,shouldSource,label);
  assert.deepEqual(Object.values(packet.parts).map(v=>v.origin),[shouldOrigin,shouldOrigin,shouldOrigin],label);
  if (shouldSource==='backend') assert.equal(requested.length,3,label);
  else assert.equal(requested.filter(v=>v.startsWith('api/')).length,3,label);
  return requested;
}
(async()=>{
  await runCase('coherent live generation',{},'backend','backend');
  await runCase('midflight generation changes -> all static',
    {core:{generation:gen1},radar:{generation:gen2},series:{generation:gen1}},
    'snapshot-fallback','static');
  await runCase('CORS non-exposed freshness -> all static',
    {core:{expose:false}},'snapshot-fallback','static');
  await runCase('stale source -> all static',
    {series:{freshness:'stale'}},'snapshot-fallback','static');
  await runCase('one provider 503 -> all static',
    {radar:{error:true}},'snapshot-fallback','static');
  await runCase('no generation header -> all static',
    {core:{generation:''}},'snapshot-fallback','static');
  const sandbox={window:{METEO_BACKEND_URL:''},fetch:async()=>{throw Error('no fetch expected')}};
  vm.runInNewContext(JS,sandbox);
  await assert.rejects(()=>sandbox.window.meteoLoadDomain('pirineo',['../../private'],'api/'),/invalid domain or parts/);
  console.log('7 browser-bridge contract checks OK (whole-domain coherence, CORS, stale and failover)');
})().catch(e=>{console.error(e);process.exitCode=1});
