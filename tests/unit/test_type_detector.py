"""Unit tests for RequestTypeDetector"""
import pytest
from src.request_processor.type_detector import RequestTypeDetector


class TestRequestTypeDetector:
    """Test RequestTypeDetector functionality"""

    def test_detect_bug_keywords(self):
        """Test detection of bug type from keywords"""
        assert RequestTypeDetector.detect_type("Fix the login bug") == "bug"
        assert RequestTypeDetector.detect_type("Memory leak in service") == "bug"
        assert RequestTypeDetector.detect_type("Error in authentication") == "bug"
        assert RequestTypeDetector.detect_type("Crash on startup") == "bug"

    def test_detect_feature_keywords(self):
        """Test detection of feature type from keywords"""
        assert RequestTypeDetector.detect_type("Add login button") == "feature"
        assert RequestTypeDetector.detect_type("Create new dashboard") == "feature"
        assert RequestTypeDetector.detect_type("Implement OAuth") == "feature"
        assert RequestTypeDetector.detect_type("Build API endpoint") == "feature"

    def test_detect_improvement_keywords(self):
        """Test detection of improvement type from keywords"""
        assert RequestTypeDetector.detect_type("Refactor auth code") == "improvement"
        assert RequestTypeDetector.detect_type("Optimize database queries") == "improvement"
        assert RequestTypeDetector.detect_type("Improve performance") == "improvement"
        assert RequestTypeDetector.detect_type("Enhance user experience") == "improvement"

    def test_detect_mixed_keywords(self):
        """Test detection with mixed keywords (highest score wins)"""
        # Bug has more keywords
        result = RequestTypeDetector.detect_type("Fix bug and error in system")
        assert result == "bug"

        # Feature has more keywords
        result = RequestTypeDetector.detect_type("Add new feature and create dashboard")
        assert result == "feature"

    def test_detect_no_keywords_defaults_feature(self):
        """Test that requests with no keywords default to feature"""
        result = RequestTypeDetector.detect_type("Something generic without keywords")
        assert result == "feature"

        result = RequestTypeDetector.detect_type("Do the thing")
        assert result == "feature"

    def test_detect_case_insensitive(self):
        """Test that detection is case insensitive"""
        assert RequestTypeDetector.detect_type("FIX THE BUG") == "bug"
        assert RequestTypeDetector.detect_type("Add Feature") == "feature"
        assert RequestTypeDetector.detect_type("REFACTOR CODE") == "improvement"

    def test_detect_multiple_same_type_wins(self):
        """Test that type with most keyword matches wins"""
        # Multiple bug keywords
        result = RequestTypeDetector.detect_type(
            "Fix broken error that's causing issues and problems"
        )
        assert result == "bug"

    def test_detect_from_context(self):
        """Test detection from contextual phrases"""
        assert RequestTypeDetector.detect_type("The login is not working") == "bug"
        assert RequestTypeDetector.detect_type("Need to add support for dark mode") == "feature"
        assert RequestTypeDetector.detect_type("Let's improve and modernize the UI") == "improvement"

    def test_get_confidence_scores(self):
        """Test getting confidence scores for all types"""
        scores = RequestTypeDetector.get_confidence("Fix bug and add feature")

        assert "bug" in scores
        assert "feature" in scores
        assert "improvement" in scores
        assert "detected" in scores

        # Should have 1 bug keyword and 1 feature keyword
        assert scores["bug"] >= 1
        assert scores["feature"] >= 1

    def test_detect_empty_string_defaults_feature(self):
        """Test that empty string defaults to feature"""
        result = RequestTypeDetector.detect_type("")
        assert result == "feature"

    def test_detect_improvement_with_update(self):
        """Test improvement detection with 'update' keyword"""
        result = RequestTypeDetector.detect_type("Update the authentication system")
        assert result == "improvement"

    def test_detect_bug_with_failing(self):
        """Test bug detection with 'failing' keyword"""
        result = RequestTypeDetector.detect_type("Tests are failing")
        assert result == "bug"

    def test_detect_feature_with_introduce(self):
        """Test feature detection with 'introduce' keyword"""
        result = RequestTypeDetector.detect_type("Introduce new API")
        assert result == "feature"

    def test_detect_with_partial_word_match(self):
        """Test that partial word matches are counted"""
        # "fixing" contains "fix"
        result = RequestTypeDetector.detect_type("Fixing the issue")
        assert result == "bug"

        # "adding" contains "add"
        result = RequestTypeDetector.detect_type("Adding new feature")
        assert result == "feature"

    def test_get_confidence_with_clear_winner(self):
        """Test confidence scores when one type clearly dominates"""
        scores = RequestTypeDetector.get_confidence("Fix bug error issue problem")

        assert scores["bug"] >= 4  # Multiple bug keywords
        assert scores["feature"] == 0
        assert scores["improvement"] == 0
        assert scores["detected"] == "bug"

    def test_detect_multiline_request(self):
        """Test detection works with multiline requests"""
        request = """Fix the login bug.
        It's causing crashes.
        Error happens on startup."""

        result = RequestTypeDetector.detect_type(request)
        assert result == "bug"
