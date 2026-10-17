import unittest
from classification import classify,organisations,prepare
class Tests(unittest.TestCase):
 def test_keep_review(self): self.assertEqual(classify('Orchestre de Paris à la Philharmonie','','Critique musicale'),'Critique musicale')
 def test_source_review(self): self.assertEqual(classify('Orphée et Eurydice','','Autres','ResMusica'),'Critique musicale')
 def test_explicit_review(self): self.assertEqual(classify("CRITIQUE - L'Orchestre de Paris",'','Autres'),'Critique musicale')
 def test_keep_governance(self): self.assertEqual(classify('Orchestre national de Lille','', 'Gouvernance'),'Gouvernance')
 def test_budget(self): self.assertEqual(classify('Baisse des subventions de l’orchestre'),'Budget et subventions')
 def test_no_venue_inference(self): self.assertEqual(organisations('Concert au Théâtre Graslin'),[])
 def test_distinct(self): self.assertEqual(organisations('ONPL et Angers Nantes Opéra'),['ONPL','Angers Nantes Opéra'])
 def test_no_auto_approval(self):
  a=prepare({'title':'Concert ONPL','review_status':'validated','reviewed_by':'123'})
  self.assertEqual(a['review_status'],'unreviewed');self.assertNotIn('reviewed_by',a)
 def test_booking_not_review(self): self.assertNotEqual(classify('Billetterie de la saison','','Autres','Bachtrack'),'Critique musicale')
if __name__=='__main__':unittest.main()
