"""
Utility functions for Assessment Quality Score System

Provides helper functions for common operations.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


def load_json_file(file_path: str) -> Optional[dict[str, Any]]:
    """
    Safely load a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed JSON as dict or None if error
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
        print(f"Error loading {file_path}: {e}")
        return None


def save_json_file(data: dict[str, Any], file_path: str, indent: int = 2) -> bool:
    """
    Save data to a JSON file.

    Args:
        data: Data to save
        file_path: Path to save to
        indent: JSON indentation

    Returns:
        True if successful, False otherwise
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except (IOError, TypeError) as e:
        print(f"Error saving {file_path}: {e}")
        return False


def get_assessment_type_from_name(name: str) -> str:
    """
    Determine assessment type from its name.

    Args:
        name: Assessment name

    Returns:
        Assessment type classification
    """
    name_lower = name.lower()

    if "final" in name_lower:
        return "Final Assessment"
    elif "practice" in name_lower or "quiz" in name_lower:
        if "advanced" in name_lower:
            return "Practice Assessment - Advanced"
        else:
            return "Practice Assessment - Basic"
    else:
        return "Standalone Assessment"


def calculate_bloom_cognitive_depth(blooms_scores: dict[str, float]) -> float:
    """
    Calculate weighted cognitive depth from Bloom's scores.

    Higher-order thinking skills receive greater weight.

    Args:
        blooms_scores: Dict of Bloom's level scores

    Returns:
        Weighted cognitive depth score (0-100)
    """
    weights = {
        "remember": 1.0,
        "understand": 1.5,
        "apply": 2.0,
        "analyze": 2.5,
        "evaluate": 3.0,
        "create": 3.5
    }

    total_weighted = 0
    total_weight = 0

    for level, weight in weights.items():
        score = blooms_scores.get(level, 0)
        total_weighted += score * weight
        total_weight += weight

    if total_weight == 0:
        return 0

    # Normalize to 0-100
    max_possible = 100 * max(weights.values())
    return (total_weighted / total_weight) * (100 / max(weights.values()))


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours} hour{'s' if hours != 1 else ''}"


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string for use as a filename.

    Args:
        name: Original name

    Returns:
        Sanitized filename-safe string
    """
    # Replace problematic characters
    replacements = {
        "/": "_",
        "\\": "_",
        ":": "_",
        "*": "_",
        "?": "_",
        '"': "_",
        "<": "_",
        ">": "_",
        "|": "_",
        " ": "_"
    }

    result = name
    for old, new in replacements.items():
        result = result.replace(old, new)

    # Remove consecutive underscores
    while "__" in result:
        result = result.replace("__", "_")

    return result.strip("_")


def extract_text_from_vtt(vtt_content: str) -> str:
    """
    Extract plain text from VTT subtitle content.

    Args:
        vtt_content: Raw VTT file content

    Returns:
        Plain text transcript
    """
    lines = vtt_content.split("\n")
    text_lines = []

    for line in lines:
        line = line.strip()
        # Skip empty lines, headers, timestamps, and markers
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if line.startswith("NOTE"):
            continue
        if "-->" in line:
            continue
        if line.isdigit():
            continue
        if line.startswith("[") and line.endswith("]"):
            continue

        text_lines.append(line)

    return " ".join(text_lines)


def generate_summary_report(results: list[dict]) -> dict:
    """
    Generate a summary report from multiple AQS results.

    Args:
        results: List of AQS result dictionaries

    Returns:
        Summary report dictionary
    """
    if not results:
        return {"error": "No results to summarize"}

    total_score = sum(r.get("aqs_score", 0) for r in results)
    avg_score = total_score / len(results)

    # Count by difficulty
    difficulty_counts = {"Basic": 0, "Intermediate": 0, "Advanced": 0}
    for r in results:
        level = r.get("difficulty_level", "Unknown")
        if level in difficulty_counts:
            difficulty_counts[level] += 1

    # Count by fit status
    fit_status_counts = {}
    for r in results:
        status = r.get("course_fit_status", "Unknown")
        fit_status_counts[status] = fit_status_counts.get(status, 0) + 1

    # Aggregate Bloom's scores
    blooms_totals = {
        "remember": 0, "understand": 0, "apply": 0,
        "analyze": 0, "evaluate": 0, "create": 0
    }
    for r in results:
        scores = r.get("blooms_scores", {})
        for level in blooms_totals:
            blooms_totals[level] += scores.get(level, 0)

    blooms_averages = {
        level: total / len(results) for level, total in blooms_totals.items()
    }

    # Collect all warnings
    all_warnings = []
    for r in results:
        all_warnings.extend(r.get("warnings", []))

    return {
        "total_assessments": len(results),
        "average_aqs_score": round(avg_score, 2),
        "difficulty_distribution": difficulty_counts,
        "course_fit_distribution": fit_status_counts,
        "average_blooms_scores": blooms_averages,
        "total_warnings": len(all_warnings),
        "unique_warnings": list(set(all_warnings))
    }
