from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User
from app.plan_generation.errors import PlanWorkflowError, PlanWorkflowFailureCode
from app.plan_generation.safety import assess_generated_plan_safety
from app.plan_generation.schemas import ClaudePlanRequest, GeneratedPlan
from app.plan_generation.service import generate_structured_plan
from app.profile.schemas import ProfileInput, ProfileResponse
from app.profile.service import get_profile
from app.wellness.service import assess_profile_safety, calculate_profile_wellness

_SYSTEM_INSTRUCTIONS = """Create a general-wellness plan that follows the response schema.
Match the calculated number of workout sessions and do not exceed the calculated session duration.
Do not provide diagnosis, treatment, rehabilitation, medication or supplement directives.
Do not prescribe calorie or macronutrient quantities because the profile does not support them.
Use only the supplied profile as personalization data and never invent research or citations."""

_APPLICATION_CONTEXT = """MyFitnessPlan provides general workout and food-pattern suggestions,
not medical care or individualized clinical nutrition advice. Give practical, conservative guidance
appropriate to the saved experience level, schedule, available equipment, dietary preferences, and
general-wellness constraints. Encourage users to stop if an activity causes pain and to seek an
appropriately qualified professional when they need medical or dietary treatment."""


def generate_plan_for_user(
    database_session: Session,
    user: User,
    settings: Settings,
) -> GeneratedPlan:
    """Orchestrate the authenticated profile-to-plan workflow without persistence."""
    stored_profile = get_profile(database_session, user)
    if stored_profile is None:
        raise PlanWorkflowError(
            PlanWorkflowFailureCode.MISSING_PROFILE,
            "Create a profile before generating a plan.",
        )

    stored_profile_response = ProfileResponse.model_validate(stored_profile)
    profile = ProfileInput.model_validate(stored_profile_response.model_dump())
    safety = assess_profile_safety(profile)
    if not safety.is_eligible:
        raise PlanWorkflowError(
            PlanWorkflowFailureCode.UNSAFE_PROFILE,
            "The saved profile is outside MyFitnessPlan's general-wellness scope.",
            issues=tuple(issue.code.value for issue in safety.issues),
        )

    calculated_values = calculate_profile_wellness(profile)
    plan = generate_structured_plan(
        ClaudePlanRequest(
            system_instructions=_SYSTEM_INSTRUCTIONS,
            application_context=_APPLICATION_CONTEXT,
            calculated_values=calculated_values,
            profile_data=profile,
        ),
        settings,
    )
    output_safety = assess_generated_plan_safety(plan, calculated_values)
    if not output_safety.is_eligible:
        raise PlanWorkflowError(
            PlanWorkflowFailureCode.UNSAFE_MODEL_OUTPUT,
            "Claude returned a plan that failed the general-wellness safety checks.",
            issues=tuple(issue.value for issue in output_safety.issues),
        )
    return plan
