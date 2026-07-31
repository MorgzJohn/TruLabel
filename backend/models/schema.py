"""
Database models matching the schema in the Design Document
(Product, Claim, Evidence, Verdict, Report, Comparison/Recommendation).
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Product(Base):
    __tablename__ = "product"
    product_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    brand = Column(String)
    category = Column(String)
    off_reference_id = Column(String)


class Claim(Base):
    __tablename__ = "claim"
    claim_id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("product.product_id"))
    claim_text = Column(String, nullable=False)
    claim_type = Column(String)


class Evidence(Base):
    __tablename__ = "evidence"
    evidence_id = Column(Integer, primary_key=True)
    claim_id = Column(Integer, ForeignKey("claim.claim_id"))
    source = Column(String)
    credibility_score = Column(Float)


class Verdict(Base):
    __tablename__ = "verdict"
    verdict_id = Column(Integer, primary_key=True)
    claim_id = Column(Integer, ForeignKey("claim.claim_id"))
    result = Column(String)
    explanation = Column(String)


class Report(Base):
    __tablename__ = "report"
    report_id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("product.product_id"))
    mas_score = Column(Float)
    created_at = Column(DateTime)
