import unittest
from classification import classify, prepare
from relevance import assess

class RealWorldEditorialTests(unittest.TestCase):
    def accepted(self, title, source='Radio Classique'):
        self.assertTrue(assess(title, source=source).accept, title)
    def rejected(self, title, source='Bachtrack'):
        self.assertFalse(assess(title, source=source).accept, title)

    def test_relevance_true(self):
        for title in [
            'Orchestre Philharmonique de Strasbourg : Aziz Shokhakimov prolongé à la direction musicale et artistique',
            'Le maestro Enrique Mazzola fait ses adieux à l’Orchestre national d’Île-de-France',
            '« Je reviendrai » : Marc Feldman quitte l’Orchestre national de Bretagne',
            'Les orchestres de Radio France trop chers ? Les musiciens se défendent',
            'Le sacre mahlérien d’Aziz Shokhakimov et de l’Orchestre philharmonique de Strasbourg',
            'Alexandra Lacroix, nouvelle directrice d’Angers Nantes Opéra',
            'La Création sans surprise du Concert de la Loge au TCE',
        ]: self.accepted(title)

    def test_relevance_false(self):
        for title in [
            'Les maires jouent l’orchestre du Titanic avant d’affronter l’iceberg budgétaire',
            'Franck Happi, nouveau chef d’orchestre des championnats à la FECAFOOT',
            'Étiquette : Debora Waldman',
            'Anna Vinnitskaya & l’Orchestre philharmonique de Strasbourg sur myCANAL : résumé de l’épisode',
            'Listing and tickets: Frank Beermann / Adam Laloum | Halle aux grains',
            'Daniil Trifonov brings revelatory Russian rarities to Carnegie Hall',
            'Intimate colossus: Daniil Trifonov plays Brahms with the Rotterdam Philharmonic',
            'Un été avec Lucie Leguay',
        ]: self.rejected(title)

    def test_classification(self):
        cases = [
            ('Orchestre Philharmonique de Strasbourg : Aziz Shokhakimov prolongé à la direction musicale', 'Gouvernance','Radio Classique'),
            ('Le maestro Enrique Mazzola fait ses adieux à l’Orchestre national d’Île-de-France','Gouvernance','Le Figaro'),
            ('Marc Feldman quitte l’Orchestre national de Bretagne','Gouvernance','Ouest-France'),
            ('Les orchestres de Radio France trop chers ? Les musiciens se défendent','Budget et subventions','franceinfo'),
            ('Le sacre mahlérien d’Aziz Shokhakimov et de l’Orchestre philharmonique de Strasbourg','Critique musicale','Bachtrack'),
            ('La Création sans surprise du Concert de la Loge au TCE','Critique musicale','Bachtrack'),
            ('Alexandra Lacroix, nouvelle directrice d’Angers Nantes Opéra','Gouvernance','Essentiel media'),
        ]
        for title, category, source in cases:
            with self.subTest(title=title): self.assertEqual(classify(title,source=source),category)

    def test_unreviewed_and_no_editorial_overwrite(self):
        item=prepare({'title':'Orchestre philharmonique de Strasbourg : directeur musical nommé', 'source':'Radio Classique', 'url':'https://example.org/one'})
        self.assertEqual(item['review_status'],'unreviewed')
        self.assertEqual(item['orchestra'],'Orchestre philharmonique de Strasbourg')
        self.assertNotIn('reviewed_by',item)

if __name__=='__main__': unittest.main()
