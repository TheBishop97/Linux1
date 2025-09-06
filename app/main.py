import logging
import threading

from fastapi import FastAPI, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, desc

from app.db import Base, engine, SessionLocal
from app.models import Article, Source
from app.schemas import ArticleOut, SourceOut
from app.ingest import run_forever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("perspectiva")

app = FastAPI(title="Perspectiva MVP", version="0.1.0")

# Create tables at startup if needed
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def start_background_ingest():
    t = threading.Thread(target=run_forever, daemon=True)
    t.start()
    logger.info("Started ingestion thread")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/sources", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    rows = db.query(Source).all()
    return rows

@app.get("/articles", response_model=list[ArticleOut])
def list_articles(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Keyword to search in title"),
    limit: int = Query(20, ge=1, le=100),
    sentiment: str | None = Query(None, description="positive|neutral|negative"),
    source_id: int | None = Query(None),
):
    stmt = select(Article).options(joinedload(Article.source)).order_by(desc(Article.published_at), desc(Article.id))
    if q:
        stmt = stmt.filter(Article.title.ilike(f"%{q}%"))
    if sentiment:
        stmt = stmt.filter(Article.sentiment == sentiment)
    if source_id:
        stmt = stmt.filter(Article.source_id == source_id)
    rows = db.execute(stmt.limit(limit)).scalars().all()
    return rows

@app.get("/", response_class=HTMLResponse)
def home(db: Session = Depends(get_db), q: str | None = None, sentiment: str | None = None):
    stmt = select(Article).options(joinedload(Article.source)).order_by(desc(Article.published_at), desc(Article.id)).limit(40)
    if q:
        stmt = stmt.filter(Article.title.ilike(f"%{q}%"))
    if sentiment:
        stmt = stmt.filter(Article.sentiment == sentiment)
    rows = db.execute(stmt).scalars().all()

    items = ""
    for a in rows:
        published = a.published_at.isoformat() if a.published_at else ""
        summary = (a.summary or "")[:600]
        items += f"""
        <div class='card'>
          <div class='meta'>[{a.source.name}] {published} — <span class='sent {a.sentiment or ''}'>{a.sentiment or ''}</span></div>
          <div class='title'><a href='{a.url}' target='_blank' rel='noopener'>{a.title}</a></div>
          <div class='summary'>{summary}</div>
        </div>
        """

    html = f"""
    <html>
    <head>
      <meta charset='utf-8'/>
      <title>Perspectiva — MVP</title>
      <style>
        body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; background:#0b0e14; color:#e6e6e6; }}
        .wrap {{ max-width: 960px; margin: 0 auto; }}
        h1 {{ margin-bottom: .5rem; }}
        .card {{ background:#131824; padding:1rem; margin:1rem 0; border-radius:14px; box-shadow: 0 2px 8px rgba(0,0,0,.3); }}
        .meta {{ font-size:.8rem; opacity:.8; margin-bottom:.25rem; }}
        .title a {{ color:#9cd2ff; text-decoration:none; }}
        .summary {{ opacity:.95; margin-top:.5rem; line-height:1.4; }}
        .sent {{ padding:.1rem .4rem; border-radius:6px; font-size:.75rem; }}
        .sent.positive {{ background:#163; }}
        .sent.neutral {{ background:#333; }}
        .sent.negative {{ background:#631; }}
        input, select {{ background:#0f1420; color:#e6e6e6; border:1px solid #253047; border-radius:8px; padding:.4rem .6rem; }}
        button {{ background:#1a2440; color:#e6e6e6; border:1px solid #2b3a5d; border-radius:8px; padding:.4rem .8rem; cursor:pointer; }}
      </style>
    </head>
    <body>
      <div class='wrap'>
        <h1>Perspectiva — MVP</h1>
        <p>Aggregated latest articles (auto-updating ingestion thread running on the server).</p>
        <div class='filters'>
          <form method='get' action='/'>
            <input type='text' name='q' placeholder='Search title keyword' />
            <select name='sentiment'>
              <option value=''>Any sentiment</option>
              <option>positive</option>
              <option>neutral</option>
              <option>negative</option>
            </select>
            <button type='submit'>Filter</button>
          </form>
        </div>
        {items}
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
