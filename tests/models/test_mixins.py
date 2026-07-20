import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from app.models.mixins import TimestampMixin, SoftDeleteMixin

Base = declarative_base()

class DummyModel(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "dummy_models"
    id = Column(Integer, primary_key=True)
    name = Column(String)

def test_mixins_attributes():
    dummy = DummyModel(name="test")
    assert hasattr(dummy, "created_at")
    assert hasattr(dummy, "updated_at")
    assert hasattr(dummy, "deleted_at")
