from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON as JSONType
from app.db import Base

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    base_url = Column(String(300), nullable=False)
    rss_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    articles = relationship("Article", back_populates="source")

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    title = Column(String(800), nullable=False)
    url = Column(String(1000), nullable=False)
    url_hash = Column(String(64), nullable=False)
    published_at = Column(DateTime, nullable=True)
    full_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    sentiment = Column(String(16), nullable=True)  # positive | neutral | negative
    meta = Column(JSONType, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="articles")

    __table_args__ = (UniqueConstraint("url_hash", name="uq_articles_url_hash"),)
