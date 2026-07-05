"""Unit tests for on-topic story selection (PRD 7 ranking, tunable behavior).

When a user has interests, off-topic (zero interest-match) stories are dropped so
a narrow interest yields on-topic content, with a guardrail that never returns an
empty set on a thin-news day.
"""

from datetime import UTC, datetime

from app.schemas.news import Article, RankedArticle
from app.services.news.service import NewsService


def _ranked(title: str, interest: float, score: float) -> RankedArticle:
    return RankedArticle(
        article=Article(
            title=title, source="X", url=f"https://x.com/{title}",
            published_at=datetime.now(UTC),
        ),
        score=score,
        subscores={"interest": interest},
    )


def test_select_top_drops_off_topic_when_interests_present() -> None:
    ranked = [
        _ranked("tech A", interest=0.0, score=0.40),   # off-topic, high score
        _ranked("sport B", interest=0.6, score=0.35),  # on-topic
        _ranked("tech C", interest=0.0, score=0.34),   # off-topic
    ]
    top = NewsService._select_top(ranked, ["sports"], top_n=3)
    assert [r.article.title for r in top] == ["sport B"]  # only on-topic kept


def test_select_top_guardrail_when_no_matches() -> None:
    """If nothing matches, fall back to plain top-N so generation isn't starved."""
    ranked = [
        _ranked("tech A", interest=0.0, score=0.40),
        _ranked("tech B", interest=0.0, score=0.35),
    ]
    top = NewsService._select_top(ranked, ["sports"], top_n=2)
    assert len(top) == 2  # fell back, not empty


def test_select_top_no_interests_returns_plain_top_n() -> None:
    ranked = [_ranked(f"a{i}", interest=0.0, score=1.0 - i * 0.1) for i in range(5)]
    top = NewsService._select_top(ranked, [], top_n=3)
    assert len(top) == 3


def test_select_top_respects_n_among_on_topic() -> None:
    ranked = [_ranked(f"s{i}", interest=0.5, score=1.0 - i * 0.1) for i in range(5)]
    top = NewsService._select_top(ranked, ["sports"], top_n=2)
    assert len(top) == 2
    assert [r.article.title for r in top] == ["s0", "s1"]  # highest scored kept
