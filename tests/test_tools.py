"""
Tests for tools.py — one test per documented failure mode, plus basic happy-path checks.

LLM-backed tools (suggest_outfit, create_fit_card) are tested with a mocked Groq client
so these tests run offline without consuming API credits.
"""

from unittest.mock import MagicMock, patch

import pytest

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe, load_listings


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_item():
    """A real listing from the dataset to use as new_item in LLM tool tests."""
    return load_listings()[0]


@pytest.fixture
def mock_groq(monkeypatch):
    """Patch _get_groq_client so no real API call is made."""
    fake_message = MagicMock()
    fake_message.content = "Stubbed LLM response."
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    monkeypatch.setattr("tools._get_groq_client", lambda: fake_client)
    return fake_client


# ── search_listings ───────────────────────────────────────────────────────────

class TestSearchListings:
    def test_no_results_returns_empty_list(self):
        # Failure mode: impossible filters — must return [] not raise
        result = search_listings("designer ballgown", size="XXS", max_price=5.0)
        assert result == []

    def test_no_results_does_not_raise(self):
        # Confirm the empty-list contract explicitly
        try:
            search_listings("nonexistent xyzzy item", size="XXS", max_price=0.01)
        except Exception as exc:
            pytest.fail(f"search_listings raised unexpectedly: {exc}")

    def test_price_filter_respected(self):
        results = search_listings("jacket", max_price=30.0)
        assert all(item["price"] <= 30.0 for item in results)

    def test_size_filter_case_insensitive(self):
        # "m" should match listings sized "M", "S/M", "M/L"
        results = search_listings("jacket", size="m")
        assert results
        assert all("m" in item["size"].lower() for item in results)

    def test_results_sorted_by_relevance(self):
        results = search_listings("vintage graphic tee")
        assert results  # at least one match
        # First result must contain more query keywords than last
        def hits(item):
            text = f"{item['title']} {item['description']} {' '.join(item['style_tags'])}".lower()
            return sum(1 for w in ["vintage", "graphic", "tee"] if w in text)
        assert hits(results[0]) >= hits(results[-1])

    def test_zero_score_items_excluded(self):
        # "vintage graphic tee" should not return, e.g., a shoe with no matching keywords
        results = search_listings("vintage graphic tee")
        for item in results:
            text = f"{item['title']} {item['description']} {' '.join(item['style_tags'])}".lower()
            assert any(w in text for w in ["vintage", "graphic", "tee"])


# ── suggest_outfit ────────────────────────────────────────────────────────────

class TestSuggestOutfit:
    def test_empty_wardrobe_does_not_crash(self, sample_item, mock_groq):
        # Failure mode: wardrobe["items"] is [] — must not raise
        result = suggest_outfit(sample_item, get_empty_wardrobe())
        assert isinstance(result, str)
        assert result.strip()

    def test_empty_wardrobe_calls_llm(self, sample_item, mock_groq):
        suggest_outfit(sample_item, get_empty_wardrobe())
        assert mock_groq.chat.completions.create.called

    def test_populated_wardrobe_calls_llm(self, sample_item, mock_groq):
        result = suggest_outfit(sample_item, get_example_wardrobe())
        assert mock_groq.chat.completions.create.called
        assert isinstance(result, str)
        assert result.strip()

    def test_returns_nonempty_string(self, sample_item, mock_groq):
        result = suggest_outfit(sample_item, get_example_wardrobe())
        assert len(result) > 0


# ── create_fit_card ───────────────────────────────────────────────────────────

class TestCreateFitCard:
    def test_empty_outfit_returns_error_string(self, sample_item):
        # Failure mode: empty outfit — must return error string, not raise
        result = create_fit_card("", sample_item)
        assert isinstance(result, str)
        assert result.strip()

    def test_whitespace_outfit_returns_error_string(self, sample_item):
        result = create_fit_card("   ", sample_item)
        assert isinstance(result, str)
        assert result.strip()

    def test_empty_outfit_does_not_raise(self, sample_item):
        try:
            create_fit_card("", sample_item)
        except Exception as exc:
            pytest.fail(f"create_fit_card raised on empty outfit: {exc}")

    def test_valid_outfit_calls_llm(self, sample_item, mock_groq):
        result = create_fit_card("Pair with baggy jeans and chunky sneakers.", sample_item)
        assert mock_groq.chat.completions.create.called
        assert isinstance(result, str)
        assert result.strip()

    def test_empty_outfit_does_not_call_llm(self, sample_item, mock_groq):
        # Guard should short-circuit before the API call
        create_fit_card("", sample_item)
        assert not mock_groq.chat.completions.create.called
