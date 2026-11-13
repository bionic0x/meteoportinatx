"""The visible laboratory cannot bypass the atmospheric core's evidence gates."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[1]/'src')]
from browser_support import NODE,ROOT,require_browser
from atmospheric_core import COMPOSITES,composite

class AtmosphericInterface(unittest.TestCase):
    def test_lab_preserves_missing_components_and_unverified_vertical_sign(self):
        chrome=require_browser(self)
        row={'cape':1000,'tcwv':30,'w700':.1,'shr06':15,'cin':30}
        cases=[{'row':row,'up':True},{'row':row,'up':False}]
        cases += [{'row':{**row,key:None},'up':True} for key in row]
        for case in cases:
            case['expected']=composite('icc',case['row'],upward_verified=case['up'])['value']
        js=r'''
const {chromium}=require('playwright'),fs=require('fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.argv[1],headless:true,args:['--no-sandbox']});
 try {
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const html=fs.readFileSync(process.argv[2],'utf8');
 await page.route('**/*',r=>r.request().url()==='http://meteo.test/'?r.fulfill({contentType:'text/html',body:html}):r.abort());
 await page.goto('http://meteo.test/');
 const payload=JSON.parse(process.argv[3]);
 const results=await page.evaluate(({cases,spec})=>cases.map(c=>compositeJS('icc',c.row,spec.weights,spec,c.up)),payload);
 for(let i=0;i<results.length;i++){
  const expected=payload.cases[i].expected;
  if(expected===null)assert.equal(results[i].value,null);else assert.ok(Math.abs(results[i].value-expected)<.0006);
 }
 const missing=await page.evaluate(spec=>fromComps({inestabilidad:.5,humedad:.5,ascenso:null,organizacion:.5},spec.weights,.2,spec),payload.spec);
 assert.equal(missing,null);
 assert.ok(!html.includes('Si falta un componente, el valor se calcula con los demás.'));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
'''
        result=subprocess.run([NODE,'-e',js,chrome,str(ROOT/'src/portinatx_app.html'),
                               json.dumps({'cases':cases,'spec':COMPOSITES['icc']})],cwd=ROOT,
                              capture_output=True,text=True,timeout=40)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
