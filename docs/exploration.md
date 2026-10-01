# Graph and vector exploration dataset

`python -m playground export --output artifacts/catalog.json` exports the four
lifecycle runs plus an additive top-level `exploration` object. This independently
seeded shopping dataset has 48 invented products in six categories, 32 demo
shoppers, and 160 purchase rows. It is **not joined to the lifecycle scenarios**:
its purchases do not reconcile to their subscription revenue or customer counts.
Schema version 1 and engine version 1.0.0 remain unchanged; consumers supporting
older artifacts can treat the new top-level object as optional.

## Product vectors

The eight dimensions, in order, are Outdoor, Kitchen, Office, Fitness, Audio,
Photography, Portability, and Premium. Each product starts with a weight of 1
for its own category and 0.2 for a related shopping interest. The portability
coordinate is 0.45 times its manually assigned portability score (0–1). Premium
is 0.45 times price in cents divided by 30,000. All current prices are below that
reference price. Category pairings and input scores are explicit in
`playground/exploration.py`; product descriptions expose portability and price
feature inputs for inspection.

Divide each feature by the square root of the sum of squared features to obtain
the exported nonnegative unit vector. Cosine similarity is the dot product
because these vectors have unit length (subject to floating-point precision).
An identical vector has similarity 1. Exclude the query product itself when
ranking neighbors; use the product ID to resolve equal-score ties consistently.

These are transparent, handcrafted feature vectors, **not learned embeddings**.
Similarity means closeness under this small feature model, not text relevance,
quality, purchase probability, or a personalized recommendation. Price is an
illustrative premium preference signal, not an assessment of product quality.
No embedding provider or vector database is required.

## Purchase graph

A local seed-42 RNG generates five purchases per customer. Customers rotate
through six category-interest segments. For the first four rows, 70% of the
selection probability goes to the primary category, 20% to its related interest,
and 10% to a uniformly selected category. Each fifth row repeats that shopper's
first product so aggregation is visible. Quantities are integers from 1 to 3.

Nodes represent customers, products, and categories. A directed `purchased` edge
goes from a customer to a product, weighted by the **sum of purchased quantity**
across all matching rows. It does not count transactions. Each product has one
`belongs_to` edge to its category, with weight 1. Customer/product IDs match the
source records; category IDs are `category-` plus the lowercase category name.
The graph contains all 86 nodes, including any products without purchases.

Graph traversal answers explicit relationship questions such as which products
share buyers. Vector search answers feature-similarity questions. Neither
establishes causation. These fictional records contain no real customer data,
timestamps, returns, tax, shipping, or inventory constraints.

## Validation

Run `python -m unittest discover -s tests`. Tests verify repeatability and global
RNG isolation, exact populations, unique IDs, all references, graph edge/quantity
reconciliation, one category edge per product, unit vector norms, cosine/dot
agreement, sensible nearest neighbors, and deterministic atomic export parity.
