from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import models  # noqa: F401
from app.db import Base, engine
from app.routers import ingredients, inventory, recipes, grocery

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cheffy API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ingredients.router)
app.include_router(inventory.router)
app.include_router(recipes.router)
app.include_router(grocery.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
