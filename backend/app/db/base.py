"""Declarative Base for SQLAlchemy Models."""

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models in TraceNest."""
    pass
