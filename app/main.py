from fastapi import FastAPI
from .database import engine
from . import models
from .routes import users, events, admin, shops

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(users.router)
app.include_router(shops.router)
app.include_router(events.router)
app.include_router(admin.router, prefix="/admin", tags=["admin"])

@app.get("/")
def read_root():
    return {"Hello": "World"}