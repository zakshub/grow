from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.db import transaction

from grow.careers.models import (
    CareerAlias,
    CareerCluster,
    CareerDimensionRelationship,
    CareerEnvironmentObservation,
    CareerFamily,
    CareerPathway,
    CareerProfile,
    CareerProfileVersion,
    CareerRelationship,
    CareerSkill,
    CareerSkillRequirement,
    CareerTaxonomy,
    CareerTaxonomyVersion,
    Confidence,
    DataClassification,
    Freshness,
    Lifecycle,
    MarketObservation,
    OrdinalRelevance,
    ResearchSource,
    ReviewStatus,
)
from grow.careers.services import publish_taxonomy_version, transition_review
from grow.synthetic.assessment_pack import create_dimension_catalog

MARKERS = ["SYNTHETIC", "REFERENCE_ONLY", "NOT_READY_FOR_PARTICIPANT_RECOMMENDATION"]
LIMITATION = (
    "Synthetic reference-only engineering data. It is not researched career guidance, "
    "market truth, or participant-facing advice."
)


@dataclass(frozen=True)
class CareerSeed:
    code: str
    title: str
    title_ur: str
    cluster: str
    family: str
    summary: str
    work: str
    dimensions: tuple[str, ...]
    interests: tuple[str, ...]
    values: tuple[str, ...]
    environments: tuple[str, ...]
    skills: tuple[tuple[str, str, str], ...]
    pathways: tuple[str, ...]
    alias: str


CAREERS = (
    CareerSeed(
        "software-developer",
        "Software Developer",
        "سافٹ ویئر ڈیولپر",
        "Technology",
        "Software",
        "Builds and maintains software systems.",
        "Analysing needs, writing and reviewing code, testing, and collaborating "
        "on software delivery.",
        ("logical_reasoning", "problem_decomposition", "digital_fluency"),
        ("investigative_analytical",),
        ("learning", "deep_expertise"),
        ("desk_versus_physical", "individual_versus_collaborative"),
        (
            ("programming", "Programming", "technical"),
            ("software-collaboration", "Software collaboration", "communication"),
        ),
        ("Skills-first route", "Degree route"),
        "Junior Developer",
    ),
    CareerSeed(
        "data-analyst",
        "Data Analyst",
        "ڈیٹا اینالسٹ",
        "Technology",
        "Data",
        "Organises and interprets data for decisions.",
        "Cleaning data, checking assumptions, analysing patterns, and communicating limitations.",
        ("numerical_reasoning", "attention_to_detail", "research_ability"),
        ("investigative_analytical", "organised_process_oriented"),
        ("learning", "deep_expertise"),
        ("desk_versus_physical", "structured_versus_open_ended"),
        (
            ("data-analysis", "Data analysis", "analytical"),
            ("data-communication", "Data communication", "communication"),
        ),
        ("Skills-first route", "Degree route"),
        "Reporting Analyst",
    ),
    CareerSeed(
        "ux-product-designer",
        "UX / Product Designer",
        "یو ایکس / پروڈکٹ ڈیزائنر",
        "Creative and Digital",
        "Product Design",
        "Explores user needs and designs usable product experiences.",
        "Researching problems, reframing needs, prototyping, testing, and collaborating.",
        ("problem_reframing", "product_thinking", "listening"),
        ("creative_expressive", "investigative_analytical"),
        ("creativity_value", "learning"),
        ("individual_versus_collaborative", "long_projects_versus_short_cycles"),
        (("prototyping", "Prototyping", "creative"), ("user-research", "User research", "domain")),
        ("Portfolio route", "Skills-first route"),
        "Product Designer",
    ),
    CareerSeed(
        "graphic-designer",
        "Graphic Designer",
        "گرافک ڈیزائنر",
        "Creative and Digital",
        "Visual Design",
        "Creates visual communication for defined audiences and contexts.",
        "Interpreting briefs, developing concepts, producing assets, and incorporating feedback.",
        ("visual_composition", "visual_creativity", "attention_to_detail"),
        ("creative_expressive",),
        ("creativity_value", "variety"),
        ("desk_versus_physical", "structured_versus_open_ended"),
        (
            ("visual-design", "Visual design", "creative"),
            ("design-tools", "Design tools", "tool_platform"),
        ),
        ("Portfolio route", "Diploma route"),
        "Visual Designer",
    ),
    CareerSeed(
        "teacher",
        "Teacher",
        "استاد",
        "Education and Social",
        "Teaching",
        "Supports learning in a subject and learner context.",
        "Planning lessons, explaining ideas, observing learning, and adapting support.",
        ("explanation", "empathy", "planning"),
        ("social_helping",),
        ("social_impact", "stability"),
        ("customer_facing_versus_behind_the_scenes", "individual_versus_collaborative"),
        (
            ("teaching", "Teaching practice", "domain"),
            ("explanation", "Explanation", "communication"),
        ),
        ("Degree route", "Certification route"),
        "Subject Teacher",
    ),
    CareerSeed(
        "sales-business-development",
        "Sales / Business Development",
        "سیلز / بزنس ڈیولپمنٹ",
        "Business",
        "Sales",
        "Develops commercial relationships and opportunities.",
        "Understanding needs, communicating offers, following up, and maintaining relationships.",
        ("persuasion", "listening", "adaptability"),
        ("enterprising_persuasive",),
        ("recognition", "income"),
        ("socially_active", "customer_facing_versus_behind_the_scenes"),
        (
            ("consultative-selling", "Consultative selling", "domain"),
            ("negotiation", "Negotiation", "communication"),
        ),
        ("Entry-level role route", "Skills-first route"),
        "Business Development Executive",
    ),
    CareerSeed(
        "accountant",
        "Accountant",
        "اکاؤنٹنٹ",
        "Business",
        "Accounting",
        "Maintains and interprets financial records within defined rules.",
        "Recording transactions, reconciling records, preparing reports, and checking compliance.",
        ("numerical_reasoning", "attention_to_detail", "conscientiousness"),
        ("organised_process_oriented", "investigative_analytical"),
        ("stability", "predictability"),
        ("structured_versus_open_ended", "desk_versus_physical"),
        (("accounting", "Accounting", "domain"), ("spreadsheet", "Spreadsheet use", "digital")),
        ("Degree route", "Certification route"),
        "Accounts Officer",
    ),
    CareerSeed(
        "research-assistant",
        "Research Assistant",
        "ریسرچ اسسٹنٹ",
        "Research",
        "Applied Research",
        "Supports structured investigation under a research protocol.",
        "Reviewing sources, collecting or organising evidence, analysing material, "
        "and documenting methods.",
        ("research_ability", "attention_to_detail", "written_expression"),
        ("investigative_analytical",),
        ("learning", "deep_expertise"),
        ("structured_versus_open_ended", "individual_versus_collaborative"),
        (
            ("research-methods", "Research methods", "domain"),
            ("evidence-writing", "Evidence writing", "communication"),
        ),
        ("Internship route", "Degree route"),
        "Junior Researcher",
    ),
    CareerSeed(
        "mechanical-technician",
        "Mechanical Technician",
        "مکینیکل ٹیکنیشن",
        "Skilled Trades",
        "Mechanical",
        "Installs, tests, maintains, or repairs mechanical equipment.",
        "Inspecting equipment, following safety procedures, diagnosing faults, "
        "and completing practical work.",
        ("practical_reasoning", "spatial_reasoning", "attention_to_detail"),
        ("practical_hands_on",),
        ("stability", "deep_expertise"),
        ("desk_versus_physical", "indoor_versus_field"),
        (
            ("mechanical-maintenance", "Mechanical maintenance", "technical"),
            ("workplace-safety", "Workplace safety", "domain"),
        ),
        ("Diploma route", "Apprenticeship route"),
        "Maintenance Technician",
    ),
    CareerSeed(
        "digital-marketer",
        "Digital Marketer",
        "ڈیجیٹل مارکیٹر",
        "Business",
        "Marketing",
        "Plans and evaluates digital communication and campaign activity.",
        "Researching audiences, creating campaigns, analysing results, and coordinating content.",
        ("written_expression", "persuasion", "digital_fluency"),
        ("enterprising_persuasive", "creative_expressive"),
        ("variety", "creativity_value"),
        ("desk_versus_physical", "stable_versus_changing"),
        (
            ("campaign-analysis", "Campaign analysis", "analytical"),
            ("digital-content", "Digital content", "creative"),
        ),
        ("Skills-first route", "Portfolio route"),
        "Marketing Executive",
    ),
    CareerSeed(
        "nurse",
        "Nurse",
        "نرس",
        "Healthcare",
        "Nursing",
        "Provides regulated clinical care within an approved scope of practice.",
        "Monitoring patients, delivering care, documenting observations, and coordinating "
        "with clinical teams.",
        ("empathy", "attention_to_detail", "stress_tolerance"),
        ("social_helping",),
        ("social_impact", "stability"),
        ("socially_active", "indoor_versus_field"),
        (
            ("clinical-care", "Clinical care", "domain"),
            ("clinical-communication", "Clinical communication", "communication"),
        ),
        ("Degree route", "Diploma route"),
        "Staff Nurse",
    ),
    CareerSeed(
        "lawyer",
        "Lawyer",
        "وکیل",
        "Law and Policy",
        "Legal Practice",
        "Provides regulated legal services within a jurisdiction and practice area.",
        "Researching law, analysing facts, drafting, advising, and representing clients "
        "where authorised.",
        ("verbal_reasoning", "written_expression", "research_ability"),
        ("investigative_analytical", "enterprising_persuasive"),
        ("recognition", "deep_expertise"),
        ("customer_facing_versus_behind_the_scenes", "structured_versus_open_ended"),
        (
            ("legal-research", "Legal research", "domain"),
            ("legal-writing", "Legal writing", "communication"),
        ),
        ("Degree route", "Internship route"),
        "Advocate",
    ),
)


def _normalise_environment(code: str) -> str:
    aliases = {
        "socially_active": "quiet_versus_socially_active",
        "indoor_versus_field": "indoor_versus_field",
    }
    return aliases.get(code, code)


@transaction.atomic
def create_synthetic_career_pack() -> dict[str, CareerProfileVersion]:
    existing = CareerTaxonomyVersion.objects.filter(
        taxonomy__code="grow-synthetic-careers", version=1
    ).first()
    if existing:
        return {
            item.profile.code: item for item in existing.career_versions.select_related("profile")
        }

    dimensions = create_dimension_catalog()
    source = ResearchSource.objects.create(
        source_type=ResearchSource.SourceType.OTHER,
        title="Grow synthetic career architecture reference",
        publisher="Grow synthetic fixture generator",
        reference="synthetic-career-pack-v1",
        publication_date=date(2026, 10, 5),
        accessed_date=date(2026, 10, 5),
        geography="Pakistan (synthetic architecture context only)",
        methodology_notes=(
            "Hand-authored fictionalised structure for deterministic engineering tests."
        ),
        limitations=LIMITATION,
        quality_status=Confidence.LOW,
        freshness=Freshness.UNKNOWN,
        licence_notes="Original synthetic repository fixture; contains no copied source text.",
    )
    for status in (ReviewStatus.IN_REVIEW, ReviewStatus.APPROVED, ReviewStatus.PUBLISHED):
        transition_review(
            target=source,
            to_status=status,
            reviewer_reference="synthetic-career-reviewer",
            reason="Publish explicitly synthetic reference source for architecture testing.",
        )
        source.refresh_from_db()

    taxonomy = CareerTaxonomy.objects.create(
        code="grow-synthetic-careers",
        title="Grow synthetic Pakistan career reference taxonomy",
        scope="Twelve varied career examples for architecture and test coverage only.",
    )
    version = CareerTaxonomyVersion.objects.create(
        taxonomy=taxonomy,
        version=1,
        provenance="Original synthetic fixture authored for Milestone 3",
        limitations=LIMITATION,
        data_markers=MARKERS,
    )
    clusters: dict[str, CareerCluster] = {}
    families: dict[tuple[str, str], CareerFamily] = {}
    results: dict[str, CareerProfileVersion] = {}
    skill_cache: dict[str, CareerSkill] = {}

    for seed in CAREERS:
        cluster_code = seed.cluster.lower().replace(" ", "-")
        cluster = clusters.get(cluster_code)
        if cluster is None:
            cluster = CareerCluster.objects.create(
                taxonomy_version=version, code=cluster_code, name_en=seed.cluster
            )
            clusters[cluster_code] = cluster
        family_code = seed.family.lower().replace(" ", "-")
        family_key = (cluster_code, family_code)
        family = families.get(family_key)
        if family is None:
            family = CareerFamily.objects.create(
                taxonomy_version=version,
                cluster=cluster,
                code=family_code,
                name_en=seed.family,
            )
            families[family_key] = family
        stable = CareerProfile.objects.create(code=seed.code)
        profile = CareerProfileVersion.objects.create(
            profile=stable,
            taxonomy_version=version,
            family=family,
            version=1,
            title_en=seed.title,
            title_ur=seed.title_ur,
            pakistan_title=seed.alias,
            summary=seed.summary,
            typical_work=seed.work,
            regulation_notes=(
                "Regulated profession: exact Pakistan requirements are UNKNOWN and require "
                "approved research."
                if seed.code in {"nurse", "lawyer"}
                else ""
            ),
            limitations=LIMITATION,
            data_classification=DataClassification.SYNTHETIC,
            participant_recommendation_ready=False,
        )
        CareerAlias.objects.create(
            profile_version=profile,
            name=seed.alias,
            alias_type=CareerAlias.AliasType.ENTRY,
        )
        dimension_codes = seed.dimensions + seed.interests + seed.values
        for code in dimension_codes:
            dimension = dimensions[code]
            is_core = code in seed.dimensions
            CareerDimensionRelationship.objects.create(
                profile_version=profile,
                dimension=dimension,
                importance=OrdinalRelevance.HIGH if is_core else OrdinalRelevance.VARIABLE,
                direction=CareerDimensionRelationship.Direction.CONTEXTUAL,
                minimum_relevance=OrdinalRelevance.UNKNOWN,
                typical_relevance=OrdinalRelevance.HIGH if is_core else OrdinalRelevance.VARIABLE,
                confidence=Confidence.LOW,
                source=source,
                limitations=LIMITATION,
                status=ReviewStatus.APPROVED,
            )
        for code in seed.environments:
            CareerEnvironmentObservation.objects.create(
                profile_version=profile,
                dimension=dimensions[_normalise_environment(code)],
                prevalence=CareerEnvironmentObservation.Prevalence.VARIABLE,
                context="Varies by organisation, industry, seniority, and employment model.",
                source=source,
                confidence=Confidence.LOW,
                limitations=LIMITATION,
                status=ReviewStatus.APPROVED,
            )
        profile_skills: list[CareerSkill] = []
        for skill_code, name, category in seed.skills:
            skill = skill_cache.get(skill_code)
            if skill is None:
                skill = CareerSkill.objects.create(code=skill_code, name=name, category=category)
                skill_cache[skill_code] = skill
            profile_skills.append(skill)
            CareerSkillRequirement.objects.create(
                profile_version=profile,
                skill=skill,
                requirement=CareerSkillRequirement.RequirementLevel.COMMON,
                source=source,
                limitations=LIMITATION,
                freshness=Freshness.UNKNOWN,
                status=ReviewStatus.APPROVED,
            )
        for route_title in seed.pathways:
            route = next(
                value
                for value, label in CareerPathway.RouteType.choices
                if route_title.lower().startswith(label.lower().split("-")[0])
            )
            pathway = CareerPathway.objects.create(
                profile_version=profile,
                route_type=route,
                title=route_title,
                education_requirement="UNKNOWN pending approved Pakistan pathway research.",
                duration="Unknown",
                prerequisites="UNKNOWN pending approved research.",
                typical_next_step="Research and human review required before participant use.",
                source=source,
                limitations=LIMITATION,
                source_date=date(2026, 10, 5),
                freshness=Freshness.UNKNOWN,
                status=ReviewStatus.APPROVED,
            )
            pathway.skills.add(*profile_skills)
        for observation_type in (
            MarketObservation.ObservationType.DEMAND,
            MarketObservation.ObservationType.REMOTE_AVAILABILITY,
            MarketObservation.ObservationType.SALARY_RANGE,
        ):
            MarketObservation.objects.create(
                profile_version=profile,
                observation_type=observation_type,
                value_state=MarketObservation.ValueState.UNKNOWN,
                source=source,
                source_date=date(2026, 10, 5),
                confidence=Confidence.UNKNOWN,
                limitations=LIMITATION,
                freshness=Freshness.UNKNOWN,
                review_status=ReviewStatus.APPROVED,
            )
        results[seed.code] = profile

    profiles = list(results.values())
    for left, right in zip(profiles, profiles[1:], strict=False):
        CareerRelationship.objects.create(
            taxonomy_version=version,
            source=left,
            target=right,
            relationship_type=CareerRelationship.RelationshipType.RELATED,
            notes="Synthetic relationship for versioning and inspection tests only.",
        )
    for profile in profiles:
        for status in (ReviewStatus.IN_REVIEW, ReviewStatus.APPROVED):
            transition_review(
                target=profile,
                to_status=status,
                reviewer_reference="synthetic-career-reviewer",
                reason="Synthetic pack content review for engineering use only.",
            )
            profile.refresh_from_db()
    for status in (ReviewStatus.IN_REVIEW, ReviewStatus.APPROVED):
        transition_review(
            target=version,
            to_status=status,
            reviewer_reference="synthetic-career-reviewer",
            reason="Synthetic taxonomy review for engineering use only.",
        )
        version.refresh_from_db()
    publish_taxonomy_version(
        version=version,
        lifecycle=Lifecycle.PILOT,
        reviewer_reference="synthetic-career-reviewer",
        reason="Publish explicitly synthetic pilot registry for deterministic testing.",
    )
    return results
