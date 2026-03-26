"""Detect ticket type from request text using keyword analysis"""


class RequestTypeDetector:
    """Detect ticket type from request text using keyword analysis"""

    # Keyword mappings for bug detection
    BUG_KEYWORDS = [
        "fix", "bug", "error", "crash", "leak", "broken",
        "issue", "problem", "failing", "not working", "failed",
        "incorrect", "wrong", "breaking"
    ]

    # Keyword mappings for feature detection
    FEATURE_KEYWORDS = [
        "add", "create", "implement", "new", "build",
        "develop", "introduce", "enable", "support"
    ]

    # Keyword mappings for improvement detection
    IMPROVEMENT_KEYWORDS = [
        "refactor", "optimize", "improve", "enhance",
        "update", "upgrade", "modernize", "clean",
        "reorganize", "simplify", "performance"
    ]

    @staticmethod
    def detect_type(request: str) -> str:
        """
        Detect ticket type from request keywords

        Uses keyword matching to classify requests into:
        - bug: Issues, fixes, problems
        - feature: New functionality
        - improvement: Enhancements to existing code

        Args:
            request: Natural language request

        Returns:
            "bug", "feature", or "improvement"

        Examples:
            >>> RequestTypeDetector.detect_type("Fix the login bug")
            'bug'

            >>> RequestTypeDetector.detect_type("Add email validation")
            'feature'

            >>> RequestTypeDetector.detect_type("Refactor authentication code")
            'improvement'

            >>> RequestTypeDetector.detect_type("Something generic")
            'feature'
        """
        request_lower = request.lower()

        # Count keyword matches for each type
        bug_score = sum(
            1 for kw in RequestTypeDetector.BUG_KEYWORDS
            if kw in request_lower
        )

        feature_score = sum(
            1 for kw in RequestTypeDetector.FEATURE_KEYWORDS
            if kw in request_lower
        )

        improvement_score = sum(
            1 for kw in RequestTypeDetector.IMPROVEMENT_KEYWORDS
            if kw in request_lower
        )

        # Build scores dictionary
        scores = {
            "bug": bug_score,
            "feature": feature_score,
            "improvement": improvement_score
        }

        # Find type with highest score
        max_type = max(scores, key=scores.get)

        # Default to "feature" if no clear match (all scores are 0)
        if scores[max_type] == 0:
            return "feature"

        return max_type

    @staticmethod
    def get_confidence(request: str) -> dict:
        """
        Get confidence scores for all types

        Args:
            request: Natural language request

        Returns:
            Dictionary with scores for each type

        Example:
            >>> RequestTypeDetector.get_confidence("Fix bug and add tests")
            {'bug': 1, 'feature': 1, 'improvement': 0, 'detected': 'bug'}
        """
        request_lower = request.lower()

        bug_score = sum(
            1 for kw in RequestTypeDetector.BUG_KEYWORDS
            if kw in request_lower
        )

        feature_score = sum(
            1 for kw in RequestTypeDetector.FEATURE_KEYWORDS
            if kw in request_lower
        )

        improvement_score = sum(
            1 for kw in RequestTypeDetector.IMPROVEMENT_KEYWORDS
            if kw in request_lower
        )

        detected_type = RequestTypeDetector.detect_type(request)

        return {
            "bug": bug_score,
            "feature": feature_score,
            "improvement": improvement_score,
            "detected": detected_type
        }
