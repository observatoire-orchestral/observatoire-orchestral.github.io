import unittest
from reclassify_history import candidate

class HistoryTests(unittest.TestCase):
 def row(self,title,category='Autres',**kwargs):
  return {'id':'test-id','title':title,'summary':'','source':'Radio Classique','url':'https://example.com/a',
          'orchestra':'Secteur orchestral français','category':category,'review_status':'unreviewed','reviewed_by':None,**kwargs}
 def test_governance(self):
  p=candidate(self.row('Orchestre Philharmonique de Strasbourg : Aziz Shokhakimov prolongé à la direction musicale'))
  self.assertEqual(p['action'],'reclassify');self.assertEqual(p['new_category'],'Gouvernance')
 def test_budget(self):
  p=candidate(self.row('Les orchestres de Radio France trop chers ? Les musiciens se défendent'))
  self.assertEqual(p['new_category'],'Budget et subventions')
 def test_metaphor_flag_only(self):
  p=candidate(self.row('Les maires jouent l’orchestre du Titanic avant l’iceberg budgétaire'))
  self.assertEqual(p['action'],'flag_irrelevant')
 def test_protect_reviewed(self):
  r=self.row('Orchestre Philharmonique de Strasbourg : Aziz Shokhakimov prolongé à la direction musicale')
  r['reviewed_by']='some-user'
  self.assertIsNone(candidate(r))
 def test_no_change(self):
  r=self.row('Orchestre Philharmonique de Strasbourg : Aziz Shokhakimov prolongé à la direction musicale','Gouvernance')
  r['orchestra']='Orchestre philharmonique de Strasbourg'
  self.assertIsNone(candidate(r))
if __name__=='__main__':unittest.main()
