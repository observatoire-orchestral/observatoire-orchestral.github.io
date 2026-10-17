import tempfile
import unittest
from pathlib import Path
from classification import prepare
from phase2_audit import report

class Phase2Tests(unittest.TestCase):
    def test_multi_organisation(self):
        item = prepare({'title': 'Concert commun de l’ONPL et Angers Nantes Opéra'})
        self.assertEqual(set(item['organizations']), {'ONPL', 'Angers Nantes Opéra'})
    def test_single_organisation(self):
        self.assertEqual(prepare({'title':'Concert ONPL'})['organizations'], ['ONPL'])
    def test_no_venue_inference(self):
        self.assertEqual(prepare({'title':'Concert au Théâtre Graslin'})['organizations'], [])
    def test_read_only_report(self):
        rows = [{'id':'1','title':'Concert de l’ONPL et Angers Nantes Opéra',
                 'summary':'','url':'https://a.test/1','source':'Example','category':'Autres',
                 'review_status':'validated','organizations':['ONPL']},
                {'id':'2','title':'Concert de l’ONPL et Angers Nantes Opéra',
                 'summary':'','url':'https://a.test/2','source':'Example','category':'Autres',
                 'review_status':'validated','organizations':['ONPL']}]
        with tempfile.TemporaryDirectory() as d:
            count, duplicates = report(rows,d)
            self.assertEqual(count,2)
            self.assertEqual(duplicates,2)
            self.assertTrue((Path(d)/'classification_candidates.csv').exists())

if __name__ == '__main__': unittest.main()
