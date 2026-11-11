"""Shared zone report: real offline browser interaction, optional dependencies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
import zone_engine
import zone_report
from zone_fixtures import provider


class ZoneReportBrowser(unittest.TestCase):
    def test_filter_mobile_layout_and_no_marine_in_mountains(self):
        if not shutil.which('node') or not shutil.which('chromium'):
            self.skipTest('Node and Chromium required')
        if subprocess.run(['node','-e',"require('playwright')"],capture_output=True).returncode:
            self.skipTest('Playwright Node module required')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            profile = zone_engine.load_profile('pirineo')
            profile['name'] = 'DEMOSTRACIÓN SINTÉTICA'
            zone_engine.collect(profile,root/'pack.zip',getter=lambda url:provider(url,partial_snow=True))
            zone_report.write_report(root/'pack.zip',root/'report.html')
            code = r'''
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.argv[1],headless:true,args:['--no-sandbox']});
 try {
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.argv[2]);
 if(await page.locator('h3').filter({hasText:/^Mar$/}).count()) throw Error('Marine section in inland zone');
 if(!await page.getByText('Sin datos suficientes',{exact:true}).count()) throw Error('Missing data hidden');
 await page.selectOption('#point-filter','masella');
 const visible=page.locator('section.point:visible');
 if(await visible.count()!==1||await visible.getAttribute('data-point')!=='masella') throw Error('Point filter failed');
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 if(overflow) throw Error('Page overflows mobile viewport');
 await page.selectOption('#point-filter','all');
 if(await page.locator('section.point:visible').count()!==3) throw Error('All-points filter failed');
 if(errors.length) throw Error(errors.join(';'));
 console.log('offline report: filtering, missing data, inland scope, mobile width PASS');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
'''
            result = subprocess.run(['node','-e',code,shutil.which('chromium'),(root/'report.html').as_uri()],
                                    capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
