import unittest
from classification import classify, clearly_irrelevant, prepare
class QualityTests(unittest.TestCase):
 def test_governance(self):
  self.assertEqual(classify("Alexandra Lacroix, nouvelle directrice d'Angers Nantes Opéra"), 'Gouvernance')
 def test_budget(self):
  self.assertEqual(classify('Les orchestres de Radio France trop chers ? Les musiciens se défendent'), 'Budget et subventions')
 def test_ticket_exclusion(self):
  self.assertTrue(clearly_irrelevant('Listing and tickets: Frank Beermann / Adam Laloum'))
 def test_archive_exclusion(self):
  self.assertTrue(clearly_irrelevant('Archives des Augustin Dumay'))
 def test_source_not_enough(self):
  self.assertNotEqual(classify('Une maquette spectaculaire du Palais Garnier rejoint le parcours de visite',source='ResMusica'), 'Critique musicale')
 def test_preserve_review_uncertain(self):
  self.assertNotEqual(classify('Un été avec Lucie Leguay',suggested='Critique musicale'), 'Critique musicale')
 def test_orchestra(self):
  self.assertEqual(prepare({'title':'L’Orchestre de Paris annonce une saison','summary':'','orchestra':'Secteur orchestral français'})['orchestra'], 'Orchestre de Paris')
 def test_review_keyword(self):
  self.assertEqual(classify('Notre critique du concert de l’Orchestre de Paris'), 'Critique musicale')
 def test_labour(self):
  self.assertEqual(classify('Grève des musiciens de l’orchestre'), 'Mobilisation et grève')
 def test_work(self):
  self.assertEqual(classify('Conditions de travail des musiciens'), 'Conditions de travail')
 def test_no_reviewer_fields(self):
  self.assertNotIn('reviewed_by',prepare({'title':'Concert Orchestre de Paris','reviewed_by':'x'}))
if __name__=='__main__': unittest.main()
