from pydantic import BaseModel


class IngredientMatch(BaseModel):
    id: int
    name: str
    score: float
