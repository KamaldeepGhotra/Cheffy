from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import models  # noqa: F401
from app.db import Base, engine
from app.routers import ingredients, inventory, recipes, grocery, meal_plan


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Cheffy API", lifespan=lifespan)
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
app.include_router(meal_plan.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
