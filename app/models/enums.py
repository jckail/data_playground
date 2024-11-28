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
    UNKNOWN = "unknown"

class EventType(enum.Enum):
    """Types of events that can occur in the system"""
    # Account Events
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_DEACTIVATED = "account_deactivated"
    ACCOUNT_REACTIVATED = "account_reactivated"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    PROFILE_UPDATED = "profile_updated"
    PASSWORD_CHANGED = "password_changed"
    EMAIL_CHANGED = "email_changed"
    
    # Shop Events
    SHOP_CREATED = "shop_created"
    SHOP_DELETED = "shop_deleted"
    SHOP_UPDATED = "shop_updated"
    SHOP_DEACTIVATED = "shop_deactivated"
    SHOP_REACTIVATED = "shop_reactivated"
    SHOP_SETTINGS_UPDATED = "shop_settings_updated"
    
    # Product Events
    PRODUCT_CREATED = "product_created"
    PRODUCT_UPDATED = "product_updated"
    PRODUCT_DELETED = "product_deleted"
    PRODUCT_PRICE_CHANGED = "product_price_changed"
    PRODUCT_STATUS_CHANGED = "product_status_changed"
    PRODUCT_CATEGORY_CHANGED = "product_category_changed"
    
    # Order Events
    ORDER_PLACED = "order_placed"
    ORDER_UPDATED = "order_updated"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_PROCESSING = "order_processing"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    ORDER_RETURNED = "order_returned"
    ORDER_REFUNDED = "order_refunded"
    
    # Payment Events
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_PROCESSING = "payment_processing"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_PARTIALLY_REFUNDED = "payment_partially_refunded"
    PAYMENT_DISPUTED = "payment_disputed"
    PAYMENT_DISPUTE_RESOLVED = "payment_dispute_resolved"
    
    # Payment Method Events
    PAYMENT_METHOD_ADDED = "payment_method_added"
    PAYMENT_METHOD_UPDATED = "payment_method_updated"
    PAYMENT_METHOD_REMOVED = "payment_method_removed"
    PAYMENT_METHOD_EXPIRED = "payment_method_expired"
    PAYMENT_METHOD_DEFAULT_CHANGED = "payment_method_default_changed"
    
    # Review Events
    REVIEW_POSTED = "review_posted"
    REVIEW_UPDATED = "review_updated"
    REVIEW_DELETED = "review_deleted"
    REVIEW_REPORTED = "review_reported"
    REVIEW_STATUS_CHANGED = "review_status_changed"
    REVIEW_VOTE_ADDED = "review_vote_added"
    REVIEW_VOTE_REMOVED = "review_vote_removed"
    
    # Promotion Events
    PROMOTION_CREATED = "promotion_created"
    PROMOTION_UPDATED = "promotion_updated"
    PROMOTION_ACTIVATED = "promotion_activated"
    PROMOTION_DEACTIVATED = "promotion_deactivated"
    PROMOTION_USED = "promotion_used"
    PROMOTION_EXPIRED = "promotion_expired"
    PROMOTION_LIMIT_REACHED = "promotion_limit_reached"
    
    # Inventory Events
    INVENTORY_UPDATED = "inventory_updated"
    INVENTORY_LOW = "inventory_low"
    INVENTORY_OUT = "inventory_out"
    INVENTORY_RESTOCKED = "inventory_restocked"
    INVENTORY_ADJUSTED = "inventory_adjusted"
    INVENTORY_AUDIT = "inventory_audit"
    
    # Invoice Events
    INVOICE_CREATED = "invoice_created"
    INVOICE_UPDATED = "invoice_updated"
    INVOICE_PAID = "invoice_paid"
    INVOICE_CANCELLED = "invoice_cancelled"
    INVOICE_OVERDUE = "invoice_overdue"
    INVOICE_REMINDER_SENT = "invoice_reminder_sent"
    
    # Metric Events
    METRICS_UPDATED = "metrics_updated"
    SHOP_METRICS_UPDATED = "shop_metrics_updated"
    PRODUCT_METRICS_UPDATED = "product_metrics_updated"
    METRICS_ROLLUP_STARTED = "metrics_rollup_started"
    METRICS_ROLLUP_COMPLETED = "metrics_rollup_completed"
    METRICS_ROLLUP_FAILED = "metrics_rollup_failed"
    
    # System Events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    MAINTENANCE_STARTED = "maintenance_started"
    MAINTENANCE_COMPLETED = "maintenance_completed"
    BACKUP_STARTED = "backup_started"
    BACKUP_COMPLETED = "backup_completed"
    RESTORE_STARTED = "restore_started"
    RESTORE_COMPLETED = "restore_completed"
    
    # Data Integrity Events
    DATA_VALIDATION_STARTED = "data_validation_started"
    DATA_VALIDATION_COMPLETED = "data_validation_completed"
    DATA_CORRUPTION_DETECTED = "data_corruption_detected"
    DATA_REPAIR_STARTED = "data_repair_started"
    DATA_REPAIR_COMPLETED = "data_repair_completed"
    
    # API Events
    API_RATE_LIMIT_WARNING = "api_rate_limit_warning"
    API_RATE_LIMIT_EXCEEDED = "api_rate_limit_exceeded"
    API_THROTTLING_APPLIED = "api_throttling_applied"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    
    # Security Events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    LOGIN_ATTEMPT_FAILED = "login_attempt_failed"
    PASSWORD_RESET = "password_reset"
    TWO_FACTOR_ENABLED = "two_factor_enabled"
    TWO_FACTOR_DISABLED = "two_factor_disabled"
    
    # Error Events
    ERROR_OCCURRED = "error_occurred"
    SHOP_ERROR = "shop_error"
    PAYMENT_ERROR = "payment_error"
    SYSTEM_ERROR = "system_error"

    # Custom Events
    UNKNOWN_EVENT = "unknown_event"
