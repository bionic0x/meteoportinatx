"""Device screen language, persistence and safety text in a real browser."""
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
const [chrome, app, sensors]=process.argv.slice(1);
(async()=>{
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();
  await page.route('**/*',route=>{
   const url=route.request().url();
   if(url==='http://meteo.test/dispositivo/')return route.fulfill({contentType:'text/html',body:fs.readFileSync(app,'utf8')});
   if(url.endsWith('/device_sensors.js'))return route.fulfill({contentType:'text/javascript',body:fs.readFileSync(sensors,'utf8')});
   if(url.endsWith('/public_fetch.js'))return route.fulfill({contentType:'text/javascript',body:'window.meteoLoadPart=async()=>({data:null,source:"snapshot"});'});
   if(url.endsWith('/public_config.js'))return route.fulfill({contentType:'text/javascript',body:''});
   return route.abort();
  });
  await page.goto('http://meteo.test/dispositivo/');
  await page.selectOption('#device-language','en');
  assert.equal(await page.locator('html').getAttribute('lang'),'en');
  assert.equal(await page.locator('#haptic-toggle').textContent(),'Enable vibration');
  assert.match(await page.locator('.notice').textContent(),/not a push alert or continuous monitoring/);
  assert.match(await page.locator('#sensors').textContent(),/Pressure/);
  await page.reload();
  assert.equal(await page.locator('#device-language').inputValue(),'en');
  await page.selectOption('#device-language','es');
  assert.equal(await page.locator('#haptic-toggle').textContent(),'Activar vibración');
  assert.match(await page.locator('.notice').textContent(),/no significa calma/);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
'''

class DeviceLanguageBrowser(unittest.TestCase):
    def test_switch_persists_and_preserves_warning(self):
        chrome = require_browser(self)
        proc = subprocess.run([NODE, '-e', JS, chrome, str(ROOT / 'src/device_app.html'),
                               str(ROOT / 'src/device_sensors.js')], cwd=ROOT,
                              capture_output=True, text=True, timeout=40, env=os.environ.copy())
        self.assertEqual(proc.returncode, 0, proc.stderr)
