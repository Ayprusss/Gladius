"""Pydantic schema for Implementer Agent output"""
from pydantic import BaseModel, Field
from typing import List


class FileChange(BaseModel):
    """Description of a file change"""
    file: str = Field(..., description="Path to the file")
    type: str = Field(..., description="Type of change: modify, create, delete")
    description: str = Field(..., description="What changed and why")


class ImplementerOutput(BaseModel):
    """Output schema for the Implementer Agent"""

    changes: List[FileChange] = Field(
        ...,
        description="List of file changes made"
    )

    patch: str = Field(
        ...,
        description="Unified diff format of all changes"
    )

    notes: str = Field(
        ...,
        description="Implementation notes, caveats, and assumptions"
    )

    tests_added_or_updated: List[str] = Field(
        default_factory=list,
        description="Test files that were added or updated"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "changes": [
                    {
                        "file": "src/middleware/auth.py",
                        "type": "create",
                        "description": "Created JWT authentication middleware"
                    },
                    {
                        "file": "src/routes/api.py",
                        "type": "modify",
                        "description": "Added auth middleware to protected routes"
                    }
                ],
                "patch": "--- a/src/routes/api.py\n+++ b/src/routes/api.py\n@@ -1,5 +1,6 @@\n from flask import Flask\n+from middleware.auth import require_auth\n...",
                "notes": "Implemented JWT authentication using PyJWT library. Tokens expire after 24 hours. Secret key should be set via environment variable.",
                "tests_added_or_updated": [
                    "tests/test_auth_middleware.py",
                    "tests/test_protected_routes.py"
                ]
            }
        }
