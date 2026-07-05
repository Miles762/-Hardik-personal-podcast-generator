"""Phase 2 unit tests: ranking scorer (PRD 7, 11.5). Pure, deterministic."""

from datetime import UTC, datetime, timedelta

from app.schemas.news import Article
from app.services.news.ranking import (
    RankWeights,
    freshness_score,
    interest_score,
    popularity_score,
    rank_articles,
    score_article,
    source_trust_score,
)


def _article(**kw) -> Article:
    base = dict(
        title="t",
        source="BBC",
        url="https://x.com/a",
        published_at=datetime.now(UTC),
        content="",
    )
    base.update(kw)
    return Article(**base)


def test_interest_score_zero_without_interests() -> None:
    assert interest_score(_article(title="space rocket"), []) == 0.0


def test_interest_score_rewards_overlap() -> None:
    match = _article(title="NASA space rocket launch", content="space mission to mars")
    nomatch = _article(title="local bakery opens downtown", content="bread and pastries")
    interests = ["space", "rocket", "mars"]
    assert interest_score(match, interests) > interest_score(nomatch, interests)


def test_all_subscores_normalized_0_1() -> None:
    a = _article(popularity=5000, source="BBC")
    r = score_article(a, ["t"])
    for name, v in r.subscores.items():
        assert 0.0 <= v <= 1.0, f"{name}={v} out of range"
    assert 0.0 <= r.score <= 1.0


def test_freshness_decays_with_age() -> None:
    now = datetime(2025, 1, 1, 12, tzinfo=UTC)
    fresh = freshness_score(now, now=now)
    half = freshness_score(now - timedelta(hours=12), now=now)  # one half-life
    old = freshness_score(now - timedelta(hours=48), now=now)
    assert fresh == 1.0
    assert abs(half - 0.5) < 1e-9
    assert old < half < fresh


def test_popularity_log_scaled_and_capped() -> None:
    assert popularity_score(0) == 0.0
    assert popularity_score(10) < popularity_score(100) < popularity_score(1000)
    assert popularity_score(10_000) <= 1.0


def test_source_trust_known_vs_unknown() -> None:
    assert source_trust_score("BBC") > source_trust_score("SomeBlog")


def test_weighting_matches_formula() -> None:
    """Score equals exactly w·subscores with default weights (0.5,0.2,0.2,0.1)."""
    now = datetime(2025, 1, 1, 12, tzinfo=UTC)
    a = _article(title="space", content="space", popularity=100, published_at=now)
    r = score_article(a, ["space"], now=now)
    w = RankWeights()
    expected = (
        w.interest * r.subscores["interest"]
        + w.freshness * r.subscores["freshness"]
        + w.popularity * r.subscores["popularity"]
        + w.source_trust * r.subscores["source_trust"]
    )
    assert abs(r.score - expected) < 1e-12


def test_rank_articles_sorts_descending() -> None:
    now = datetime(2025, 1, 1, 12, tzinfo=UTC)
    relevant = _article(title="space rocket mars", content="space", published_at=now)
    irrelevant = _article(title="cooking recipe", content="food", published_at=now)
    ranked = rank_articles([irrelevant, relevant], ["space", "mars"], now=now)
    assert ranked[0].article.title == "space rocket mars"
    assert ranked[0].score >= ranked[1].score
