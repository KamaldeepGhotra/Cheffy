from pydantic import BaseModel, Field, model_validator
from datetime import date, datetime


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


class GroceryListRequest(BaseModel):
    household_id: str
    recipe_ids: list[int]
    servings: dict[int, int]


class GroceryLine(BaseModel):
    ingredient_name: str
    needed: float
    unit: str


class GroceryListResponse(BaseModel):
    have: list[GroceryLine]
    need: list[GroceryLine]


class MealPlanEntryCreate(BaseModel):
    household_id: str
    week_start: date
    day: int | None = Field(default=None, ge=0, le=6)
    recipe_id: int
    servings: int = Field(default=1, ge=1)
    assigned_to: str | None = None


class MealPlanEntryOut(BaseModel):
    id: int
    week_start: date
    day: int | None
    recipe_id: int
    recipe_name: str
    servings: int
    assigned_to: str | None


class MealPlanEntryUpdate(BaseModel):
    day: int | None = Field(default=None, ge=0, le=6)
    servings: int = Field(default=None, ge=1)
    assigned_to: str | None = None

    @model_validator(mode="after")
    def require_a_field(self):
        if not self.model_fields_set:
            raise ValueError("Send at least one of day, servings or assigned_to")
        return self
