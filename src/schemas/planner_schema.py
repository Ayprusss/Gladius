"""Pydantic schema for Planner Agent output"""
from pydantic import BaseModel, Field
from typing import List


class FileToChange(BaseModel):
    """File that needs to be changed"""
    path: str = Field(..., description="Relative path to the file")
    reason: str = Field(..., description="Why this file needs to change")


class PlannerOutput(BaseModel):
    """Output schema for the Planner Agent"""

    summary: str = Field(
        ...,
        description="2-3 sentence summary of what this ticket requires"
    )

    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made during planning"
    )

    plan: List[str] = Field(
        ...,
        description="Step-by-step implementation plan"
    )

    files_to_change: List[FileToChange] = Field(
        default_factory=list,
        description="Files that will need to be modified"
    )

    test_plan: List[str] = Field(
        default_factory=list,
        description="Test scenarios to validate the implementation"
    )

    risks: List[str] = Field(
        default_factory=list,
        description="Potential risks and concerns"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "summary": "Implement JWT-based authentication for the API",
                "assumptions": [
                    "Using existing user database",
                    "JWT tokens expire after 24 hours"
                ],
                "plan": [
                    "Create authentication middleware",
                    "Add JWT token generation endpoint",
                    "Protect existing API routes"
                ],
                "files_to_change": [
                    {
                        "path": "src/middleware/auth.py",
                        "reason": "Add JWT validation middleware"
                    }
                ],
                "test_plan": [
                    "Test login with valid credentials",
                    "Test protected endpoints without token"
                ],
                "risks": [
                    "Token storage security",
                    "Backward compatibility with existing clients"
                ]
            }
        }
