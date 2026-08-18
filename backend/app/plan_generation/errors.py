from enum import StrEnum


class PlanGenerationFailureCode(StrEnum):
    MISSING_CONFIGURATION = "missing_configuration"
    TIMEOUT = "timeout"
    NETWORK_FAILURE = "network_failure"
    PROVIDER_REJECTION = "provider_rejection"
    EMPTY_OUTPUT = "empty_output"
    INVALID_JSON = "invalid_json"
    SCHEMA_VIOLATION = "schema_violation"
    OUTPUT_TRUNCATED = "output_truncated"
    UNEXPECTED_RESPONSE = "unexpected_response"


class PlanGenerationError(RuntimeError):
    """A safe, machine-readable generation failure for later API mapping."""

    def __init__(self, code: PlanGenerationFailureCode, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


class PlanWorkflowFailureCode(StrEnum):
    MISSING_PROFILE = "missing_profile"
    UNSAFE_PROFILE = "unsafe_profile"
    UNSAFE_MODEL_OUTPUT = "unsafe_model_output"


class PlanWorkflowError(RuntimeError):
    """A generation-workflow rejection that is safe to expose at the API boundary."""

    def __init__(
        self,
        code: PlanWorkflowFailureCode,
        public_message: str,
        *,
        issues: tuple[str, ...] = (),
    ) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.issues = issues
