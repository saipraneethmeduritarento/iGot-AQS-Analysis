"""
Assessment Quality Score (AQS) Module

This module provides functionality to evaluate educational assessments
and generate quality scores based on:
- Difficulty level analysis
- Bloom's taxonomy scoring
- Course content alignment
"""

from .aqs_evaluator import (
    AQSEvaluator,
    AQSResult,
    BloomsScores,
    TokenMetrics,
    TokenEvaluationMetrics as EvaluationMetrics
)
from .data_loader import (
    AssessmentDataLoader,
    Assessment,
    CourseData,
    CourseMetadata,
    CourseContent,
    Question
)
from .prompt_manager import PromptManager
from .checkpoint_manager import CheckpointManager
from .utils import (
    load_json_file,
    save_json_file,
    calculate_bloom_cognitive_depth,
    generate_summary_report,
    sanitize_filename
)

__all__ = [
    "AQSEvaluator",
    "AQSResult",
    "BloomsScores",
    "TokenMetrics",
    "EvaluationMetrics",
    "AssessmentDataLoader",
    "Assessment",
    "CourseData",
    "CourseMetadata",
    "CourseContent",
    "Question",
    "PromptManager",
    "CheckpointManager",
    "load_json_file",
    "save_json_file",
    "calculate_bloom_cognitive_depth",
    "generate_summary_report",
    "sanitize_filename"
]
__version__ = "0.1.0"
