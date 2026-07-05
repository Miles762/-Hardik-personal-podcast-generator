"""Phase 4: audio chunking, merge fallback, service, stitching (PRD 9, 11.5).

Fully offline: TTS + storage are fakes, merge is exercised via its byte-concat
fallback path (no ffmpeg needed in the pure unit tests).
"""

from app.services.audio.chunk import MAX_CHUNK_CHARS, chunk_script
from app.services.audio.merge import _merge_by_concat, merge_audio
from app.services.audio.service import AudioService
from tests.fakes import FakeStorage, FakeTTSClient


def test_chunk_splits_on_paragraphs() -> None:
    script = "Para one.\n\nPara two.\n\nPara three."
    chunks = chunk_script(script)
    assert [c.text for c in chunks] == ["Para one.", "Para two.", "Para three."]


def test_chunk_stitching_hints_point_to_neighbors() -> None:
    chunks = chunk_script("Alpha.\n\nBravo.\n\nCharlie.")
    assert chunks[0].previous_text == ""            # first has no previous
    assert chunks[0].next_text.startswith("Bravo")
    assert chunks[1].previous_text.endswith("Alpha.")
    assert chunks[-1].next_text == ""               # last has no next


def test_chunk_long_paragraph_splits_under_cap() -> None:
    long_para = " ".join(f"Sentence number {i} here." for i in range(200))
    chunks = chunk_script(long_para)
    assert len(chunks) > 1
    assert all(len(c.text) <= MAX_CHUNK_CHARS for c in chunks)


def test_merge_concat_fallback_joins_bytes() -> None:
    data, dur = _merge_by_concat([b"aaa", b"bbb"])
    assert data == b"aaabbb"
    assert dur >= 0


async def test_merge_empty_is_zero() -> None:
    data, dur = await merge_audio([])
    assert data == b""
    assert dur == 0


async def test_audio_service_synthesizes_all_chunks(monkeypatch) -> None:
    tts = FakeTTSClient()
    storage = FakeStorage()
    service = AudioService(tts, storage=storage)

    # Bypass ffmpeg: force the merge to a deterministic concat.
    from app.services.audio import service as service_mod

    async def _fake_merge(parts):
        return b"".join(parts), len(parts) * 10

    monkeypatch.setattr(service_mod, "merge_audio", _fake_merge)

    script = "Hello there.\n\nSecond paragraph.\n\nThird and final."
    url, duration = await service.synthesize_episode(
        script, voice_id="voice123", filename="episode_7.mp3"
    )

    assert url == "/audio/episode_7.mp3"
    assert duration == 30                      # 3 chunks * 10
    assert len(tts.calls) == 3
    assert all(c["voice_id"] == "voice123" for c in tts.calls)
    # Stitching: second chunk carries previous/next context (PRD 9).
    assert tts.calls[1]["previous_text"].endswith("Hello there.")
    assert tts.calls[1]["next_text"].startswith("Third")
    assert "episode_7.mp3" in storage.saved


async def test_audio_service_rejects_empty_script() -> None:
    service = AudioService(FakeTTSClient(), storage=FakeStorage())
    try:
        await service.synthesize_episode("   ", voice_id="v", filename="x.mp3")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
