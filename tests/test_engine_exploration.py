"""Verify the independent graph/vector dataset against its source purchase rows."""
from collections import Counter
import json
import math
import random
import unittest

from playground.catalog import build_catalog
from playground.exploration import build_exploration


class ExplorationTests(unittest.TestCase):
    def test_deterministic_independent_catalog_extension(self):
        before = random.getstate()
        exploration = build_exploration()
        self.assertEqual(before, random.getstate())
        self.assertEqual(exploration, build_exploration())
        self.assertEqual(exploration, build_catalog()['exploration'])
        self.assertEqual(exploration['seed'], 42)
        self.assertIn('not joined', exploration['description'])
        self.assertEqual(set(exploration), {'seed', 'description', 'dimensions', 'products', 'customers', 'purchases', 'graph'})
        json.dumps(exploration, allow_nan=False)

    def test_population_identifiers_and_references(self):
        data = build_exploration()
        self.assertEqual((len(data['products']), len(data['customers']), len(data['purchases'])), (48, 32, 160))
        products = {row['id']: row for row in data['products']}
        customers = {row['id']: row for row in data['customers']}
        self.assertEqual(len(products), 48)
        self.assertEqual(len(customers), 32)
        self.assertEqual(len({row['id'] for row in data['purchases']}), 160)
        self.assertEqual(len({row['category'] for row in data['products']}), 6)
        self.assertTrue(all(type(row['price_cents']) is int and row['price_cents'] > 0 for row in data['products']))
        for row in data['purchases']:
            self.assertIn(row['customer_id'], customers)
            self.assertIn(row['product_id'], products)
            self.assertIs(type(row['quantity']), int)
            self.assertGreater(row['quantity'], 0)

    def test_graph_edges_reconcile_with_purchase_quantities(self):
        data = build_exploration()
        nodes = {row['id']: row for row in data['graph']['nodes']}
        self.assertEqual(len(nodes), 86)
        expected = Counter()
        for row in data['purchases']:
            expected[(row['customer_id'], row['product_id'])] += row['quantity']
        actual = {}
        categories = {}
        for edge in data['graph']['edges']:
            self.assertIn(edge['source'], nodes)
            self.assertIn(edge['target'], nodes)
            self.assertIs(type(edge['weight']), int)
            self.assertGreater(edge['weight'], 0)
            if edge['relation'] == 'purchased':
                self.assertEqual(nodes[edge['source']]['kind'], 'customer')
                self.assertEqual(nodes[edge['target']]['kind'], 'product')
                key = (edge['source'], edge['target'])
                self.assertNotIn(key, actual)
                actual[key] = edge['weight']
            else:
                self.assertEqual(edge['relation'], 'belongs_to')
                self.assertEqual(nodes[edge['source']]['kind'], 'product')
                self.assertEqual(nodes[edge['target']]['kind'], 'category')
                self.assertEqual(edge['weight'], 1)
                self.assertNotIn(edge['source'], categories)
                categories[edge['source']] = nodes[edge['target']]['label']
        self.assertEqual(actual, dict(expected))
        self.assertEqual(categories, {row['id']: row['category'] for row in data['products']})
        self.assertLess(len(actual), len(data['purchases']))
        self.assertEqual(sum(actual.values()), sum(row['quantity'] for row in data['purchases']))

    def test_normalized_vectors_have_truthful_similarity(self):
        data = build_exploration()
        self.assertEqual(len(data['dimensions']), 8)
        self.assertEqual(len(set(data['dimensions'])), 8)
        for product in data['products']:
            vector = product['vector']
            self.assertEqual(len(vector), 8)
            self.assertTrue(all(math.isfinite(value) and value >= 0 for value in vector))
            self.assertAlmostEqual(sum(value * value for value in vector), 1.0, places=12)
            strongest = max(range(8), key=vector.__getitem__)
            self.assertEqual(data['dimensions'][strongest], product['category'])
        anchor = data['products'][0]
        scores = []
        for other in data['products'][1:]:
            dot = sum(a * b for a, b in zip(anchor['vector'], other['vector']))
            cosine = dot / (math.sqrt(sum(a * a for a in anchor['vector'])) * math.sqrt(sum(b * b for b in other['vector'])))
            self.assertAlmostEqual(dot, cosine, places=12)
            self.assertGreaterEqual(cosine, 0)
            self.assertLessEqual(cosine, 1 + 1e-12)
            scores.append((cosine, other))
        nearest = max(scores, key=lambda item: item[0])[1]
        self.assertEqual(nearest['category'], anchor['category'])
        self.assertNotEqual(nearest['id'], anchor['id'])


if __name__ == '__main__':
    unittest.main()
