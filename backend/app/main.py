from fastapi import FastAPI
from app import models  # noqa: F401
from app.routers import ingredients, inventory

app = FastAPI(title="Cheffy API")
app.include_router(ingredients.router)
app.include_router(inventory.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
