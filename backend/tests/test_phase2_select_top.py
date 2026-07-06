"""Unit tests for balanced-coverage story selection (PRD 7 ranking).

Selection drops off-topic (zero interest-match) stories, and round-robins across
the user's interests so a multi-interest user hears something from each pick
instead of one hot topic sweeping every slot. Falls back to plain top-N when
nothing matches so generation never starves.
"""

from datetime import UTC, datetime

from app.schemas.news import Article, RankedArticle
from app.services.news.service import NewsService


def _ranked(title: str, score: float, content: str = "") -> RankedArticle:
    """Interest match is computed from real text, so titles carry keywords."""
    art = Article(
        title=title, source="X", url=f"https://x.com/{title}",
        published_at=datetime.now(UTC), content=content or title,
    )
    # subscores["interest"] is set to score>0 marker; real per-interest matching
    # is recomputed inside _select_top from the article text.
    return RankedArticle(article=art, score=score, subscores={"interest": 1.0})


def _offtopic(title: str, score: float) -> RankedArticle:
    art = Article(
        title=title, source="X", url=f"https://x.com/{title}",
        published_at=datetime.now(UTC), content=title,
    )
    return RankedArticle(article=art, score=score, subscores={"interest": 0.0})


def test_drops_off_topic_stories() -> None:
    ranked = [
        _offtopic("cooking recipe stew", 0.40),      # off-topic, high score
        _ranked("sports match final score", 0.35),   # on-topic
        _offtopic("weather forecast rain", 0.34),
    ]
    top = NewsService._select_top(ranked, ["sports"], top_n=3)
    assert [r.article.title for r in top] == ["sports match final score"]


def test_guardrail_falls_back_when_no_matches() -> None:
    ranked = [_offtopic("cooking A", 0.40), _offtopic("weather B", 0.35)]
    top = NewsService._select_top(ranked, ["sports"], top_n=2)
    assert len(top) == 2  # fell back to plain top-N, not empty


def test_no_interests_returns_plain_top_n() -> None:
    ranked = [_ranked(f"story {i}", 1.0 - i * 0.1) for i in range(5)]
    top = NewsService._select_top(ranked, [], top_n=3)
    assert len(top) == 3


def test_round_robin_covers_each_interest() -> None:
    """Key behavior: with many sports + one tech story, tech still gets a slot."""
    ranked = [
        _ranked("sports match one", 0.90),
        _ranked("sports game two", 0.85),
        _ranked("sports final three", 0.80),
        _ranked("technology gadget launch", 0.50),  # lower score, different topic
    ]
    top = NewsService._select_top(ranked, ["sports", "technology"], top_n=2)
    titles = [r.article.title for r in top]
    # Round-robin: best sports story, then the tech story (not a 2nd sports one).
    assert "technology gadget launch" in titles
    assert any("sports" in t for t in titles)


def test_fills_remaining_slots_when_one_interest_dominates() -> None:
    """If only one interest has stories, it may fill all slots (no starving)."""
    ranked = [
        _ranked("sports one", 0.9),
        _ranked("sports two", 0.8),
        _ranked("sports three", 0.7),
    ]
    top = NewsService._select_top(ranked, ["sports", "technology"], top_n=3)
    assert len(top) == 3  # all sports, since tech had no stories
