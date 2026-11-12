"""Hub language and stored preference apply to content and data status."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_support import NODE, ROOT, require_browser  # noqa: E402

JS = r'''
const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const [chrome,file]=process.argv.slice(1);
(async()=>{
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();
  const html=fs.readFileSync(file,'utf8');
  await page.route('**/*',route=>{
   const url=route.request().url();
   if(url==='http://meteo.test/') return route.fulfill({contentType:'text/html',body:html});
   if(url.endsWith('/api/core.json')) return route.fulfill({json:{issued:new Date().toISOString()}});
   return route.abort();
  });
  await page.goto('http://meteo.test/');
  await page.selectOption('#language','en');
  assert.equal(await page.locator('html').getAttribute('lang'),'en');
  assert.match(await page.locator('h1').innerText(),/Two territories/);
  await page.waitForFunction(()=>document.querySelector('#port-status').textContent.includes('Latest cycle'));
  await page.reload();
  assert.equal(await page.locator('#language').inputValue(),'en');
  await page.selectOption('#language','es');
  assert.equal(await page.locator('html').getAttribute('lang'),'es');
  assert.match(await page.locator('h1').innerText(),/Dos territorios/);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
'''

class HubLanguageBrowser(unittest.TestCase):
    def test_hub_language_persists_and_translates_status(self):
        chrome=require_browser(self)
        proc=subprocess.run([NODE,'-e',JS,chrome,str(ROOT/'src/nowcast_hub.html')],
                            cwd=ROOT,capture_output=True,text=True,timeout=40,env=os.environ.copy())
        self.assertEqual(proc.returncode,0,proc.stderr)
