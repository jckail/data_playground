from fastapi import FastAPI
from .routes import users, events, admin, shops, invoices, payments

app = FastAPI()

app.include_router(users.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(shops.router)
app.include_router(events.router)
app.include_router(admin.router, prefix="/admin", tags=["admin"])

@app.get("/")
def read_root():
    return {"Hello": "World"}
