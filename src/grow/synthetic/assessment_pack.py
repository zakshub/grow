from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from grow.assessments.engine import evaluate_assessment_session
from grow.assessments.models import (
    AssessmentDefinition,
    AssessmentDimension,
    AssessmentDimensionRequirement,
    AssessmentItem,
    AssessmentItemPresentation,
    AssessmentItemVariant,
    AssessmentLifecycle,
    AssessmentSection,
    AssessmentSession,
    AssessmentVersion,
    DimensionCategory,
)
from grow.assessments.services import (
    detect_contradictions,
    publish_assessment_version,
    record_assessment_response,
    start_assessment_session,
)
from grow.participants.models import EducationStage, Participant
from grow.synthetic.scenarios import create_synthetic_scenarios

DIMENSION_CATALOG: dict[str, tuple[str, ...]] = {
    DimensionCategory.COGNITIVE_FUNCTIONAL: (
        "Logical reasoning",
        "Numerical reasoning",
        "Verbal reasoning",
        "Verbal expression",
        "Written expression",
        "Spatial reasoning",
        "Pattern recognition",
        "Attention to detail",
        "Planning",
        "Problem decomposition",
        "Research ability",
        "Digital fluency",
        "Practical reasoning",
        "Visual composition",
        "Idea generation",
    ),
    DimensionCategory.PERSONALITY_WORK_STYLE: (
        "Social energy",
        "Openness",
        "Conscientiousness",
        "Structure preference",
        "Flexibility",
        "Independence",
        "Collaboration",
        "Ambiguity tolerance",
        "Risk tolerance",
        "Initiative",
        "Persistence",
        "Adaptability",
        "Stress tolerance",
    ),
    DimensionCategory.COMMUNICATION_SOCIAL: (
        "Listening",
        "Explanation",
        "Persuasion",
        "Negotiation",
        "Empathy",
        "Conflict handling",
        "Facilitation",
        "Leadership preference",
        "Group coordination",
        "Public speaking comfort",
    ),
    DimensionCategory.CREATIVITY: (
        "Visual creativity",
        "Verbal creativity",
        "Storytelling",
        "Concept generation",
        "Problem reframing",
        "Product thinking",
        "Improvisation",
        "Systems creativity",
        "Spatial creativity",
        "Craft and making",
    ),
    DimensionCategory.VOCATIONAL_INTEREST: (
        "Practical hands-on",
        "Investigative analytical",
        "Creative expressive",
        "Social helping",
        "Enterprising persuasive",
        "Organised process-oriented",
    ),
    DimensionCategory.WORK_VALUE: (
        "Income",
        "Stability",
        "Independence value",
        "Creativity value",
        "Social impact",
        "Recognition",
        "Prestige",
        "Learning",
        "Leadership value",
        "Flexibility value",
        "Remote work",
        "Predictability",
        "Fast earning entry",
        "International mobility",
        "Work-life balance",
        "Variety",
        "Deep expertise",
    ),
    DimensionCategory.WORK_ENVIRONMENT: (
        "Quiet vs socially active",
        "Structured vs open-ended",
        "Desk vs physical",
        "Indoor vs field",
        "Individual vs collaborative",
        "Stable vs changing",
        "Long projects vs short cycles",
        "Abstract vs concrete",
        "Customer-facing vs behind-the-scenes",
        "Local vs travel-oriented",
    ),
}


def dimension_code(name: str) -> str:
    return (
        name.lower().replace("/", " ").replace("-", " ").replace("vs", "versus").replace(" ", "_")
    )


REQUIRED_DIMENSIONS = (
    "logical_reasoning",
    "verbal_expression",
    "planning",
    "ambiguity_tolerance",
    "public_speaking_comfort",
    "creative_expressive",
    "investigative_analytical",
    "idea_generation",
)


LIKERT_OPTIONS = ["strongly_disagree", "disagree", "agree", "strongly_agree"]
LIKERT_RULES: dict[str, object] = {
    "map": {
        "strongly_disagree": {
            "signal": "negative",
            "polarity": -1,
            "direction": "conflicts",
            "confidence_band": "low",
            "confidence_score": "0.35",
        },
        "disagree": {
            "signal": "negative",
            "polarity": -0.6,
            "direction": "conflicts",
            "confidence_band": "low",
            "confidence_score": "0.30",
        },
        "agree": {
            "signal": "positive",
            "polarity": 0.6,
            "direction": "supports",
            "confidence_band": "low",
            "confidence_score": "0.30",
        },
        "strongly_agree": {
            "signal": "positive",
            "polarity": 1,
            "direction": "supports",
            "confidence_band": "low",
            "confidence_score": "0.35",
        },
    }
}


@dataclass(frozen=True)
class ItemSeed:
    code: str
    dimension: str
    item_type: str
    purpose: str
    urdu: str
    english: str


ITEM_SEEDS = (
    ItemSeed(
        "logic_pattern",
        "logical_reasoning",
        AssessmentItem.ItemType.SINGLE_CHOICE,
        AssessmentItem.Purpose.CORE,
        "اگر ترتیب 2، 4، 8، 16 ہو تو اگلا عدد کیا ہوگا؟",
        "If the sequence is 2, 4, 8, 16, what comes next?",
    ),
    ItemSeed(
        "logic_process",
        "logical_reasoning",
        AssessmentItem.ItemType.LIKERT,
        AssessmentItem.Purpose.CORE,
        "مجھے کسی بڑے مسئلے کو چھوٹے مرحلوں میں تقسیم کرنا پسند ہے۔",
        "I like breaking a large problem into smaller steps.",
    ),
    ItemSeed(
        "investigative_interest",
        "investigative_analytical",
        AssessmentItem.ItemType.LIKERT,
        AssessmentItem.Purpose.CORE,
        "میں کسی سوال کی وجہ جاننے کے لیے خود مزید تحقیق کرتا یا کرتی ہوں۔",
        "I investigate further on my own to understand why something happens.",
    ),
    ItemSeed(
        "creative_expression",
        "creative_expressive",
        AssessmentItem.ItemType.LIKERT,
        AssessmentItem.Purpose.CORE,
        "مجھے نئی چیز، کہانی یا ڈیزائن بنانے میں دلچسپی ہوتی ہے۔",
        "I enjoy creating a new object, story, or design.",
    ),
    ItemSeed(
        "verbal_explanation",
        "verbal_expression",
        AssessmentItem.ItemType.LIKERT,
        AssessmentItem.Purpose.CORE,
        "میں کسی مشکل بات کو آسان الفاظ میں سمجھا سکتا یا سکتی ہوں۔",
        "I can explain a difficult idea in simple words.",
    ),
    ItemSeed(
        "public_speaking_self_report",
        "public_speaking_comfort",
        AssessmentItem.ItemType.LIKERT,
        AssessmentItem.Purpose.CORE,
        "مجھے لوگوں کے سامنے بات کرنے میں آسانی محسوس ہوتی ہے۔",
        "I feel comfortable speaking in front of a group.",
    ),
    ItemSeed(
        "public_speaking_clarification",
        "public_speaking_comfort",
        AssessmentItem.ItemType.SCENARIO_CHOICE,
        AssessmentItem.Purpose.CLARIFICATION,
        "اگر گروپ آپ سے مختصر بات کرنے کو کہے تو آپ کا زیادہ ممکن ردعمل کیا ہوگا؟",
        "If a group asks you to speak briefly, what are you most likely to do?",
    ),
    ItemSeed(
        "planning_habit",
        "planning",
        AssessmentItem.ItemType.LIKERT,
        AssessmentItem.Purpose.CORE,
        "کسی کام سے پہلے میں اس کے مرحلے طے کرتا یا کرتی ہوں۔",
        "Before a task, I usually plan its steps.",
    ),
    ItemSeed(
        "ambiguity_response",
        "ambiguity_tolerance",
        AssessmentItem.ItemType.LIKERT,
        AssessmentItem.Purpose.CORE,
        "جب ہدایات مکمل نہ ہوں تب بھی میں کام شروع کرنے کا طریقہ ڈھونڈ لیتا یا لیتی ہوں۔",
        "I can find a way to begin when instructions are incomplete.",
    ),
    ItemSeed(
        "open_help_story",
        "verbal_expression",
        AssessmentItem.ItemType.LONG_TEXT,
        AssessmentItem.Purpose.OPEN_DISCOVERY,
        "لوگ عموماً کس قسم کا مسئلہ حل کرنے کے لیے آپ سے مدد مانگتے ہیں؟",
        "What kind of problems do people usually ask you to help solve?",
    ),
    ItemSeed(
        "open_self_learning",
        "investigative_analytical",
        AssessmentItem.ItemType.LONG_TEXT,
        AssessmentItem.Purpose.OPEN_DISCOVERY,
        "آپ اپنی مرضی سے کس چیز کے بارے میں سیکھتے ہیں؟",
        "What do you learn about without anyone telling you to?",
    ),
    ItemSeed(
        "open_lost_time",
        "creative_expressive",
        AssessmentItem.ItemType.LONG_TEXT,
        AssessmentItem.Purpose.OPEN_DISCOVERY,
        "کون سا کام کرتے ہوئے آپ کو وقت گزرنے کا احساس نہیں رہتا؟",
        "What activity makes you lose track of time?",
    ),
    ItemSeed(
        "open_boredom",
        "ambiguity_tolerance",
        AssessmentItem.ItemType.LONG_TEXT,
        AssessmentItem.Purpose.OPEN_DISCOVERY,
        "کس قسم کا کام آپ کو بہت جلد بور کر دیتا ہے؟",
        "What kind of work becomes boring very quickly?",
    ),
    ItemSeed(
        "open_proud_example",
        "idea_generation",
        AssessmentItem.ItemType.LONG_TEXT,
        AssessmentItem.Purpose.OPEN_DISCOVERY,
        "کسی ایسی چیز کے بارے میں بتائیں جسے بنا کر، حل کر کے یا سمجھا کر آپ کو فخر ہوا۔",
        "Tell us about something you made, solved, or explained that made you proud.",
    ),
)


AUDIENCE_EDUCATION = {
    AssessmentItemVariant.Audience.GRADE_8_10: (
        EducationStage.GRADE_8,
        EducationStage.GRADE_10,
    ),
    AssessmentItemVariant.Audience.INTERMEDIATE: (EducationStage.INTERMEDIATE,),
    AssessmentItemVariant.Audience.UNIVERSITY: (EducationStage.UNIVERSITY,),
    AssessmentItemVariant.Audience.GRADUATE: (EducationStage.GRADUATE,),
    AssessmentItemVariant.Audience.ADULT_CAREER_SWITCHER: (
        EducationStage.GRADUATE,
        EducationStage.OTHER,
    ),
}


AUDIENCE_URDU_HELPERS = {
    AssessmentItemVariant.Audience.GRADE_8_10: "اسکول یا روزمرہ زندگی کی مثال ذہن میں رکھیں۔",
    AssessmentItemVariant.Audience.INTERMEDIATE: "پڑھائی یا روزمرہ تجربے کی مثال ذہن میں رکھیں۔",
    AssessmentItemVariant.Audience.UNIVERSITY: "یونیورسٹی، منصوبے یا روزمرہ تجربے کو سامنے رکھیں۔",
    AssessmentItemVariant.Audience.GRADUATE: "تعلیم، کام یا روزمرہ تجربے کو سامنے رکھیں۔",
    AssessmentItemVariant.Audience.ADULT_CAREER_SWITCHER: (
        "اپنے سابقہ کام اور موجودہ زندگی دونوں کو سامنے رکھیں۔"
    ),
}


ASSESSMENT_SCENARIOS = {
    "grade-8-learner-unsure": "grade-8-minor",
    "matric-logical-investigative": "grade-10-minor",
    "intermediate-creative-communication": "intermediate-student",
    "university-conflicting-preferences": "university-student",
    "graduate-uncertain-direction": "graduate",
    "adult-career-switcher-assessment": "adult-career-switcher",
    "highly-contradictory-self-report": "contradictory-evidence",
    "mostly-unknown-dimensions": "unknown-age",
    "stopped-assessment-early": "reduced-fee-candidate",
    "assessment-human-review-required": "human-review-required",
}


def _create_catalog() -> dict[str, AssessmentDimension]:
    dimensions: dict[str, AssessmentDimension] = {}
    for category, names in DIMENSION_CATALOG.items():
        for name in names:
            code = dimension_code(name)
            dimension, _ = AssessmentDimension.objects.get_or_create(
                code=code,
                defaults={
                    "category": category,
                    "name": name,
                    "description": (
                        "Synthetic pilot engineering taxonomy; not a validated construct."
                    ),
                },
            )
            dimensions[code] = dimension
    return dimensions


def _rules_for(seed: ItemSeed) -> tuple[dict[str, object], dict[str, object]]:
    if seed.code == "logic_pattern":
        return (
            {"options": ["24", "30", "32", "36"]},
            {
                "map": {
                    "32": {
                        "signal": "positive",
                        "polarity": 1,
                        "direction": "supports",
                        "confidence_band": "low",
                        "confidence_score": "0.40",
                    },
                    "24": {
                        "signal": "negative",
                        "polarity": -0.5,
                        "direction": "conflicts",
                        "confidence_band": "low",
                        "confidence_score": "0.25",
                    },
                    "30": {
                        "signal": "negative",
                        "polarity": -0.5,
                        "direction": "conflicts",
                        "confidence_band": "low",
                        "confidence_score": "0.25",
                    },
                    "36": {
                        "signal": "negative",
                        "polarity": -0.5,
                        "direction": "conflicts",
                        "confidence_band": "low",
                        "confidence_score": "0.25",
                    },
                }
            },
        )
    if seed.code == "public_speaking_clarification":
        return (
            {"options": ["volunteer", "accept_if_asked", "avoid"]},
            {
                "map": {
                    "volunteer": {
                        "signal": "positive",
                        "polarity": 1,
                        "direction": "supports",
                        "confidence_band": "low",
                        "confidence_score": "0.35",
                    },
                    "accept_if_asked": {
                        "signal": "mixed",
                        "polarity": 0.2,
                        "direction": "neutral",
                        "confidence_band": "low",
                        "confidence_score": "0.25",
                    },
                    "avoid": {
                        "signal": "negative",
                        "polarity": -1,
                        "direction": "conflicts",
                        "confidence_band": "low",
                        "confidence_score": "0.35",
                    },
                }
            },
        )
    if seed.item_type == AssessmentItem.ItemType.LIKERT:
        return {"options": LIKERT_OPTIONS}, LIKERT_RULES
    return {}, {}


def _create_definition(dimensions: dict[str, AssessmentDimension]) -> AssessmentVersion:
    definition, _ = AssessmentDefinition.objects.get_or_create(
        code="grow-synthetic-pilot",
        defaults={
            "title": "Grow synthetic progressive discovery pack",
            "purpose": (
                "Exercise deterministic assessment architecture with synthetic content only."
            ),
        },
    )
    existing = AssessmentVersion.objects.filter(definition=definition, version=1).first()
    if existing:
        return existing
    version = AssessmentVersion.objects.create(
        definition=definition,
        version=1,
        maximum_items=12,
        limitations=(
            "Synthetic Urdu/English pilot content for engineering tests only; not "
            "psychometrically, "
            "clinically, culturally, or operationally validated."
        ),
    )
    structured = AssessmentSection.objects.create(
        assessment_version=version,
        code="structured",
        order=1,
        title="Synthetic structured signals",
    )
    open_discovery = AssessmentSection.objects.create(
        assessment_version=version,
        code="open-discovery",
        order=2,
        title="Synthetic open discovery",
    )
    for priority, code in enumerate(REQUIRED_DIMENSIONS, start=1):
        AssessmentDimensionRequirement.objects.create(
            assessment_version=version,
            dimension=dimensions[code],
            required=True,
            priority=priority,
            minimum_independent_sources=2,
            minimum_source_types=2,
        )
    for order, seed in enumerate(ITEM_SEEDS, start=1):
        response_schema, interpretation_rules = _rules_for(seed)
        item = AssessmentItem.objects.create(
            assessment_version=version,
            section=(
                open_discovery
                if seed.purpose == AssessmentItem.Purpose.OPEN_DISCOVERY
                else structured
            ),
            dimension=dimensions[seed.dimension],
            code=seed.code,
            item_type=seed.item_type,
            purpose=seed.purpose,
            order=order,
            response_schema=response_schema,
            interpretation_rules=interpretation_rules,
            evidence_source_type="self_report",
        )
        for audience, education_stages in AUDIENCE_EDUCATION.items():
            for education in education_stages:
                AssessmentItemVariant.objects.create(
                    item=item,
                    language="ur",
                    locale="pk",
                    audience=audience,
                    education_stage=education,
                    prompt=seed.urdu,
                    helper_text=AUDIENCE_URDU_HELPERS[audience],
                    answer_labels=(
                        {
                            "strongly_disagree": "بالکل متفق نہیں",
                            "disagree": "متفق نہیں",
                            "agree": "متفق",
                            "strongly_agree": "مکمل متفق",
                        }
                        if seed.item_type == AssessmentItem.ItemType.LIKERT
                        else {}
                    ),
                )
        AssessmentItemVariant.objects.create(
            item=item,
            language="en",
            locale="pk",
            audience=AssessmentItemVariant.Audience.GENERAL,
            education_stage=EducationStage.UNKNOWN,
            prompt=seed.english,
            helper_text="Synthetic internal fallback wording.",
        )
    publish_assessment_version(
        assessment_version=version,
        lifecycle=AssessmentLifecycle.PILOT,
        actor_reference="synthetic-pack-builder",
    )
    return version


def _audience(participant: Participant) -> str:
    education = participant.profile.education_stage
    if participant.life_stage_track == "career_reset":
        return AssessmentItemVariant.Audience.ADULT_CAREER_SWITCHER
    if education in {EducationStage.GRADE_8, EducationStage.GRADE_10}:
        return AssessmentItemVariant.Audience.GRADE_8_10
    if education == EducationStage.INTERMEDIATE:
        return AssessmentItemVariant.Audience.INTERMEDIATE
    if education == EducationStage.UNIVERSITY:
        return AssessmentItemVariant.Audience.UNIVERSITY
    if education == EducationStage.GRADUATE:
        return AssessmentItemVariant.Audience.GRADUATE
    return AssessmentItemVariant.Audience.GENERAL


def _respond(session: AssessmentSession, item_code: str, value: object) -> None:
    assessment_version = session.assessment_version
    assert assessment_version is not None
    item = assessment_version.items.get(code=item_code)
    variant = (
        item.variants.filter(language="ur", audience=session.audience).first()
        or item.variants.filter(language="en", audience="general").first()
    )
    assert variant is not None
    presentation = AssessmentItemPresentation.objects.create(
        session=session,
        item=item,
        variant=variant,
        sequence=session.presentations.count() + 1,
        selection_status="ASK_MORE",
        selection_reason="Synthetic scenario setup",
        selection_policy_version=assessment_version.selection_policy_version,
    )
    if item.item_type in {AssessmentItem.ItemType.SHORT_TEXT, AssessmentItem.ItemType.LONG_TEXT}:
        record_assessment_response(
            presentation=presentation,
            text_value=str(value),
            actor_type="synthetic_fixture",
        )
    else:
        record_assessment_response(
            presentation=presentation,
            structured_value=value,
            actor_type="synthetic_fixture",
        )


@transaction.atomic
def create_synthetic_assessment_pack() -> dict[str, AssessmentSession]:
    participants = create_synthetic_scenarios()
    dimensions = _create_catalog()
    version = _create_definition(dimensions)
    sessions: dict[str, AssessmentSession] = {}
    answer_plan: dict[str, tuple[tuple[str, object], ...]] = {
        "grade-8-learner-unsure": (("open_self_learning", "مصنوعی جواب: ابھی واضح نہیں۔"),),
        "matric-logical-investigative": (
            ("logic_pattern", "32"),
            ("logic_process", "agree"),
            ("investigative_interest", "strongly_agree"),
        ),
        "intermediate-creative-communication": (
            ("creative_expression", "strongly_agree"),
            ("verbal_explanation", "agree"),
            ("open_proud_example", "مصنوعی جواب: ایک پوسٹر بنایا اور سمجھایا۔"),
        ),
        "university-conflicting-preferences": (
            ("public_speaking_self_report", "strongly_agree"),
            ("public_speaking_clarification", "avoid"),
            ("open_boredom", "مصنوعی جواب: اپنی پسند اور خاندانی توقع میں فرق ہے۔"),
        ),
        "graduate-uncertain-direction": (
            ("open_help_story", "مصنوعی جواب: مختلف کاموں میں مدد کرتا ہوں مگر سمت واضح نہیں۔"),
        ),
        "adult-career-switcher-assessment": (
            ("planning_habit", "agree"),
            ("ambiguity_response", "agree"),
        ),
        "highly-contradictory-self-report": (
            ("public_speaking_self_report", "strongly_agree"),
            ("public_speaking_clarification", "avoid"),
        ),
        "mostly-unknown-dimensions": (),
        "stopped-assessment-early": (("creative_expression", "agree"),),
        "assessment-human-review-required": (("logic_pattern", "24"),),
    }
    for scenario_code, participant_code in ASSESSMENT_SCENARIOS.items():
        participant = participants[participant_code]
        existing = AssessmentSession.objects.filter(
            journey__participant=participant,
            assessment_version=version,
            definition_code=version.definition.code,
        ).first()
        if existing:
            sessions[scenario_code] = existing
            continue
        session = start_assessment_session(
            journey=participant.journeys.get(is_active=True),
            assessment_version=version,
            audience=_audience(participant),
            maximum_items=(1 if scenario_code == "assessment-human-review-required" else None),
            actor_type="synthetic_fixture",
        )
        for item_code, value in answer_plan[scenario_code]:
            _respond(session, item_code, value)
        if scenario_code == "stopped-assessment-early":
            session.status = AssessmentSession.SessionStatus.STOPPED_EARLY
            session.sufficiency_status = AssessmentSession.SufficiencyStatus.INSUFFICIENT
            session.save(update_fields=["status", "sufficiency_status", "updated_at"])
        detect_contradictions(session=session, actor_type="synthetic_fixture")
        if scenario_code == "assessment-human-review-required":
            evaluate_assessment_session(session=session, actor_reference="synthetic-pack-builder")
        sessions[scenario_code] = session
    return sessions
