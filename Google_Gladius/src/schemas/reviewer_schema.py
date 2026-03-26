"""Pydantic schema for Reviewer Agent output"""
from pydantic import BaseModel, Field
from typing import List, Literal


class Issue(BaseModel):
    """An issue found during review"""
    severity: Literal["critical", "major", "minor"] = Field(
        ...,
        description="Severity level of the issue"
    )
    file: str = Field(..., description="File where the issue was found")
    line: int = Field(None, description="Line number (if applicable)")
    description: str = Field(..., description="What's wrong")
    suggestion: str = Field(..., description="How to fix it")


class ReviewerOutput(BaseModel):
    """Output schema for the Reviewer Agent"""

    review_summary: str = Field(
        ...,
        description="Overall assessment of the implementation"
    )

    issues: List[Issue] = Field(
        default_factory=list,
        description="Issues found during review"
    )

    suggested_changes: List[str] = Field(
        default_factory=list,
        description="Specific, actionable changes to improve the implementation"
    )

    verdict: Literal["APPROVE", "REQUEST_CHANGES"] = Field(
        ...,
        description="Final verdict: APPROVE or REQUEST_CHANGES"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "review_summary": "Implementation looks solid overall. JWT authentication is properly implemented with good error handling. However, there are a few security concerns that need to be addressed.",
                "issues": [
                    {
                        "severity": "critical",
                        "file": "src/middleware/auth.py",
                        "line": 45,
                        "description": "JWT secret key is hardcoded",
                        "suggestion": "Move secret key to environment variable"
                    },
                    {
                        "severity": "minor",
                        "file": "src/routes/api.py",
                        "line": 12,
                        "description": "Missing error handling for expired tokens",
                        "suggestion": "Add try-catch for JWT decode errors"
                    }
                ],
                "suggested_changes": [
                    "Add environment variable validation for JWT_SECRET",
                    "Implement token refresh mechanism",
                    "Add rate limiting to login endpoint"
                ],
                "verdict": "REQUEST_CHANGES"
            }
        }
