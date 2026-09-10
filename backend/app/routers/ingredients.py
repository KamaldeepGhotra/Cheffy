from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.matching import find_ingredient_matches
from app.schemas import IngredientMatch

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("/search", response_model=list[IngredientMatch])
def search_ingredients(q: str, limit: int = 5, db: Session = Depends(get_db)):
    matches = find_ingredient_matches(db, q, limit=limit)
    return [IngredientMatch(id=ingredient.id, name=ingredient.name, score=score) for ingredient, score in matches]
