"""Regression: RSS normalisation must not reference removed TOPICS."""
import unittest
from unittest.mock import patch

class CollectHotfixTests(unittest.TestCase):
    def test_normalize_without_topics(self):
        with patch.dict('os.environ', {'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_SERVICE_ROLE_KEY': 'test'}):
            import collect
            item = collect.normalize({'title': 'Orchestre : grève', 'link': 'https://example.org/article', 'summary': 'Mobilisation'}, 'ONPL', 'Example')
            self.assertEqual(item['category'], 'Autres')
            self.assertEqual(item['review_status'], 'unreviewed')
            from classification import prepare
            self.assertEqual(prepare(item)['category'], 'Mobilisation et grève')

if __name__ == '__main__':
    unittest.main()
