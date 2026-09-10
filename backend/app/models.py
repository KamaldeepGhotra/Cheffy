from sqlalchemy import Column, Integer, String
from app.db import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    category = Column(String, nullable=True)
    default_unit = Column(String, nullable=True)
