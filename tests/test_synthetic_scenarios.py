from __future__ import annotations

import pytest

from grow.access.models import AccessCategory, AccessDecision
from grow.assessments.models import Contradiction
from grow.participants.models import MinorStatus, ParticipantIdentifier
from grow.reviews.models import HumanReview
from grow.synthetic.scenarios import SCENARIOS, create_synthetic_scenarios


@pytest.mark.django_db
def test_all_required_synthetic_scenarios_exist() -> None:
    created = create_synthetic_scenarios()
    expected = {
        "grade-8-minor",
        "grade-10-minor",
        "intermediate-student",
        "university-student",
        "graduate",
        "adult-career-switcher",
        "unknown-age",
        "guardian-handling-required",
        "contradictory-evidence",
        "human-review-required",
        "reduced-fee-candidate",
        "free-access-candidate",
    }
    assert set(created) == expected
    assert len(created) == len(SCENARIOS) == 12


@pytest.mark.django_db
def test_synthetic_fixtures_are_idempotent() -> None:
    first = create_synthetic_scenarios()
    second = create_synthetic_scenarios()
    assert {key: value.id for key, value in first.items()} == {
        key: value.id for key, value in second.items()
    }


@pytest.mark.django_db
def test_synthetic_identifiers_are_hashes_not_contacts() -> None:
    create_synthetic_scenarios()
    identifiers = ParticipantIdentifier.objects.all()
    assert identifiers.count() == 12
    assert all(len(item.lookup_digest) == 64 for item in identifiers)
    assert all(item.ciphertext == "" for item in identifiers)


@pytest.mark.django_db
def test_minor_unknown_and_guardian_cases_are_explicit() -> None:
    scenarios = create_synthetic_scenarios()
    assert scenarios["grade-8-minor"].profile.minor_status == MinorStatus.MINOR
    assert scenarios["unknown-age"].profile.minor_status == MinorStatus.UNKNOWN
    assert scenarios["guardian-handling-required"].guardian_relationships.exists()


@pytest.mark.django_db
def test_contradiction_and_review_scenarios_are_present() -> None:
    scenarios = create_synthetic_scenarios()
    contradiction_journey = scenarios["contradictory-evidence"].journeys.get()
    review_journey = scenarios["human-review-required"].journeys.get()
    assert Contradiction.objects.filter(journey=contradiction_journey).exists()
    assert HumanReview.objects.filter(journey=review_journey).exists()


@pytest.mark.django_db
def test_access_candidates_remain_pending_human_decisions() -> None:
    scenarios = create_synthetic_scenarios()
    reduced = AccessDecision.objects.get(participant=scenarios["reduced-fee-candidate"])
    free = AccessDecision.objects.get(participant=scenarios["free-access-candidate"])
    assert reduced.candidate_category == AccessCategory.REDUCED
    assert free.candidate_category == AccessCategory.FREE
    assert reduced.status == free.status == AccessDecision.DecisionStatus.PENDING
    assert reduced.final_category == free.final_category == AccessCategory.UNKNOWN
