from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import MealPlanEntry, Recipe
from app.schemas import MealPlanEntryCreate, MealPlanEntryOut

router = APIRouter(prefix="/meal-plan", tags=["meal-plan"])


def _to_out(entry: MealPlanEntry) -> MealPlanEntryOut:
    return MealPlanEntryOut(
        id=entry.id,
        week_start=entry.week_start,
        day=entry.day,
        recipe_id=entry.recipe_id,
        recipe_name=entry.recipe.name,
        servings=entry.servings,
        assigned_to=entry.assigned_to,
    )


@router.get("", response_model=list[MealPlanEntryOut])
def get_week(household_id: str, week_start: date, db: Session = Depends(get_db)):
    entries = (
        db.query(MealPlanEntry)
        .filter_by(household_id=household_id, week_start=week_start)
        .order_by(MealPlanEntry.day, MealPlanEntry.id)
        .all()
    )
    return [_to_out(e) for e in entries]


@router.post("", response_model=MealPlanEntryOut, status_code=201)
def add_entry(payload: MealPlanEntryCreate, db: Session = Depends(get_db)):
    if not db.query(Recipe).filter_by(id=payload.recipe_id).first():
        raise HTTPException(status_code=404, detail="Recipe not found")
    entry = MealPlanEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_out(entry)


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(MealPlanEntry).filter_by(id=entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Meal plan entry not found")
    db.delete(entry)
    db.commit()
