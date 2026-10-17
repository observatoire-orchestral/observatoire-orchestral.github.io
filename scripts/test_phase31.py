import unittest
from classification import classify, clearly_irrelevant

class QualityTests(unittest.TestCase):
    def test_budget(self):
        self.assertEqual(classify('Les orchestres de Radio France trop chers ? Les musiciens se défendent',source='franceinfo'),'Budget et subventions')
    def test_director(self):
        self.assertEqual(classify("Alexandra Lacroix, nouvelle directrice d'Angers Nantes Opéra"),'Gouvernance')
    def test_renewal(self):
        self.assertEqual(classify("Aziz Shokhakimov renouvelé à la tête de l'Orchestre philharmonique de Strasbourg"),'Gouvernance')
    def test_ticket_excluded(self):
        title='Listing and tickets: Frank Beermann / Adam Laloum | Halle aux grains'
        self.assertTrue(clearly_irrelevant(title))
        self.assertNotEqual(classify(title,source='Bachtrack',url='https://bachtrack.com/foo'),'Critique musicale')
    def test_archive_excluded(self):
        self.assertTrue(clearly_irrelevant('Archives des Augustin Dumay'))
    def test_heritage_not_review(self):
        self.assertNotEqual(classify('Une maquette spectaculaire du Palais Garnier rejoint le parcours de visite',source='ResMusica'),'Critique musicale')
    def test_source_not_enough(self):
        self.assertNotEqual(classify('Un été avec Lucie Leguay',source='Forum Opéra'),'Critique musicale')
    def test_actual_review(self):
        self.assertEqual(classify('Alexandre Desplat et l’Orchestre de Paris : notre critique',source='Télérama'),'Critique musicale')
    def test_labor_priority(self):
        self.assertEqual(classify('Grève des musiciens à l’orchestre : notre critique',source='ResMusica'),'Mobilisation et grève')
    def test_preserve_ambiguous(self):
        self.assertFalse(clearly_irrelevant('Ben Glassberg à l’Opéra de Rouen, un chef d’orchestre prodige en quête d’harmonie'))
    def test_rugby(self):
        self.assertTrue(clearly_irrelevant('Cinéma et musique classique - ASM Rugby'))
    def test_equine(self):
        self.assertTrue(clearly_irrelevant('Le Jumping de Bordeaux prépare une belle soirée entre création équestre et dressage'))
if __name__=='__main__': unittest.main()
