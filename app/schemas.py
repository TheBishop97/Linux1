from datetime import datetime
from pydantic import BaseModel

class SourceOut(BaseModel):
    id: int
    name: str
    base_url: str

    class Config:
        orm_mode = True

class ArticleOut(BaseModel):
    id: int
    source: SourceOut
    title: str
    url: str
    published_at: datetime | None
    summary: str | None
    sentiment: str | None

    class Config:
        orm_mode = True
