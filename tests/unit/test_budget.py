"""Unit tests for BudgetTracker's in-memory fallback (no repository injected)."""

from __future__ import annotations

from sirius.adapters.llm.budget import BudgetPolicy, BudgetTracker


def test_has_remaining_budget_when_nothing_spent() -> None:
    tracker = BudgetTracker(BudgetPolicy(monthly_limit_usd=20.0))

    assert tracker.has_remaining_budget() is True
    assert tracker.is_near_limit() is False


def test_record_usage_computes_cost_from_the_policy() -> None:
    policy = BudgetPolicy(
        input_cost_usd_per_million_tokens=2.0, output_cost_usd_per_million_tokens=4.0
    )
    tracker = BudgetTracker(policy)

    tracker.record_usage(input_tokens=1_000_000, output_tokens=1_000_000)

    assert tracker.spent_usd == 6.0


def test_is_near_limit_once_the_warn_threshold_is_reached() -> None:
    policy = BudgetPolicy(warn_threshold_usd=1.0, input_cost_usd_per_million_tokens=1_000_000.0)
    tracker = BudgetTracker(policy)

    tracker.record_usage(input_tokens=1, output_tokens=0)

    assert tracker.is_near_limit() is True


def test_has_remaining_budget_becomes_false_once_the_monthly_limit_is_hit() -> None:
    policy = BudgetPolicy(monthly_limit_usd=1.0, input_cost_usd_per_million_tokens=1_000_000.0)
    tracker = BudgetTracker(policy)

    tracker.record_usage(input_tokens=1, output_tokens=0)

    assert tracker.has_remaining_budget() is False


def test_without_a_repository_spend_does_not_survive_a_new_instance() -> None:
    """The in-memory fallback is explicitly process-local: a fresh tracker
    (simulating a restart) starts back at zero. Persistence across restarts
    requires injecting a repository (see test_sqlite_llm_usage_repository.py).
    """
    policy = BudgetPolicy(input_cost_usd_per_million_tokens=1_000_000.0)
    first_tracker = BudgetTracker(policy)
    first_tracker.record_usage(input_tokens=1, output_tokens=0)

    second_tracker = BudgetTracker(policy)

    assert second_tracker.spent_usd == 0.0


# --- Gasto de audio (Model Studio, hallazgo MS-A04) ---------------------


def test_transcription_cost_counts_against_the_same_monthly_total() -> None:
    """Sin tabla nueva ni migración: suma al mismo total que el texto."""
    tracker = BudgetTracker()

    tracker.record_usage(input_tokens=1_000_000, output_tokens=0)
    after_text = tracker.spent_usd
    tracker.record_transcription(audio_seconds=600.0)

    assert tracker.spent_usd > after_text


def test_speech_cost_counts_against_the_same_monthly_total() -> None:
    tracker = BudgetTracker()

    tracker.record_speech(character_count=100_000)

    assert tracker.spent_usd > 0.0


def test_audio_spend_can_exhaust_the_budget_and_block_sending() -> None:
    """SV-011 de verdad: si el audio no se apuntara, el tope nunca llegaría."""
    policy = BudgetPolicy(monthly_limit_usd=1.0, transcription_cost_usd_per_minute=0.5)
    tracker = BudgetTracker(policy=policy)

    assert tracker.has_remaining_budget()
    tracker.record_transcription(audio_seconds=120.0)

    assert not tracker.has_remaining_budget()


def test_negative_audio_quantities_never_refund_budget() -> None:
    """Una duración o un recuento absurdos no pueden devolver saldo."""
    tracker = BudgetTracker()
    tracker.record_speech(character_count=50_000)
    spent = tracker.spent_usd

    tracker.record_transcription(audio_seconds=-3600.0)
    tracker.record_speech(character_count=-1_000_000)

    assert tracker.spent_usd == spent
