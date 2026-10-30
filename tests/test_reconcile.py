import csv
import tempfile
import unittest
from pathlib import Path
from src.reconcile import reconcile

class ReconcileTest(unittest.TestCase):
    def test_one_encounter_multiple_cpts_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d)/'ehr.csv', Path(d)/'db.csv'
            a.write_text('Patient Name,Provider Name,Date of Service,CPT Code\nAva  Smith,Dr Lee,09/24/2024,97110\nAva Smith,Dr Lee,09/24/2024,97140\nBen Jones,Dr Lee,09/25/2024,NORCM\n')
            b.write_text('Patient Name,Provider Name,from_date_range,cpt_codes\nava smith,dr lee,2024-09-24,"{97110,97140}"\n')
            s, missing = reconcile(a,b)
            self.assertEqual((s['ehr_unique'], s['matched'], s['missing'], s['norcm_missing']), (2,1,1,1))
            self.assertEqual(missing[0]['Patient Name'], 'ben jones')

if __name__ == '__main__': unittest.main()
