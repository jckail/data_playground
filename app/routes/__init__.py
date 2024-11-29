from .fake_users import router as fake_users_router
from .invoices import router as invoices_router
from .payments import router as payments_router
from .shops import router as shops_router
from .events import router as events_router
from .create_rollups import router as create_rollups_router
from .fake_user_snapshot import router as fake_user_snapshot_router
from .shop_snapshot import router as shop_snapshot_router
from .generate_fake_data import router as generate_fake_data_router
from .fake_user2 import router as fake_user2_router

__all__ = [
    'fake_users_router',
    'invoices_router',
    'payments_router',
    'shops_router',
    'events_router',
    'create_rollups_router',
    'fake_user_snapshot_router',
    'shop_snapshot_router',
    'generate_fake_data_router',
    'fake_user2_router'
]
