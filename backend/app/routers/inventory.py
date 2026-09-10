from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.matching import resolve_or_create_ingredient
from app.models import InventoryItem
from app.schemas import InventoryItemCreate, InventoryItemOut

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _to_out(item: InventoryItem) -> InventoryItemOut:
    return InventoryItemOut(
        id=item.id,
        ingredient_id=item.ingredient_id,
        ingredient_name=item.ingredient.name,
        household_id=item.household_id,
        quantity=item.quantity,
        unit=item.unit,
        added_date=item.added_date,
    )


@router.post("", response_model=InventoryItemOut, status_code=201)
def add_inventory_item(payload: InventoryItemCreate, db: Session = Depends(get_db)):
    ingredient = resolve_or_create_ingredient(db, payload.ingredient_name)
    item = InventoryItem(
        ingredient_id=ingredient.id,
        household_id=payload.household_id,
        quantity=payload.quantity,
        unit=payload.unit,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.get("", response_model=list[InventoryItemOut])
def list_inventory(household_id: str, db: Session = Depends(get_db)):
    items = db.query(InventoryItem).filter_by(household_id=household_id).all()
    return [_to_out(item) for item in items]


@router.delete("/{item_id}", status_code=204)
def delete_inventory_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(InventoryItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    db.delete(item)
    db.commit()
