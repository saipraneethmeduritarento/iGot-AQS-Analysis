"""
Prompt Manager for Assessment Quality Score System

Handles loading and formatting of YAML prompts for LLM interactions.
"""

import os
import re
from pathlib import Path
from string import Template
from typing import Any, Optional

import yaml


class PromptManager:
    """Manages loading and formatting of system prompts from YAML configuration."""

    def __init__(self, prompts_dir: Optional[str] = None, version: str = "v4"):
        """
        Initialize the prompt manager.

        Args:
            prompts_dir: Path to the prompts directory. Defaults to project prompts folder.
            version: Version of prompts to use (v1, v2, etc.). Defaults to v4.
        """
        self.version = version
        if prompts_dir is None:
            # Default to prompts directory relative to this file
            self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        self.prompts: dict[str, Any] = {}
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load all YAML prompt files from the prompts directory."""
        prompt_file = self.prompts_dir / "aqs_system_prompts.yaml"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        with open(prompt_file, "r", encoding="utf-8") as f:
            all_prompts = yaml.safe_load(f)
            # Load the specific version (v1, v2, etc.)
            self.prompts = all_prompts.get(self.version, {})
            if not self.prompts:
                raise ValueError(f"Prompt version '{self.version}' not found in {prompt_file}")

    def _safe_format(self, template: str, **kwargs) -> str:
        """
        Safely format a template string that may contain JSON with curly braces.
        
        Uses a custom approach: replaces only known placeholders, leaving JSON braces intact.
        """
        result = template
        for key, value in kwargs.items():
            # Replace {key} with the value, but not {{key}} or JSON-like patterns
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))
        return result

    def get_system_role(self) -> str:
        """Get the system role prompt."""
        return self.prompts.get("system_role", "")

    def get_difficulty_analysis_prompt(
        self,
        course_title: str,
        course_description: str,
        course_level: str,
        assessment_name: str,
        assessment_type: str,
        total_questions: int,
        expected_duration: int,
        questions_text: str
    ) -> str:
        """
        Get formatted difficulty analysis prompt.

        Args:
            course_title: Title of the course
            course_description: Course description
            course_level: Course difficulty level
            assessment_name: Name of the assessment
            assessment_type: Type of assessment
            total_questions: Number of questions
            expected_duration: Expected duration in minutes
            questions_text: Formatted questions text

        Returns:
            Formatted prompt string
        """
        template = self.prompts.get("difficulty_analysis", {}).get("prompt", "")
        return self._safe_format(
            template,
            course_title=course_title,
            course_description=course_description,
            course_level=course_level,
            assessment_name=assessment_name,
            assessment_type=assessment_type,
            total_questions=total_questions,
            expected_duration=expected_duration,
            questions_text=questions_text
        )

    def get_blooms_taxonomy_prompt(self, questions_with_options: str) -> str:
        """
        Get formatted Bloom's taxonomy evaluation prompt.

        Args:
            questions_with_options: Formatted questions with options

        Returns:
            Formatted prompt string
        """
        template = self.prompts.get("blooms_taxonomy", {}).get("prompt", "")
        return self._safe_format(template, questions_with_options=questions_with_options)

    def get_combined_analysis_prompt(
        self,
        course_title: str,
        course_description: str,
        course_level: str,
        learning_objectives: str,
        competencies: str,
        course_content_summary: str,
        assessment_name: str,
        assessment_type: str,
        total_questions: int,
        expected_duration: int,
        questions_text: str,
        is_standalone: bool = False
    ) -> str:
        """
        Get formatted combined analysis prompt (difficulty + blooms + course fit in one call).

        Args:
            course_title: Title of the course
            course_description: Course description
            course_level: Course difficulty level
            learning_objectives: Learning objectives
            competencies: Course competencies
            course_content_summary: Summary of course content
            assessment_name: Name of the assessment
            assessment_type: Type of assessment
            total_questions: Number of questions
            expected_duration: Expected duration in minutes
            questions_text: Formatted questions text
            is_standalone: Whether this is a standalone assessment

        Returns:
            Formatted prompt string
        """
        if is_standalone:
            template = self.prompts.get("combined_analysis_standalone", {}).get("prompt", "")
            return self._safe_format(
                template,
                assessment_name=assessment_name,
                assessment_type=assessment_type,
                total_questions=total_questions,
                expected_duration=expected_duration,
                questions_text=questions_text
            )
        else:
            template = self.prompts.get("combined_analysis", {}).get("prompt", "")
            return self._safe_format(
                template,
                course_title=course_title,
                course_description=course_description,
                course_level=course_level,
                learning_objectives=learning_objectives,
                competencies=competencies,
                course_content_summary=course_content_summary,
                assessment_name=assessment_name,
                assessment_type=assessment_type,
                total_questions=total_questions,
                expected_duration=expected_duration,
                questions_text=questions_text
            )

    def get_course_fit_prompt(
        self,
        course_title: str,
        course_description: str,
        learning_objectives: str,
        competencies: str,
        course_content_summary: str,
        questions_text: str
    ) -> str:
        """
        Get formatted course fit analysis prompt.

        Args:
            course_title: Title of the course
            course_description: Course description
            learning_objectives: Learning objectives
            competencies: Course competencies
            course_content_summary: Summary of course content
            questions_text: Formatted questions text

        Returns:
            Formatted prompt string
        """
        template = self.prompts.get("course_fit_analysis", {}).get("prompt", "")
        return self._safe_format(
            template,
            course_title=course_title,
            course_description=course_description,
            learning_objectives=learning_objectives,
            competencies=competencies,
            course_content_summary=course_content_summary,
            questions_text=questions_text
        )

    def get_final_aqs_prompt(
        self,
        difficulty_level: str,
        difficulty_rationale: str,
        complexity_score: float,
        language_score: float,
        cognitive_score: float,
        alignment_score: float,
        blooms_scores: dict,
        blooms_distribution: str,
        course_fit_score: float,
        course_fit_status: str
    ) -> str:
        """
        Get formatted final AQS computation prompt.

        Args:
            difficulty_level: Assessed difficulty level
            difficulty_rationale: Rationale for difficulty
            complexity_score: Complexity score
            language_score: Language difficulty score
            cognitive_score: Cognitive effort score
            alignment_score: Course alignment score
            blooms_scores: Bloom's taxonomy scores
            blooms_distribution: Bloom's distribution summary
            course_fit_score: Course fit score
            course_fit_status: Course fit status

        Returns:
            Formatted prompt string
        """
        template = self.prompts.get("final_aqs_computation", {}).get("prompt", "")
        return self._safe_format(
            template,
            difficulty_level=difficulty_level,
            difficulty_rationale=difficulty_rationale,
            complexity_score=complexity_score,
            language_score=language_score,
            cognitive_score=cognitive_score,
            alignment_score=alignment_score,
            blooms_scores=blooms_scores,
            blooms_distribution=blooms_distribution,
            course_fit_score=course_fit_score,
            course_fit_status=course_fit_status
        )

    def get_edge_case_warning(self, case_type: str, **kwargs) -> str:
        """
        Get warning message for edge cases.

        Args:
            case_type: Type of edge case (missing_content, few_questions, etc.)
            **kwargs: Additional parameters for the warning template

        Returns:
            Warning message string
        """
        edge_cases = self.prompts.get("edge_case_handlers", {})
        case_config = edge_cases.get(case_type, {})
        template = case_config.get("warning_template", "")

        if template and kwargs:
            return template.format(**kwargs)
        return template

    def get_aqs_quality_tier(self, score: float) -> tuple[str, str]:
        """
        Determine quality tier based on AQS score.

        Args:
            score: AQS score (0-100)

        Returns:
            Tuple of (tier_name, tier_description)
        """
        quality_tiers = self.prompts.get("quality_tiers", {})

        tiers_order = ["excellent", "good", "satisfactory", "needs_improvement", "poor"]

        for tier in tiers_order:
            tier_config = quality_tiers.get(tier, {})
            min_score = tier_config.get("min_score", 0)
            if score >= min_score:
                return tier.replace("_", " ").title(), tier_config.get("description", "")

        return "Poor", quality_tiers.get("poor", {}).get("description", "")

    def get_blooms_weights(self) -> dict[str, float]:
        """Get Bloom's taxonomy level weights."""
        weights = self.prompts.get("blooms_weights", {})
        return {
            "remember": weights.get("remember", 1.0),
            "understand": weights.get("understand", 1.5),
            "apply": weights.get("apply", 2.0),
            "analyze": weights.get("analyze", 2.5),
            "evaluate": weights.get("evaluate", 3.0),
            "create": weights.get("create", 3.5)
        }

    def get_output_schema(self) -> str:
        """Get the expected output JSON schema."""
        return self.prompts.get("output_schema", {}).get("format", "{}")

    def get_few_questions_threshold(self) -> int:
        """Get the threshold for low question count warning."""
        return self.prompts.get("edge_case_handlers", {}).get(
            "few_questions", {}
        ).get("threshold", 5)

    def get_difficulty_mismatch_threshold(self) -> int:
        """Get the threshold for difficulty mismatch alert."""
        return self.prompts.get("edge_case_handlers", {}).get(
            "difficulty_mismatch", {}
        ).get("threshold", 30)
