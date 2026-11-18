"""Unittest: format, numeric, and negative validation checks on wholly synthetic fixture."""
import json, tempfile, unittest, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from electron_pipeline import convert
from check_v01_local import validate

class TestConversion(unittest.TestCase):
    def setUp(self):
        self.src=json.loads((ROOT/'examples'/'synthetic_demo_input.json').read_text())
    def run_convert(self,obj):
        with tempfile.TemporaryDirectory() as d:
            i=Path(d)/'in.json';o=Path(d)/'out.json';i.write_text(json.dumps(obj));convert(i,o)
            return json.loads(o.read_text())
    def test_v01(self):
        x=self.run_convert(self.src)
        self.assertEqual(validate(x),[])
        self.assertEqual(x['quality']['status'],'quarantined')
        self.assertTrue(x['synthetic'])
        self.assertEqual(x['rbe'],1.0)
        self.assertEqual(x['metrics'][0]['pct_rx'],80)
        self.assertEqual(x['dvh'][0]['volume_pct'][0],100)
    def test_reject_nonmonotonic_dvh(self):
        self.src['structures'][0]['dvh'][2][1]=101
        with self.assertRaises(ValueError):self.run_convert(self.src)
    def test_reject_wrong_id(self):
        self.src['plan_id']='PATIENT_A'
        with self.assertRaises(ValueError):self.run_convert(self.src)
    def test_reject_missing_prescription(self):
        self.src['prescription_Gy']=None
        with self.assertRaises(ValueError):self.run_convert(self.src)
    def test_reject_malformed_quality(self):
        self.src['quality']={'status':'quarantined','issues':[]}
        with self.assertRaises(ValueError):self.run_convert(self.src)
    def test_reject_invalid_metric(self):
        self.src['structures'][0]['metrics_Gy']['D95']=float('nan')
        with self.assertRaises(ValueError):self.run_convert(self.src)
if __name__=='__main__':unittest.main(verbosity=2)
