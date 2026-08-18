class PlanNotFoundError(RuntimeError):
    """The requested plan does not exist for the authenticated user."""


class ArchivedPlanActivationError(RuntimeError):
    """Archived plans cannot re-enter the active lifecycle."""
