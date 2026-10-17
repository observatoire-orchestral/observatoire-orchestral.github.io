import unittest
from classification import classify, organisations, prepare, SECTOR

class ClassificationTests(unittest.TestCase):
    def test_budget(self):
        self.assertEqual(classify('Le budget de l’orchestre baisse'), 'Budget et subventions')
    def test_employment(self):
        self.assertEqual(classify('Suppression de postes de musiciens'), 'Emploi et recrutement')
    def test_conditions(self):
        self.assertEqual(classify('Accord sur les conditions de travail'), 'Conditions de travail')
    def test_governance(self):
        self.assertEqual(classify('Nomination du directeur général'), 'Gouvernance')
    def test_strike(self):
        self.assertEqual(classify('Préavis de grève à l’orchestre'), 'Mobilisation et grève')
    def test_review(self):
        self.assertEqual(classify('Critique du concert symphonique'), 'Critique musicale')
    def test_event_not_review(self):
        self.assertNotEqual(classify('Event listing: concert', suggested='Critique musicale'), 'Critique musicale')
    def test_no_venue_inference(self):
        self.assertEqual(organisations('Orphée au Théâtre Graslin'), [])
    def test_named(self):
        self.assertEqual(organisations('L’ONPL donne un concert'), ['ONPL'])
    def test_multiple(self):
        self.assertEqual(prepare({'title': 'ONPL et Angers Nantes Opéra', 'review_status': 'validated'})['orchestra'], SECTOR)
    def test_automatic_unreviewed(self):
        a = prepare({'title': 'ONPL : grève', 'review_status': 'validated', 'reviewed_by': 'person'})
        self.assertEqual(a['review_status'], 'unreviewed')
        self.assertNotIn('reviewed_by', a)

if __name__ == '__main__':
    unittest.main()
