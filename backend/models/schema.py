"""
Database models matching the schema in the Design Document
(Product, Claim, Evidence, Verdict, Report). (FR-9)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from models.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    brand = Column(String)
    category = Column(String)
    sugars_100g = Column(Float, nullable=True)
    additives_count = Column(Integer, default=0)
    nutriscore_grade = Column(String, nullable=True)
    ingredients_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reports = relationship("Report", back_populates="product", cascade="all, delete-orphan")


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    claim_text = Column(String, nullable=False)
    claim_type = Column(String)

    verdicts = relationship("Verdict", back_populates="claim", cascade="all, delete-orphan")


class Verdict(Base):
    __tablename__ = "verdicts"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"))
    result = Column(String)  # "supported", "contradicted", "unsupported"
    explanation = Column(Text)
    source = Column(String)  # "fssai_regulation", "ccpa_ruling", "open_food_facts"
    regulation_ref = Column(String, nullable=True)

    claim = relationship("Claim", back_populates="verdicts")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String, nullable=False)
    brand = Column(String)
    marketing_text = Column(Text, nullable=True)
    mas_score = Column(Integer, nullable=True)
    claims_json = Column(Text, nullable=True)  # JSON serialized claim verdicts
    evidence_json = Column(Text, nullable=True)  # JSON serialized evidence used
    report_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="reports")
