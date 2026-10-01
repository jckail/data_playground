"""Independent synthetic commerce graph and transparent product feature vectors."""
from collections import Counter
from math import sqrt
from random import Random

DIMENSIONS = ("Outdoor", "Kitchen", "Office", "Fitness", "Audio", "Photography", "Portability", "Premium")
# Name, integer price cents, portability score. These are invented products.
PRODUCTS = (
    ("Outdoor", "Fitness", (
        ("Trail daypack", 5900, .95), ("Alpine tent", 18900, .60),
        ("Pocket lantern", 2900, 1.0), ("Camp kettle", 3900, .70),
        ("Trekking poles", 7900, .80), ("Insulated flask", 3500, .90),
        ("Picnic blanket", 4500, .60), ("Compact camp chair", 8900, .65))),
    ("Kitchen", "Office", (
        ("Pour-over brewer", 3900, .65), ("Chef knife", 8900, .30),
        ("Cast iron skillet", 6900, .10), ("Lunch box", 2900, .95),
        ("Spice grinder", 4900, .50), ("Kitchen scale", 3500, .55),
        ("Ceramic serving bowl", 4500, .20), ("Travel coffee press", 5900, .90))),
    ("Office", "Audio", (
        ("Ergonomic desk chair", 24900, .05), ("Mechanical keyboard", 12900, .45),
        ("Pocket notebook", 1900, 1.0), ("Adjustable desk lamp", 6900, .30),
        ("Laptop stand", 5900, .65), ("Cable organizer", 1500, .95),
        ("Portable whiteboard", 7900, .60), ("Desk storage tray", 2900, .40))),
    ("Fitness", "Outdoor", (
        ("Training mat", 4900, .70), ("Resistance bands", 2900, 1.0),
        ("Adjustable dumbbell", 17900, .10), ("Running belt", 2500, .95),
        ("Recovery roller", 3900, .60), ("Jump rope", 1900, 1.0),
        ("Balance board", 7900, .35), ("Training bag", 6900, .85))),
    ("Audio", "Office", (
        ("Studio headphones", 14900, .65), ("Wireless earbuds", 9900, 1.0),
        ("Bookshelf speakers", 24900, .10), ("Portable speaker", 7900, .95),
        ("USB microphone", 12900, .55), ("Audio interface", 19900, .45),
        ("Headphone case", 2900, .90), ("Desktop amplifier", 22900, .25))),
    ("Photography", "Outdoor", (
        ("Travel tripod", 11900, .85), ("Camera sling", 7900, .90),
        ("Studio light", 18900, .20), ("Lens cleaning kit", 1900, 1.0),
        ("Reflector panel", 3900, .65), ("Camera backpack", 13900, .80),
        ("Tabletop lightbox", 9900, .35), ("Compact camera grip", 5900, .95))),
)


def build_exploration():
    """Create seed-42 shopping records without touching lifecycle simulation RNG."""
    rng = Random(42)
    products = []
    by_category = {}
    categories = list(DIMENSIONS[:6])
    for category, adjacent, items in PRODUCTS:
        by_category[category] = []
        for name, price, portability in items:
            raw = [0.0] * 8
            raw[categories.index(category)] = 1.0
            raw[categories.index(adjacent)] = 0.2
            raw[6] = 0.45 * portability
            raw[7] = 0.45 * price / 30000
            norm = sqrt(sum(value * value for value in raw))
            product = dict(id=f"product-{len(products) + 1:03d}", name=name, category=category,
                           description=f"Synthetic {category.lower()} product. Portability {portability:.0%}; premium price feature {price / 30000:.0%}. Related interest: {adjacent.lower()}.",
                           price_cents=price, vector=[value / norm for value in raw])
            products.append(product)
            by_category[category].append(product["id"])
    customers = []
    purchases = []
    for index in range(32):
        category, adjacent, _ = PRODUCTS[index % len(PRODUCTS)]
        customer = dict(id=f"customer-{index + 1:03d}", name=f"Demo shopper {index + 1:02d}", segment=f"{category} enthusiast")
        customers.append(customer)
        selected = []
        for purchase_index in range(5):
            # One repeat per shopper exposes the distinction between rows and edges.
            if purchase_index == 4:
                product_id = selected[0]
            else:
                draw = rng.random()
                interest = category if draw < .7 else adjacent if draw < .9 else rng.choice(categories)
                product_id = rng.choice(by_category[interest])
                selected.append(product_id)
            purchases.append(dict(id=f"purchase-{len(purchases) + 1:03d}", customer_id=customer["id"],
                                  product_id=product_id, quantity=rng.randint(1, 3)))
    nodes = [dict(id=customer["id"], label=customer["name"], kind="customer") for customer in customers]
    nodes.extend(dict(id=product["id"], label=product["name"], kind="product") for product in products)
    nodes.extend(dict(id=f"category-{category.lower()}", label=category, kind="category") for category in categories)
    quantities = Counter()
    for purchase in purchases:
        quantities[(purchase["customer_id"], purchase["product_id"])] += purchase["quantity"]
    edges = [dict(source=customer, target=product, relation="purchased", weight=quantity)
             for (customer, product), quantity in sorted(quantities.items())]
    edges.extend(dict(source=product["id"], target=f"category-{product['category'].lower()}", relation="belongs_to", weight=1)
                 for product in products)
    return dict(seed=42,
                description="Independent synthetic shopping dataset: 48 products, 32 demo shoppers and 160 purchase rows. It is not joined to the lifecycle scenarios. Vectors are transparent category, portability and price features, not learned embeddings; cosine similarity measures only these features.",
                dimensions=list(DIMENSIONS), products=products, customers=customers, purchases=purchases,
                graph=dict(nodes=nodes, edges=edges))
