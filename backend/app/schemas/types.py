"""Shared Pydantic types.

`EmailAddress` deliberately relaxes deliverability checking so that reserved
RFC 2606 domains (`.test`, `.example`, `.invalid`) are accepted for seed data
and test fixtures, while genuinely malformed addresses are still rejected with
422. Pydantic's built-in `EmailStr` refuses those reserved TLDs outright.
"""

from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator


def _check_email(value: str) -> str:
    try:
        result = validate_email(
            value,
            check_deliverability=False,
            # RFC 2606 reserves .test/.example/.invalid; this project is a
            # demo/test environment, so those domains are treated as usable.
            test_environment=True,
        )
    except EmailNotValidError as exc:
        raise ValueError(f"value is not a valid email address: {exc}") from exc
    # Return the normalized string, not email-validator's ValidatedEmail object,
    # which Pydantic cannot serialize to JSON.
    return result.normalized


EmailAddress = Annotated[str, AfterValidator(_check_email)]

__all__ = ["EmailAddress"]
