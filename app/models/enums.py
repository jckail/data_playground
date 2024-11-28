import enum

class PaymentMethodType(enum.Enum):
    """Types of payment methods that can be stored"""
    CREDIT_CARD = "credit_card"  # Credit cards
    DEBIT_CARD = "debit_card"  # Debit cards
    BANK_ACCOUNT = "bank_account"  # Direct bank account
    DIGITAL_WALLET = "digital_wallet"  # Digital wallets (PayPal, etc.)
    CRYPTO_WALLET = "crypto_wallet"  # Cryptocurrency wallets

class PaymentMethodStatus(enum.Enum):
    """Possible states for a payment method"""
    ACTIVE = "active"  # Available for use
    EXPIRED = "expired"  # Card/account expired
    SUSPENDED = "suspended"  # Temporarily unavailable
    DELETED = "deleted"  # Removed by user

class PaymentStatus(enum.Enum):
    """Possible states for a payment"""
    # Initial states
    DRAFT = "draft"  # Being prepared
    PENDING = "pending"  # Payment initiated
    PROCESSING = "processing"  # Payment being processed
    
    # Success states
    COMPLETED = "completed"  # Payment successful
    PAID = "paid"  # Fully paid
    PARTIALLY_PAID = "partially_paid"  # Partially paid
    
    # Problem states
    FAILED = "failed"  # Payment failed
    OVERDUE = "overdue"  # Past due date
    
    # Cancellation/Refund states
    CANCELLED = "cancelled"  # Payment cancelled
    REFUNDED = "refunded"  # Payment fully refunded
    PARTIALLY_REFUNDED = "partially_refunded"  # Payment partially refunded

class OrderStatus(enum.Enum):
    """Possible states for an order"""
    PENDING = "pending"  # Order created but not processed
    PROCESSING = "processing"  # Order being prepared
    SHIPPED = "shipped"  # Order sent to customer
    DELIVERED = "delivered"  # Order received by customer
    CANCELLED = "cancelled"  # Order cancelled before completion
    REFUNDED = "refunded"  # Order refunded after completion
    ON_HOLD = "on_hold"  # Order temporarily suspended
    RETURNED = "returned"  # Order returned by customer

class ShippingMethod(enum.Enum):
    """Available shipping methods"""
    STANDARD = "standard"  # Regular shipping (3-5 days)
    EXPRESS = "express"  # Expedited shipping (1-2 days)
    OVERNIGHT = "overnight"  # Next-day delivery
    LOCAL_PICKUP = "local_pickup"  # Customer picks up from store
    INTERNATIONAL = "international"  # International shipping

class PaymentTerms(enum.Enum):
    """Available payment terms"""
    IMMEDIATE = "immediate"  # Due immediately
    NET_15 = "net_15"  # Due in 15 days
    NET_30 = "net_30"  # Due in 30 days
    NET_45 = "net_45"  # Due in 45 days
    NET_60 = "net_60"  # Due in 60 days
    CUSTOM = "custom"  # Custom payment terms

class ShopCategory(enum.Enum):
    """Categories available for shops"""
    RETAIL = "retail"  # General retail
    RESTAURANT = "restaurant"  # Food service
    SERVICES = "services"  # Service providers
    TECHNOLOGY = "technology"  # Tech products/services
    FASHION = "fashion"  # Clothing and accessories
    HEALTH = "health"  # Health and wellness
    ENTERTAINMENT = "entertainment"  # Entertainment products/services
    OTHER = "other"  # Other categories

class ProductCategory(enum.Enum):
    """Categories available for products"""
    ELECTRONICS = "electronics"  # Electronic devices
    CLOTHING = "clothing"  # Apparel
    FOOD = "food"  # Food items
    BOOKS = "books"  # Books and publications
    HOME = "home"  # Home goods
    BEAUTY = "beauty"  # Beauty products
    SPORTS = "sports"  # Sports equipment
    TOYS = "toys"  # Toys and games
    AUTOMOTIVE = "automotive"  # Auto parts/accessories
    HEALTH = "health"  # Health products
    OTHER = "other"  # Other categories

class ProductStatus(enum.Enum):
    """Possible states for a product"""
    ACTIVE = "active"  # Available for purchase
    INACTIVE = "inactive"  # Temporarily unavailable
    OUT_OF_STOCK = "out_of_stock"  # No stock available
    DISCONTINUED = "discontinued"  # No longer sold

class PromotionType(enum.Enum):
    """Types of promotions that can be offered"""
    PERCENTAGE = "percentage"  # Percentage off total
    FIXED_AMOUNT = "fixed_amount"  # Fixed amount off total
    BUY_X_GET_Y = "buy_x_get_y"  # Buy X items, get Y free/discounted
    BUNDLE = "bundle"  # Discount on product bundles
    FREE_SHIPPING = "free_shipping"  # Free shipping offer
    MINIMUM_PURCHASE = "minimum_purchase"  # Discount with minimum spend

class PromotionStatus(enum.Enum):
    """Possible states for a promotion"""
    DRAFT = "draft"  # Being created/edited
    SCHEDULED = "scheduled"  # Set to start in future
    ACTIVE = "active"  # Currently running
    PAUSED = "paused"  # Temporarily suspended
    ENDED = "ended"  # Naturally completed
    CANCELLED = "cancelled"  # Manually stopped

class PromotionApplicability(enum.Enum):
    """What the promotion applies to"""
    ALL_PRODUCTS = "all_products"  # Applies to entire shop
    SPECIFIC_PRODUCTS = "specific_products"  # Only certain products
    SPECIFIC_CATEGORIES = "specific_categories"  # Only certain categories
    MINIMUM_ORDER = "minimum_order"  # Orders above threshold

class ReviewType(enum.Enum):
    """Types of reviews that can be created"""
    SHOP = "shop"  # Review for the overall shop
    PRODUCT = "product"  # Review for a specific product

class ReviewStatus(enum.Enum):
    """Possible states for a review"""
    PENDING = "pending"  # Awaiting moderation
    APPROVED = "approved"  # Visible to public
    REJECTED = "rejected"  # Not approved for display
    REPORTED = "reported"  # Flagged for review
    REMOVED = "removed"  # Taken down after being live

class InventoryChangeType(enum.Enum):
    """Types of inventory changes that can occur"""
    PURCHASE = "purchase"  # New stock purchased/received
    SALE = "sale"  # Stock sold to customer
    RETURN = "return"  # Customer return
    ADJUSTMENT = "adjustment"  # Manual stock adjustment
    LOSS = "loss"  # Damaged/lost inventory
    RECOUNT = "recount"  # Physical inventory count
    TRANSFER_IN = "transfer_in"  # Stock received from another location
    TRANSFER_OUT = "transfer_out"  # Stock sent to another location
    RESERVATION = "reservation"  # Stock reserved for order
    RESERVATION_RELEASE = "reservation_release"  # Reserved stock released

class EntityType(enum.Enum):
    USER = "user"
    SHOP = "user_shop"
    SHOP_PRODUCT = "shop_product"
    USER_INVOICE = "user_invoice"
    USER_PAYMENT = "user_payment"
    SHOP_ORDER = "shop_order"
    SHOP_REVIEW = "shop_review"
    SHOP_PROMOTION = "shop_promotion"
    USER_PAYMENT_METHOD = "user_payment_method"