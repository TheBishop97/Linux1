import hashlib
import logging
import time
from datetime import datetime
from typing import Optional

import feedparser
import trafilatura
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Source, Article
from app.config import settings

log = logging.getLogger("ingest")
log.setLevel(logging.INFO)

sent_analyzer = SentimentIntensityAnalyzer()

DEFAULT_SOURCES = {
    "BBC": {"base_url": "https://www.bbc.co.uk", "rss": "https://feeds.bbci.co.uk/news/rss.xml"},
    "CNN": {"base_url": "https://www.cnn.com", "rss": "https://rss.cnn.com/rss/edition.rss"},
}

def make_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

def extract_text(url: str) -> Optional[str]:
    try:
        downloaded = trafilatura.fetch_url(url, no_ssl=True)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except Exception as e:
        log.warning("Trafilatura failed for %s: %s", url, e)
        return None

def summarize_text(text: str, sentences: int = 3) -> str:
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        sents = summarizer(parser.document, sentences)
        out = " ".join(str(s) for s in sents)
        if out.strip():
            return out
    except Exception:
        pass
    # naive fallback
    chunks = [t.strip() for t in text.replace("\n", " ").split(".") if t.strip()]
    return ". ".join(chunks[:sentences]) + ("." if chunks else "")

def sentiment_label(text: str) -> str:
    vs = sent_analyzer.polarity_scores(text)
    compound = vs.get("compound", 0)
    if compound >= 0.05:
        return "positive"
    elif compound <= -0.05:
        return "negative"
    return "neutral"

def upsert_source(db: Session, name: str, base_url: str, rss_url: Optional[str]):
    src = db.query(Source).filter(Source.base_url == base_url).first()
    if src:
        return src
    src = Source(name=name, base_url=base_url, rss_url=rss_url)
    db.add(src)
    db.commit()
    db.refresh(src)
    return src

def seed_default_sources(db: Session):
    for name, cfg in DEFAULT_SOURCES.items():
        upsert_source(db, name=name, base_url=cfg["base_url"], rss_url=cfg["rss"])

def fetch_once():
    db = SessionLocal()
    try:
        seed_default_sources(db)
        feeds = settings.FEEDS or [cfg["rss"] for cfg in DEFAULT_SOURCES.values()]
        max_items = settings.MAX_ITEMS_PER_FEED
        for feed_url in feeds:
            try:
                fp = feedparser.parse(feed_url)
            except Exception as e:
                log.error("Failed to parse feed %s: %s", feed_url, e)
                continue

            for entry in fp.entries[:max_items]:
                url = (entry.get("link") or "").strip()
                if not url:
                    continue
                url_h = make_hash(url)

                exists = db.query(Article).filter(Article.url_hash == url_h).first()
                if exists:
                    continue

                # map to source by RSS matching first, else by host contain
                source = db.query(Source).filter(Source.rss_url == feed_url).first()
                if not source:
                    host = url.split("/")[2] if "://" in url else None
                    if host:
                        source = db.query(Source).filter(Source.base_url.contains(host)).first()
                if not source:
                    source = upsert_source(db, name=host or "unknown", base_url=f"https://{host}" if host else url, rss_url=feed_url)

                # extract text
                text = extract_text(url) or (entry.get("summary") or "")
                if not text or len(text) < 200:
                    # skip very short items
                    continue

                summary = summarize_text(text, sentences=settings.SUMMARY_SENTENCES)
                sent = sentiment_label(summary or text)

                published = None
                if entry.get("published_parsed"):
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except Exception:
                        published = None

                art = Article(
                    source_id=source.id,
                    title=(entry.get("title") or "")[:800],
                    url=url,
                    url_hash=url_h,
                    published_at=published,
                    full_text=text,
                    summary=summary,
                    sentiment=sent,
                    meta={"feed": feed_url}
                )
                db.add(art)
                try:
                    db.commit()
                    log.info("Stored article: %s (%s)", art.title[:80], source.name)
                except Exception as e:
                    db.rollback()
                    log.error("DB commit failed for %s: %s", url, e)
    finally:
        db.close()

def run_forever():
    interval = max(60, int(settings.FETCH_INTERVAL_SECONDS))
    log.info("Ingestion loop started (interval=%s seconds)", interval)
    while True:
        start = time.time()
        try:
            fetch_once()
        except Exception:
            log.exception("Unexpected error in fetch_once")
        elapsed = time.time() - start
        sleep_for = max(5, interval - int(elapsed))
        time.sleep(sleep_for)

if __name__ == "__main__":
    fetch_once()
