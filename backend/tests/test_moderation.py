"""`analyze_review_with_hf` üç bantlı karar mantığı testleri.

Gerçek HuggingFace servisine gidilmez: `moderation.httpx.AsyncClient` sahte bir sınıfla
değiştirilip HF yanıtı doğrudan üretilir.
"""

import asyncio

import pytest

from app.services import moderation
from app.services.moderation import ModerationStatus, analyze_review_with_hf


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, *args, **kwargs):
        return self._response


@pytest.fixture()
def hf_response(monkeypatch):
    """HF yanıtını sahteleyen fabrika. Skor listesi verilir, `ModerationStatus` döner."""
    monkeypatch.setattr(moderation.settings, "HF_API_TOKEN", "test-token")

    def _run(predictions, status_code=200):
        response = _FakeResponse([predictions], status_code=status_code)
        monkeypatch.setattr(moderation.httpx, "AsyncClient", lambda *a, **kw: _FakeClient(response))
        return asyncio.run(analyze_review_with_hf("bir yorum"))

    return _run


def _preds(**scores):
    return [{"label": label, "score": score} for label, score in scores.items()]


class TestModerationBands:
    def test_above_reject_threshold_is_rejected(self, hf_response):
        assert hf_response(_preds(toxic=0.95)) == ModerationStatus.REJECTED

    def test_just_above_reject_threshold_is_rejected(self, hf_response):
        assert hf_response(_preds(insult=0.71)) == ModerationStatus.REJECTED

    def test_exactly_reject_threshold_is_pending(self, hf_response):
        assert hf_response(_preds(toxic=0.70)) == ModerationStatus.PENDING

    def test_middle_band_is_pending(self, hf_response):
        assert hf_response(_preds(toxic=0.55)) == ModerationStatus.PENDING

    def test_exactly_pending_threshold_is_pending(self, hf_response):
        assert hf_response(_preds(obscene=0.35)) == ModerationStatus.PENDING

    def test_just_below_pending_threshold_is_approved(self, hf_response):
        assert hf_response(_preds(toxic=0.34)) == ModerationStatus.APPROVED

    def test_clean_text_is_approved(self, hf_response):
        assert hf_response(_preds(toxic=0.001, insult=0.002)) == ModerationStatus.APPROVED

    def test_max_score_across_labels_wins(self, hf_response):
        """İlk etiket temiz olsa bile en yüksek skor karar verir (eski kod ilkinde duruyordu)."""
        assert hf_response(_preds(toxic=0.01, threat=0.80)) == ModerationStatus.REJECTED

    def test_middle_band_from_non_first_label(self, hf_response):
        assert hf_response(_preds(toxic=0.02, identity_hate=0.50)) == ModerationStatus.PENDING

    def test_unknown_labels_ignored(self, hf_response):
        """TOXIC_LABELS dışındaki yüksek skor karara girmez; tanınan etiket kararı verir."""
        assert hf_response(
            [{"label": "neutral", "score": 0.99}, {"label": "toxic", "score": 0.01}]
        ) == ModerationStatus.APPROVED


class TestModerationFallbacks:
    def test_empty_text_is_approved_without_request(self, monkeypatch):
        monkeypatch.setattr(moderation.settings, "HF_API_TOKEN", "test-token")
        assert asyncio.run(analyze_review_with_hf("   ")) == ModerationStatus.APPROVED

    def test_missing_token_falls_back_to_pending(self, monkeypatch):
        monkeypatch.setattr(moderation.settings, "HF_API_TOKEN", "")
        assert asyncio.run(analyze_review_with_hf("bir yorum")) == ModerationStatus.PENDING

    def test_no_known_label_falls_back_to_pending(self, hf_response):
        """Model veya etiket adları değişirse karar "temiz" sayılmaz, insan onayına düşer."""
        assert hf_response([{"label": "neutral", "score": 0.99}]) == ModerationStatus.PENDING

    def test_empty_predictions_fall_back_to_pending(self, hf_response):
        assert hf_response([]) == ModerationStatus.PENDING

    def test_labelless_dict_falls_back_to_pending(self, hf_response):
        assert hf_response([{"score": 0.99}]) == ModerationStatus.PENDING

    def test_non_200_falls_back_to_pending(self, hf_response):
        assert hf_response(_preds(toxic=0.01), status_code=503) == ModerationStatus.PENDING
