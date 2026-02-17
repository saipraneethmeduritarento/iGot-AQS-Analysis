"""
AQS Evaluator Module

Core evaluation engine for computing Assessment Quality Scores
using Google Vertex AI Gemini for analysis.
"""

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

from .data_loader import Assessment, CourseData, AssessmentDataLoader
from .prompt_manager import PromptManager
from .config import settings


# Model pricing per 1M tokens (USD)
MODEL_PRICING = {
    "gemini-2.0-flash": {
        "input": 0.10,   # $0.10 per 1M input tokens
        "output": 0.40,  # $0.40 per 1M output tokens
    },
    "gemini-2.5-flash": {
        "input": 0.30,   # $0.30 per 1M input tokens
        "output": 2.50,  # $2.50 per 1M output tokens
    },
    "gemini-3-pro-preview": {
        "input": 2.00,   # $2.00 per 1M input tokens (text/image/video)
        "output": 12.00,  # $12.00 per 1M output tokens (incl. thinking tokens)
    },
    "gemini-3-flash-preview": {
        "input": 0.50,   # $0.50 per 1M input tokens
        "output": 3.00,  # $3.00 per 1M output tokens
    },
}

# Default pricing for unknown models
DEFAULT_PRICING = {
    "input": 0.10,
    "output": 0.40,
}


@dataclass
class TokenMetrics:
    """Token usage metrics for a single LLM call."""
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    
    def add(self, other: "TokenMetrics") -> "TokenMetrics":
        """Add metrics from another TokenMetrics object."""
        return TokenMetrics(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            thinking_tokens=self.thinking_tokens + other.thinking_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            input_cost=self.input_cost + other.input_cost,
            output_cost=self.output_cost + other.output_cost,
            total_cost=self.total_cost + other.total_cost
        )
    
    def calculate_cost(self, model_name: str) -> None:
        """Calculate cost based on token usage and model pricing."""
        pricing = MODEL_PRICING.get(model_name, DEFAULT_PRICING)
        # Note: Currently ignoring cached token pricing unless explicitly added to MODEL_PRICING
        # Cached input generally has a lower cost, but for now we'll stick to standard input pricing
        # or just 0 if not specified, to avoid over-complicating. 
        # Typically cached input is ~25% of standard input cost.
        
        self.input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        self.output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        self.total_cost = self.input_cost + self.output_cost


@dataclass
class TokenEvaluationMetrics:
    """Comprehensive metrics for an evaluation run."""
    assessment_name: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    model_name: str = ""
    
    # Overall token metrics (combined from all LLM calls)
    overall_tokens: TokenMetrics = field(default_factory=TokenMetrics)
    
    # Totals (for backward compatibility)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_thinking_tokens: int = 0
    total_cached_tokens: int = 0
    total_tokens: int = 0
    
    # Cost totals
    total_input_cost: float = 0.0
    total_output_cost: float = 0.0
    total_cost: float = 0.0
    
    # LLM call counts
    llm_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    
    def add_tokens(self, tokens: TokenMetrics) -> None:
        """Add token metrics from an LLM call to the overall total."""
        self.overall_tokens = self.overall_tokens.add(tokens)
    
    def calculate_total_cost(self) -> None:
        """Calculate total costs from overall token metrics."""
        self.total_input_tokens = self.overall_tokens.input_tokens
        self.total_output_tokens = self.overall_tokens.output_tokens
        self.total_thinking_tokens = self.overall_tokens.thinking_tokens
        self.total_cached_tokens = self.overall_tokens.cached_tokens
        self.total_tokens = self.overall_tokens.total_tokens
        self.total_input_cost = self.overall_tokens.input_cost
        self.total_output_cost = self.overall_tokens.output_cost
        self.total_cost = self.overall_tokens.total_cost
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "assessment_name": self.assessment_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": round(self.duration_seconds, 2),
            "model_name": self.model_name,
            "token_usage": {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "thinking_tokens": self.total_thinking_tokens,
                "cached_tokens": self.total_cached_tokens,
                "total_tokens": self.total_tokens
            },
            "cost": {
                "input_cost_usd": round(self.total_input_cost, 6),
                "output_cost_usd": round(self.total_output_cost, 6),
                "total_cost_usd": round(self.total_cost, 6),
                "pricing_model": self.model_name
            },
            "llm_calls": {
                "total": self.llm_calls,
                "successful": self.successful_calls,
                "failed": self.failed_calls
            }
        }


@dataclass
class DifficultyScores:
    """Difficulty analysis sub-scores."""
    complexity_score: float = 0.0
    complexity_rationale: str = ""
    language_difficulty_score: float = 0.0
    language_difficulty_rationale: str = ""
    cognitive_effort_score: float = 0.0
    cognitive_effort_rationale: str = ""
    course_alignment_score: float = 0.0
    course_alignment_rationale: str = ""


@dataclass
class CourseFitDetails:
    """Detailed course fit analysis."""
    content_coverage_score: float = 0.0
    content_coverage_rationale: str = ""
    objective_alignment_score: float = 0.0
    objective_alignment_rationale: str = ""
    difficulty_appropriateness_score: float = 0.0
    difficulty_appropriateness_rationale: str = ""
    completeness_score: float = 0.0
    completeness_rationale: str = ""
    alignment_details: str = ""
    improvement_suggestions: list[str] = field(default_factory=list)


@dataclass
class QuestionClassification:
    """Per-question Bloom's taxonomy classification."""
    question_number: int = 0
    blooms_level: str = ""
    justification: str = ""


@dataclass
class BloomsScores:
    """Bloom's taxonomy scores."""
    remember: float = 0.0
    understand: float = 0.0
    apply: float = 0.0
    analyze: float = 0.0
    evaluate: float = 0.0
    create: float = 0.0


@dataclass
class BloomsRationales:
    """Bloom's taxonomy rationales."""
    remember: str = ""
    understand: str = ""
    apply: str = ""
    analyze: str = ""
    evaluate: str = ""
    create: str = ""


@dataclass
class AQSResult:
    """Complete AQS evaluation result."""
    assessment_name: str = ""
    assessment_type: str = ""
    
    # Difficulty Analysis
    difficulty_level: str = ""
    difficulty_rationale: str = ""
    difficulty_scores: DifficultyScores = field(default_factory=DifficultyScores)
    
    # Bloom's Taxonomy Analysis
    blooms_scores: BloomsScores = field(default_factory=BloomsScores)
    blooms_rationales: BloomsRationales = field(default_factory=BloomsRationales)
    blooms_distribution_summary: str = ""
    question_classifications: list[QuestionClassification] = field(default_factory=list)
    
    # Course Fit Analysis
    course_fit_score: float = 0.0
    course_fit_status: str = ""
    course_fit_details: CourseFitDetails = field(default_factory=CourseFitDetails)
    
    # Final Score
    aqs_score: float = 0.0
    AQS_quality_tier: str = ""  # Excellent/Good/Satisfactory/Needs Improvement/Poor
    quality_tier_reasoning: str = ""  # Explanation of why this tier was chosen
    
    # Flags and Warnings
    confidence_flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: TokenEvaluationMetrics = field(default_factory=TokenEvaluationMetrics)

    def to_dict(self) -> dict:
        """Convert to dictionary with proper structure."""
        return {
            "assessment_name": self.assessment_name,
            "assessment_type": self.assessment_type,
            
            # Difficulty Analysis
            "difficulty_level": self.difficulty_level,
            "difficulty_rationale": self.difficulty_rationale,
            "difficulty_scores": asdict(self.difficulty_scores),
            
            # Bloom's Taxonomy Analysis
            "blooms_scores": asdict(self.blooms_scores),
            "blooms_rationales": asdict(self.blooms_rationales),
            "blooms_distribution_summary": self.blooms_distribution_summary,
            "question_classifications": [asdict(qc) for qc in self.question_classifications],
            
            # Course Fit Analysis
            "course_fit_score": self.course_fit_score,
            "course_fit_status": self.course_fit_status,
            "course_fit_details": asdict(self.course_fit_details),
            
            # Final Score
            "aqs_score": self.aqs_score,
            "AQS_quality_tier": self.AQS_quality_tier,
            "quality_tier_reasoning": self.quality_tier_reasoning,
            
            # Flags and Warnings
            "confidence_flags": self.confidence_flags,
            "warnings": self.warnings,
            "metrics": self.metrics.to_dict()
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class AQSEvaluator:
    """
    Assessment Quality Score Evaluator.

    Uses LLM to analyze assessments and generate quality scores based on:
    - Difficulty level analysis
    - Bloom's taxonomy classification
    - Course content alignment
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompts_dir: Optional[str] = None,
        project_id: Optional[str] = None,
        location: Optional[str] = None
    ):
        """
        Initialize the AQS Evaluator.

        Args:
            model_name: Gemini model to use (overrides GEMINI_MODEL_NAME from settings)
            prompts_dir: Path to prompts directory
            project_id: Google Cloud project ID (overrides GOOGLE_PROJECT_ID from settings)
            location: Google Cloud location (overrides GOOGLE_PROJECT_LOCATION from settings)
        """
        # Get configuration from parameters or settings
        self.project_id = project_id or settings.google_project_id
        self.location = location or settings.google_project_location
        self.model_name = model_name or settings.gemini_model_name
        
        # Configure Vertex AI
        from google import genai
        from google.genai import types
        
        self.client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location
        )
        self.prompt_manager = PromptManager(prompts_dir)

    def evaluate_assessment(
        self,
        course_data: CourseData,
        assessment: Assessment,
        is_standalone: bool = False
    ) -> AQSResult:
        """
        Evaluate a single assessment and generate AQS.

        Args:
            course_data: Complete course data
            assessment: Assessment to evaluate
            is_standalone: Whether this is a standalone assessment

        Returns:
            AQSResult with complete evaluation
        """
        # Start timing
        start_time = time.time()
        start_datetime = datetime.now().isoformat()
        
        # Initialize metrics
        metrics = TokenEvaluationMetrics(
            assessment_name=assessment.name,
            start_time=start_datetime,
            model_name=self.model_name
        )
        
        result = AQSResult(
            assessment_name=assessment.name,
            assessment_type=assessment.assessment_type
        )

        # Collect warnings from data loading
        result.warnings.extend(course_data.warnings)

        # Check for edge cases
        self._check_edge_cases(assessment, result, is_standalone)

        # Format data for prompts
        data_loader = AssessmentDataLoader("")
        questions_text = data_loader.format_questions_for_prompt(assessment)
        content_summary = data_loader.format_course_content_summary(course_data.content)
        
        # Determine content scope for module vs final assessments
        if assessment.is_final_assessment:
            effective_content_summary = content_summary
        elif assessment.module_content and (assessment.module_content.transcript or assessment.module_content.pdf_text):
            module_content = assessment.module_content
            parts = [f"Module: {module_content.module_name}"]
            if module_content.transcript:
                parts.append(f"\nModule Transcript:\n{module_content.transcript}")
            if module_content.pdf_text:
                parts.append(f"\nModule PDF Content:\n{module_content.pdf_text}")
            effective_content_summary = "\n".join(parts)
            if len(effective_content_summary) > 10000:
                effective_content_summary = effective_content_summary[:10000] + "... [truncated]"
        else:
            effective_content_summary = content_summary

        # Single combined LLM call for all analyses
        combined_result, tokens, success = self._analyze_combined(
            course_data, assessment, questions_text, effective_content_summary, is_standalone
        )
        tokens.calculate_cost(self.model_name)
        metrics.add_tokens(tokens)
        metrics.llm_calls += 1
        if success:
            metrics.successful_calls += 1
        else:
            metrics.failed_calls += 1
            if "error" in combined_result:
                result.warnings.append(f"LLM Analysis Failed: {combined_result['error']}")

        # Extract difficulty analysis results
        difficulty_result = combined_result.get("difficulty_analysis", {})
        result.difficulty_level = difficulty_result.get("difficulty_level", "Intermediate")
        result.difficulty_rationale = difficulty_result.get("difficulty_rationale", "")
        result.difficulty_scores = DifficultyScores(
            complexity_score=difficulty_result.get("complexity_score", 0),
            complexity_rationale=difficulty_result.get("complexity_rationale", ""),
            language_difficulty_score=difficulty_result.get("language_difficulty_score", 0),
            language_difficulty_rationale=difficulty_result.get("language_difficulty_rationale", ""),
            cognitive_effort_score=difficulty_result.get("cognitive_effort_score", 0),
            cognitive_effort_rationale=difficulty_result.get("cognitive_effort_rationale", ""),
            course_alignment_score=difficulty_result.get("course_alignment_score", 0),
            course_alignment_rationale=difficulty_result.get("course_alignment_rationale", "")
        )

        # Extract Bloom's taxonomy results
        blooms_result = combined_result.get("blooms_taxonomy", {})
        blooms_scores = blooms_result.get("blooms_scores", {})
        result.blooms_scores = BloomsScores(
            remember=blooms_scores.get("remember", 0),
            understand=blooms_scores.get("understand", 0),
            apply=blooms_scores.get("apply", 0),
            analyze=blooms_scores.get("analyze", 0),
            evaluate=blooms_scores.get("evaluate", 0),
            create=blooms_scores.get("create", 0)
        )
        blooms_rationales = blooms_result.get("blooms_rationales", {})
        result.blooms_rationales = BloomsRationales(
            remember=blooms_rationales.get("remember", ""),
            understand=blooms_rationales.get("understand", ""),
            apply=blooms_rationales.get("apply", ""),
            analyze=blooms_rationales.get("analyze", ""),
            evaluate=blooms_rationales.get("evaluate", ""),
            create=blooms_rationales.get("create", "")
        )
        result.blooms_distribution_summary = blooms_result.get(
            "blooms_distribution_summary", ""
        )
        
        # Capture per-question Bloom's classifications
        question_classifications = blooms_result.get("question_classifications", [])
        for qc in question_classifications:
            result.question_classifications.append(QuestionClassification(
                question_number=qc.get("question_number", 0),
                blooms_level=qc.get("blooms_level", ""),
                justification=qc.get("justification", "")
            ))

        # Extract course fit results
        if is_standalone:
            result.course_fit_score = 0
            result.course_fit_status = "Not Applicable"
            result.confidence_flags.append("Standalone assessment - course fit not evaluated")
            fit_result = {}
        else:
            fit_result = combined_result.get("course_fit", {}) or {}
            result.course_fit_score = fit_result.get("course_fit_score", 0)
            result.course_fit_status = fit_result.get("course_fit_status", "")
            result.course_fit_details = CourseFitDetails(
                content_coverage_score=fit_result.get("content_coverage_score", 0),
                content_coverage_rationale=fit_result.get("content_coverage_rationale", ""),
                objective_alignment_score=fit_result.get("objective_alignment_score", 0),
                objective_alignment_rationale=fit_result.get("objective_alignment_rationale", ""),
                difficulty_appropriateness_score=fit_result.get("difficulty_appropriateness_score", 0),
                difficulty_appropriateness_rationale=fit_result.get("difficulty_appropriateness_rationale", ""),
                completeness_score=fit_result.get("completeness_score", 0),
                completeness_rationale=fit_result.get("completeness_rationale", ""),
                alignment_details=fit_result.get("alignment_details", ""),
                improvement_suggestions=fit_result.get("improvement_suggestions", [])
            )

            # Check for difficulty mismatch
            self._check_difficulty_mismatch(
                difficulty_result, fit_result, result
            )

        # Compute Final AQS
        result.aqs_score = self._compute_final_aqs(
            difficulty_result, blooms_result, result.course_fit_score, is_standalone
        )
        
        # Determine quality tier based on AQS score
        result.AQS_quality_tier = self._get_aqs_quality_tier(result.aqs_score)
        
        # Extract quality tier reasoning from LLM result
        result.quality_tier_reasoning = combined_result.get("quality_tier_reasoning", "")
        if not result.quality_tier_reasoning:
             # Fallback if LLM didn't provide reasoning
             result.quality_tier_reasoning = f"Assessment score of {result.aqs_score} falls within the {result.AQS_quality_tier} range."

        # Finalize metrics
        end_time = time.time()
        metrics.end_time = datetime.now().isoformat()
        metrics.duration_seconds = end_time - start_time
        
        # Calculate total costs (this also updates total_input_tokens, total_output_tokens, total_tokens)
        metrics.calculate_total_cost()
        
        result.metrics = metrics
        return result

    def _analyze_combined(
        self,
        course_data: CourseData,
        assessment: Assessment,
        questions_text: str,
        content_summary: str,
        is_standalone: bool
    ) -> tuple[dict, TokenMetrics, bool]:
        """
        Perform combined analysis (difficulty + blooms + course fit) in a single LLM call.
        
        Args:
            course_data: Course data
            assessment: Assessment to evaluate
            questions_text: Formatted questions text
            content_summary: Course/module content summary
            is_standalone: Whether this is a standalone assessment
            
        Returns:
            Tuple of (parsed JSON response, token metrics, success flag)
        """
        competencies = ", ".join(course_data.metadata.competencies)
        
        prompt = self.prompt_manager.get_combined_analysis_prompt(
            course_title=course_data.metadata.name,
            course_description=course_data.metadata.description,
            course_level=course_data.metadata.primary_category,
            learning_objectives=course_data.metadata.description,
            competencies=competencies,
            course_content_summary=content_summary,
            assessment_name=assessment.name,
            assessment_type=assessment.assessment_type,
            total_questions=assessment.total_questions,
            expected_duration=assessment.expected_duration // 60 if assessment.expected_duration else 0,
            questions_text=questions_text,
            is_standalone=is_standalone
        )

        return self._call_llm(prompt, "combined analysis")

    def _check_edge_cases(
        self, assessment: Assessment, result: AQSResult, is_standalone: bool
    ) -> None:
        """Check for edge cases and add appropriate warnings."""
        # Few questions warning
        threshold = self.prompt_manager.get_few_questions_threshold()
        if assessment.total_questions < threshold:
            warning = self.prompt_manager.get_edge_case_warning(
                "few_questions", question_count=assessment.total_questions
            )
            if warning:
                result.warnings.append(warning)
            result.confidence_flags.append("Low question count")

        # No questions at all
        if not assessment.questions:
            result.warnings.append(
                "No question details available - evaluation based on metadata only"
            )
            result.confidence_flags.append("Missing question details")

    def _check_difficulty_mismatch(
        self,
        difficulty_result: dict,
        fit_result: dict,
        result: AQSResult
    ) -> None:
        """Check for difficulty mismatch between assessment and course."""
        threshold = self.prompt_manager.get_difficulty_mismatch_threshold()

        # Simple mismatch detection based on difficulty appropriateness score
        appropriateness = fit_result.get("difficulty_appropriateness_score", 100)
        
        # Handle None values - treat as perfect alignment to avoid errors
        if appropriateness is None:
            appropriateness = 100
            
        if appropriateness < (100 - threshold):
            alert = self.prompt_manager.get_edge_case_warning(
                "difficulty_mismatch",
                assessment_difficulty=difficulty_result.get("difficulty_level", "Unknown"),
                course_level="Expected",
                mismatch_score=100 - appropriateness
            )
            if alert:
                result.warnings.append(alert)

    def _analyze_difficulty(
        self,
        course_data: CourseData,
        assessment: Assessment,
        questions_text: str
    ) -> tuple[dict, TokenMetrics, bool]:
        """Analyze assessment difficulty level."""
        prompt = self.prompt_manager.get_difficulty_analysis_prompt(
            course_title=course_data.metadata.name,
            course_description=course_data.metadata.description,
            course_level=course_data.metadata.primary_category,
            assessment_name=assessment.name,
            assessment_type=assessment.assessment_type,
            total_questions=assessment.total_questions,
            expected_duration=assessment.expected_duration // 60 if assessment.expected_duration else 0,
            questions_text=questions_text
        )

        return self._call_llm(prompt, "difficulty analysis")

    def _analyze_blooms_taxonomy(self, questions_text: str) -> tuple[dict, TokenMetrics, bool]:
        """Analyze questions against Bloom's taxonomy."""
        prompt = self.prompt_manager.get_blooms_taxonomy_prompt(
            questions_with_options=questions_text
        )

        return self._call_llm(prompt, "Bloom's taxonomy analysis")

    def _analyze_course_fit(
        self,
        course_data: CourseData,
        assessment: Assessment,
        questions_text: str,
        content_summary: str
    ) -> tuple[dict, TokenMetrics, bool]:
        """
        Analyze assessment fit with course content.
        
        For Final Assessments: Compare against ALL course modules
        For Module Assessments: Compare against ONLY the associated module content
        """
        competencies = ", ".join(course_data.metadata.competencies)
        
        # Determine content to use based on assessment type
        if assessment.is_final_assessment:
            # Final assessment: use full course content
            effective_content_summary = content_summary
            content_scope = "Full Course"
        elif assessment.module_content and (assessment.module_content.transcript or assessment.module_content.pdf_text):
            # Module assessment: use only the associated module content
            module_content = assessment.module_content
            parts = [f"Module: {module_content.module_name}"]
            if module_content.transcript:
                parts.append(f"\nModule Transcript:\n{module_content.transcript}")
            if module_content.pdf_text:
                parts.append(f"\nModule PDF Content:\n{module_content.pdf_text}")
            effective_content_summary = "\n".join(parts)
            if len(effective_content_summary) > 10000:
                effective_content_summary = effective_content_summary[:10000] + "... [truncated]"
            content_scope = f"Module: {assessment.associated_module}"
        else:
            # Fallback to full course content if module content not available
            effective_content_summary = content_summary
            content_scope = "Full Course (module content not available)"

        prompt = self.prompt_manager.get_course_fit_prompt(
            course_title=course_data.metadata.name,
            course_description=course_data.metadata.description,
            learning_objectives=course_data.metadata.description,  # Using description as objectives
            competencies=competencies,
            course_content_summary=effective_content_summary,
            questions_text=questions_text
        )

        return self._call_llm(prompt, f"course fit analysis ({content_scope})")

    def _compute_final_aqs(
        self,
        difficulty_result: dict,
        blooms_result: dict,
        course_fit_score: float,
        is_standalone: bool
    ) -> float:
        """
        Compute final AQS score.

        Formula:
        - For regular assessments:
          AQS = (Difficulty × 0.25) + (Blooms × 0.35) + (Course Fit × 0.40)
        - For standalone assessments:
          AQS = (Difficulty × 0.40) + (Blooms × 0.60)
        """
        # Calculate difficulty component (average of sub-scores × 10)
        diff_scores = [
            difficulty_result.get("complexity_score", 5),
            difficulty_result.get("language_difficulty_score", 5),
            difficulty_result.get("cognitive_effort_score", 5),
            difficulty_result.get("course_alignment_score", 5)
        ]
        difficulty_component = (sum(diff_scores) / len(diff_scores)) * 10

        # Calculate Bloom's component (weighted cognitive depth)
        blooms_scores = blooms_result.get("blooms_scores", {})
        weights = self.prompt_manager.get_blooms_weights()

        total_weighted = 0
        total_weight = 0
        for level, weight in weights.items():
            score = blooms_scores.get(level, 0)
            total_weighted += score * weight
            total_weight += weight

        # Normalize to 0-100
        if total_weight > 0:
            blooms_component = (total_weighted / total_weight) * (100 / max(weights.values()))
        else:
            blooms_component = 50  # Default if no scores

        # Calculate final AQS
        if is_standalone:
            aqs = (difficulty_component * 0.40) + (blooms_component * 0.60)
        else:
            aqs = (
                (difficulty_component * 0.25) +
                (blooms_component * 0.35) +
                (course_fit_score * 0.40)
            )

        return round(min(100, max(0, aqs)), 2)

    def _get_aqs_quality_tier(self, aqs_score: float) -> str:
        """
        Determine quality tier based on AQS score.
        
        Tiers from prompts:
        - Excellent: >= 85
        - Good: >= 70
        - Satisfactory: >= 55
        - Needs Improvement: >= 40
        - Poor: < 40
        """
        if aqs_score >= 85:
            return "Excellent"
        elif aqs_score >= 70:
            return "Good"
        elif aqs_score >= 55:
            return "Satisfactory"
        elif aqs_score >= 40:
            return "Needs Improvement"
        else:
            return "Poor"

    def _call_llm(self, prompt: str, analysis_type: str) -> tuple[dict, TokenMetrics, bool]:
        """
        Call the LLM and parse JSON response.

        Args:
            prompt: The prompt to send
            analysis_type: Type of analysis for error messages

        Returns:
            Tuple of (parsed JSON response, token metrics, success flag)
        """
        from google.genai import types
        
        system_role = self.prompt_manager.get_system_role()
        # For google-genai SDK, system instructions are passed in config, not prepended to prompt
        # But to minimize changes to prompt structure, we can keep it prepended if the model supports it, 
        # or better, use the system_instruction parameter if we want to be cleaner.
        # However, the previous implementation prepended it: f"{system_role}\n\n{prompt}"
        # Let's stick to the previous behavior for prompt fidelity, or use the proper config.
        # The prompt_manager.get_system_role() returns a string. 
        # Let's use the explicit system_instruction in GenerateContentConfig for better separation.
        
        metrics = TokenMetrics()

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_role,
                    temperature=0.1,
                )
            )

            # Extract token usage from response
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                metrics.input_tokens = getattr(usage, 'prompt_token_count', 0) or 0
                metrics.output_tokens = getattr(usage, 'candidates_token_count', 0) or 0
                metrics.thinking_tokens = getattr(usage, 'thoughts_token_count', 0) or 0
                metrics.cached_tokens = getattr(usage, 'cached_content_token_count', 0) or 0
                metrics.total_tokens = getattr(usage, 'total_token_count', 0)

            # Extract JSON from response
            response_text = response.text
            return self._extract_json(response_text), metrics, True

        except Exception as e:
            print(f"Error in {analysis_type}: {e}")
            return {"error": str(e)}, metrics, False

    def _extract_json(self, text: str) -> dict:
        """Extract JSON object from LLM response text."""
        # Try to find JSON block in markdown code fence
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Try parsing the entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def evaluate_course(
        self,
        course_data: CourseData
    ) -> list[AQSResult]:
        """
        Evaluate all assessments in a course.

        Args:
            course_data: Complete course data with assessments

        Returns:
            List of AQSResult for each assessment
        """
        results = []

        for assessment in course_data.assessments:
            result = self.evaluate_assessment(course_data, assessment)
            results.append(result)

        return results


def evaluate_course_from_path(
    data_dir: str,
    course_id: str,
    api_key: str,
    output_dir: Optional[str] = None
) -> list[dict]:
    """
    Convenience function to evaluate a course from file path.

    Args:
        data_dir: Path to data directory
        course_id: Course identifier
        api_key: Google AI API key
        output_dir: Optional output directory for results

    Returns:
        List of AQS results as dictionaries
    """
    import os
    from pathlib import Path

    # Load course data
    loader = AssessmentDataLoader(data_dir)
    course_data = loader.load_course(course_id)

    if not course_data:
        raise ValueError(f"Could not load course: {course_id}")

    # Evaluate assessments
    evaluator = AQSEvaluator(api_key)
    results = evaluator.evaluate_course(course_data)

    # Convert to dicts
    result_dicts = [r.to_dict() for r in results]

    # Save to output directory if specified
    if output_dir:
        output_path = Path(output_dir) / course_id
        output_path.mkdir(parents=True, exist_ok=True)

        for result in results:
            safe_name = result.assessment_name.replace(" ", "_").replace("/", "_")
            output_file = output_path / f"{safe_name}_aqs.json"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.to_json(indent=2))

    return result_dicts
