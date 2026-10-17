import unittest
from classification import classify, organisations, prepare
from monitoring_queries import ORCHESTRAS, SECTOR_QUERIES
class EditorialTests(unittest.TestCase):
 def test_working_conditions(self): self.assertEqual(classify('Orchestre : santé au travail des musiciens'),'Conditions de travail')
 def test_finance(self): self.assertEqual(classify('Orchestre : désengagement financier de la région'),'Budget et subventions')
 def test_strike(self): self.assertEqual(classify('Orchestre : préavis de grève'),'Mobilisation et grève')
 def test_jobs(self): self.assertEqual(classify('Orchestre : postes vacants'),'Emploi et recrutement')
 def test_governance(self): self.assertEqual(classify('Orchestre : chambre régionale des comptes'),'Gouvernance')
 def test_review(self): self.assertEqual(classify('Un concert remarquable',source='Bachtrack'),'Critique musicale')
 def test_not_ticketing(self): self.assertNotEqual(classify('Ouverture de la billetterie',source='Bachtrack'),'Critique musicale')
 def test_keep_uncertain_review(self): self.assertEqual(classify('Concert de printemps',suggested='Critique musicale'),'Critique musicale')
 def test_onpl_not_opera(self): self.assertEqual(organisations('Angers Nantes Opéra : nouvelle saison'),['Angers Nantes Opéra'])
 def test_not_venue(self): self.assertEqual(organisations('Théâtre Graslin : soirée musicale'),[])
 def test_unreviewed(self): self.assertEqual(prepare({'title':'Orchestre : grève','review_status':'validated'})['review_status'],'unreviewed')
 def test_coverage(self): self.assertGreaterEqual(len(ORCHESTRAS),25)
 def test_queries(self): self.assertGreaterEqual(len(SECTOR_QUERIES),15)
if __name__=='__main__': unittest.main()
