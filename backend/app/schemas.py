from pydantic import BaseModel
from datetime import datetime


class IngredientMatch(BaseModel):
    id: int
    name: str
    score: float


class InventoryItemCreate(BaseModel):
    household_id: str
    ingredient_name: str
    quantity: float
    unit: str


class InventoryItemOut(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    household_id: str
    quantity: float
    unit: str
    added_date: datetime

    class Config:
        from_attributes = True


class RecipeSearchRequest(BaseModel):
    query: str


class RecipeIngredientOut(BaseModel):
    ingredient_id: int
    ingredient_name: str
    quantity: float
    unit: str


class RecipeOut(BaseModel):
    id: int
    name: str
    instructions: str
    calories: float | None
    protein: float | None
    fat: float | None
    carbs: float | None
    ingredients: list[RecipeIngredientOut]
