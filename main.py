"""
Assessment Quality Score (AQS) System

Main entry point for evaluating educational assessments on the iGOT platform.
Generates quality scores based on difficulty analysis, Bloom's taxonomy,
and course content alignment.

Supports multiple models for comparison evaluation.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List
from datetime import datetime
import time

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from scripts.assessment_quality_score import (
    AQSEvaluator,
    AssessmentDataLoader,
    PromptManager,
    CheckpointManager
)
from scripts.assessment_quality_score.config import settings



def get_models_from_env() -> List[str]:
    """Parse models from settings.gemini_model_name."""
    model_str = settings.gemini_model_name
    
    # Handle JSON array format
    if model_str.startswith("["):
        try:
            models = json.loads(model_str)
            return [m.strip() for m in models if m.strip()]
        except json.JSONDecodeError:
            pass
    
    # Handle comma-separated format
    if "," in model_str:
        return [m.strip() for m in model_str.split(",") if m.strip()]
    
    # Single model
    return [model_str.strip()]


def result_to_txt(result: dict, course_name: str = "") -> str:
    """Convert AQS result to human-readable text format."""
    lines = []
    lines.append("=" * 70)
    lines.append("ASSESSMENT QUALITY SCORE (AQS) REPORT")
    lines.append("=" * 70)
    
    if course_name:
        lines.append(f"\nCourse: {course_name}")
    
    lines.append(f"\nAssessment: {result.get('assessment_name', 'N/A')}")
    lines.append(f"Type: {result.get('assessment_type', 'N/A')}")
    lines.append("")
    
    # SCORES SECTION
    lines.append("-" * 40)
    lines.append("SCORES")
    lines.append("-" * 40)
    lines.append(f"  AQS Score: {result.get('aqs_score', 0)}/100")
    lines.append(f"  AQS Quality Tier: {result.get('aqs_quality_tier', 'N/A')}")
    lines.append(f"  Difficulty Level: {result.get('difficulty_level', 'N/A')}")
    lines.append(f"  Course Fit: {result.get('course_fit_status', 'N/A')} ({result.get('course_fit_score', 0)})")
    lines.append("")
    
    # DIFFICULTY ANALYSIS SECTION
    lines.append("-" * 40)
    lines.append("DIFFICULTY ANALYSIS")
    lines.append("-" * 40)
    lines.append(f"  {result.get('difficulty_rationale', 'N/A')}")
    lines.append("")
    
    # Difficulty sub-scores
    diff_scores = result.get('difficulty_scores', {})
    if any(diff_scores.values()):
        lines.append("  Sub-scores (1-10 scale):")
        lines.append(f"    Complexity:         {diff_scores.get('complexity_score', 0)}")
        lines.append(f"    Language Difficulty: {diff_scores.get('language_difficulty_score', 0)}")
        lines.append(f"    Cognitive Effort:   {diff_scores.get('cognitive_effort_score', 0)}")
        lines.append(f"    Course Alignment:   {diff_scores.get('course_alignment_score', 0)}")
        lines.append("")
    
    # BLOOM'S TAXONOMY SECTION
    lines.append("-" * 40)
    lines.append("BLOOM'S TAXONOMY DISTRIBUTION")
    lines.append("-" * 40)
    blooms = result.get('blooms_scores', {})
    for level in ['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create']:
        score = blooms.get(level, 0)
        if score > 0:
            bar = "█" * int(score / 5) if score >= 5 else "▌"
            lines.append(f"  {level.capitalize():12} {score:6.2f}% {bar}")
    lines.append("")
    lines.append(f"  Summary: {result.get('blooms_distribution_summary', 'N/A')}")
    lines.append("")
    
    # Per-question classifications
    question_classifications = result.get('question_classifications', [])
    if question_classifications:
        lines.append("  Per-Question Classifications:")
        for qc in question_classifications:
            q_num = qc.get('question_number', 0)
            q_level = qc.get('blooms_level', 'N/A')
            q_just = qc.get('justification', '')
            lines.append(f"    Q{q_num}: {q_level} - {q_just}")
        lines.append("")
    
    # COURSE FIT DETAILS SECTION
    fit_details = result.get('course_fit_details', {})
    if fit_details and any(fit_details.values()):
        lines.append("-" * 40)
        lines.append("COURSE FIT DETAILS")
        lines.append("-" * 40)
        lines.append(f"  Content Coverage:         {fit_details.get('content_coverage_score', 0)}/100")
        lines.append(f"  Objective Alignment:      {fit_details.get('objective_alignment_score', 0)}/100")
        lines.append(f"  Difficulty Appropriateness: {fit_details.get('difficulty_appropriateness_score', 0)}/100")
        lines.append(f"  Completeness:             {fit_details.get('completeness_score', 0)}/100")
        if fit_details.get('alignment_details'):
            lines.append(f"\n  Analysis: {fit_details.get('alignment_details', 'N/A')}")
        
        suggestions = fit_details.get('improvement_suggestions', [])
        if suggestions:
            lines.append("\n  Improvement Suggestions:")
            for suggestion in suggestions:
                lines.append(f"    • {suggestion}")
        lines.append("")
    
    # WARNINGS SECTION
    if result.get('warnings'):
        lines.append("-" * 40)
        lines.append("WARNINGS")
        lines.append("-" * 40)
        for warning in result['warnings']:
            lines.append(f"  ⚠ {warning}")
        lines.append("")
    
    # CONFIDENCE FLAGS SECTION
    if result.get('confidence_flags'):
        lines.append("-" * 40)
        lines.append("CONFIDENCE FLAGS")
        lines.append("-" * 40)
        for flag in result['confidence_flags']:
            lines.append(f"  • {flag}")
        lines.append("")
    
    # METRICS SECTION
    metrics = result.get('metrics', {})
    if metrics:
        lines.append("-" * 40)
        lines.append("METRICS")
        lines.append("-" * 40)
        lines.append(f"  Duration: {metrics.get('duration_seconds', 0):.2f}s")
        token_usage = metrics.get('token_usage', {})
        lines.append(f"  Input Tokens: {token_usage.get('input_tokens', 0):,}")
        lines.append(f"  Output Tokens: {token_usage.get('output_tokens', 0):,}")
        lines.append(f"  Thinking Tokens: {token_usage.get('thinking_tokens', 0):,}")
        lines.append(f"  Total Tokens: {token_usage.get('total_tokens', 0):,}")
        llm_calls = metrics.get('llm_calls', {})
        lines.append(f"  LLM Calls: {llm_calls.get('successful', 0)}/{llm_calls.get('total', 0)} successful")
        
        # Cost information
        cost = metrics.get('cost', {})
        if cost:
            lines.append(f"\n  Cost ({cost.get('pricing_model', 'N/A')}):")
            lines.append(f"    Input Cost:  ${cost.get('input_cost_usd', 0):.6f}")
            lines.append(f"    Output Cost: ${cost.get('output_cost_usd', 0):.6f}")
            lines.append(f"    Total Cost:  ${cost.get('total_cost_usd', 0):.6f}")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def course_summary_to_txt(course_data: dict) -> str:
    """Convert course summary to human-readable text format."""
    lines = []
    lines.append("=" * 70)
    lines.append("COURSE EVALUATION SUMMARY")
    lines.append("=" * 70)
    
    lines.append(f"\nCourse ID: {course_data.get('course_id', 'N/A')}")
    lines.append(f"Course Name: {course_data.get('course_name', 'N/A')}")
    if course_data.get('model_name'):
        lines.append(f"Model Used: {course_data.get('model_name')}")
    lines.append(f"Total Assessments: {course_data.get('total_assessments', 0)}")
    lines.append("")
    
    assessments = course_data.get('assessments', [])
    if assessments:
        lines.append("-" * 40)
        lines.append("ASSESSMENT SCORES")
        lines.append("-" * 40)
        lines.append(f"{'Assessment':<30} {'AQS':>8} {'Difficulty':<15} {'Course Fit':<20}")
        lines.append("-" * 75)
        
        for a in assessments:
            name = a.get('assessment_name', 'N/A')[:28]
            aqs = a.get('aqs_score', 0)
            diff = a.get('difficulty_level', 'N/A')
            fit = f"{a.get('course_fit_status', 'N/A')} ({a.get('course_fit_score', 0)})"
            lines.append(f"{name:<30} {aqs:>7.2f} {diff:<15} {fit:<20}")
        
        lines.append("")
        
        # Calculate averages
        avg_aqs = sum(a.get('aqs_score', 0) for a in assessments) / len(assessments)
        avg_fit = sum(a.get('course_fit_score', 0) for a in assessments) / len(assessments)
        lines.append(f"Average AQS Score: {avg_aqs:.2f}/100")
        lines.append(f"Average Course Fit: {avg_fit:.2f}/100")
    
    # Add token and cost metrics if available
    metrics = course_data.get('metrics', {})
    if metrics:
        lines.append("")
        lines.append("-" * 40)
        lines.append("OVERALL METRICS")
        lines.append("-" * 40)
        lines.append(f"Total Duration: {metrics.get('total_duration_seconds', 0):.2f}s")
        lines.append(f"")
        lines.append(f"Token Usage:")
        lines.append(f"  Input Tokens:  {metrics.get('total_input_tokens', 0):,}")
        lines.append(f"  Output Tokens: {metrics.get('total_output_tokens', 0):,}")
        lines.append(f"  Thinking Tokens: {metrics.get('total_thinking_tokens', 0):,}")
        lines.append(f"  Total Tokens:  {metrics.get('total_tokens', 0):,}")
        lines.append(f"")
        lines.append(f"Cost Summary ({course_data.get('model_name', 'N/A')}):")
        lines.append(f"  Input Cost:  ${metrics.get('total_input_cost_usd', 0):.6f}")
        lines.append(f"  Output Cost: ${metrics.get('total_output_cost_usd', 0):.6f}")
        lines.append(f"  Total Cost:  ${metrics.get('total_cost_usd', 0):.6f}")
        lines.append(f"")
        lines.append(f"LLM Calls: {metrics.get('successful_llm_calls', 0)}/{metrics.get('total_llm_calls', 0)} successful")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def validate_config() -> None:
    """Validate required configuration is present."""
    # Pydantic settings will validate required fields on instantiation
    # Just verify that the settings were loaded correctly
    if not settings.google_project_id:
        raise ValueError(
            "Missing required configuration: GOOGLE_PROJECT_ID\n"
            "Please ensure .env file is configured with GOOGLE_PROJECT_ID"
        )


def list_courses(data_dir: str) -> None:
    """List all available courses in the data directory."""
    loader = AssessmentDataLoader(data_dir)
    courses = loader.get_available_courses()

    if not courses:
        print("No courses found in the data directory.")
        return

    print(f"\nFound {len(courses)} courses:\n")
    for course_id in sorted(courses):
        # Try to load metadata for course name
        course_data = loader.load_course(course_id)
        if course_data:
            print(f"  {course_id}")
            print(f"    Name: {course_data.metadata.name}")
            print(f"    Assessments: {len(course_data.assessments)}")
            print()
        else:
            print(f"  {course_id} (metadata unavailable)")


def evaluate_single_course(
    data_dir: str,
    course_id: str,
    output_dir: str,
    verbose: bool = False,
    model_name: str = None,
    force_restart: bool = False
) -> None:
    """Evaluate all assessments in a single course."""
    import time
    from datetime import datetime
    
    course_start_time = time.time()
    print(f"\nLoading course: {course_id}")
    
    # Determine model to use
    if model_name is None:
        model_name = get_models_from_env()[0]
    print(f"Using model: {model_name}")

    loader = AssessmentDataLoader(data_dir)
    course_data = loader.load_course(course_id)

    if not course_data:
        print(f"Error: Could not load course {course_id}")
        return

    print(f"Course: {course_data.metadata.name}")
    print(f"Found {len(course_data.assessments)} assessments")

    if course_data.warnings:
        print("\nWarnings during data loading:")
        for warning in course_data.warnings:
            print(f"  ⚠ {warning}")

    if not course_data.assessments:
        print("No assessments to evaluate.")
        return

    # Initialize evaluator with Vertex AI
    evaluator = AQSEvaluator(model_name=model_name)

    # Create output directory
    output_path = Path(output_dir) / course_id
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize checkpoint manager
    checkpoint_manager = CheckpointManager()
    
    # Load checkpoint (unless force_restart is True)
    checkpoint = None if force_restart else checkpoint_manager.load_checkpoint(model_name, course_id)
    completed_assessments = checkpoint_manager.get_completed_assessments(checkpoint)
    
    if checkpoint and not force_restart:
        print(f"\n📋 Found checkpoint: {checkpoint['completed_count']}/{checkpoint['total_assessments']} assessments completed")
        print(f"   Resuming from where we left off...")
    elif force_restart and checkpoint:
        print(f"\n🔄 Force restart enabled - ignoring checkpoint")
        checkpoint_manager.clear_checkpoint(model_name, course_id)

    # Initialize course-level metrics
    course_metrics = {
        "course_id": course_id,
        "course_name": course_data.metadata.name,
        "model_name": model_name,
        "start_time": datetime.now().isoformat(),
        "end_time": "",
        "total_duration_seconds": 0,
        "total_assessments": len(course_data.assessments),
        "successful_evaluations": 0,
        "failed_evaluations": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_thinking_tokens": 0,
        "total_tokens": 0,
        "total_input_cost_usd": 0.0,
        "total_output_cost_usd": 0.0,
        "total_cost_usd": 0.0,
        "total_llm_calls": 0,
        "successful_llm_calls": 0,
        "failed_llm_calls": 0,
        "assessment_metrics": []
    }

    # Evaluate each assessment
    all_results = []
    for i, assessment in enumerate(course_data.assessments, 1):
        # Check if assessment is already completed
        if assessment.name in completed_assessments:
            print(f"\n[{i}/{len(course_data.assessments)}] ⏭️  Skipping (already completed): {assessment.name}")
            continue
        
        print(f"\n[{i}/{len(course_data.assessments)}] Evaluating: {assessment.name}")
        print(f"  Type: {assessment.assessment_type}")
        print(f"  Questions: {assessment.total_questions}")

        try:
            result = evaluator.evaluate_assessment(course_data, assessment)
            all_results.append(result.to_dict())
            course_metrics["successful_evaluations"] += 1

            # Aggregate metrics
            metrics = result.metrics
            course_metrics["total_input_tokens"] += metrics.total_input_tokens
            course_metrics["total_output_tokens"] += metrics.total_output_tokens
            course_metrics["total_thinking_tokens"] += metrics.total_thinking_tokens
            course_metrics["total_tokens"] += metrics.total_tokens
            course_metrics["total_input_cost_usd"] += metrics.total_input_cost
            course_metrics["total_output_cost_usd"] += metrics.total_output_cost
            course_metrics["total_cost_usd"] += metrics.total_cost
            course_metrics["total_llm_calls"] += metrics.llm_calls
            course_metrics["successful_llm_calls"] += metrics.successful_calls
            course_metrics["failed_llm_calls"] += metrics.failed_calls
            course_metrics["assessment_metrics"].append(metrics.to_dict())

            # Print summary
            print(f"\n  Results:")
            print(f"    Difficulty: {result.difficulty_level}")
            print(f"    AQS Score: {result.aqs_score}/100")
            print(f"    Course Fit: {result.course_fit_status} ({result.course_fit_score})")
            
            # Print metrics
            print(f"\n  📊 Metrics:")
            print(f"    ⏱  Time: {metrics.duration_seconds:.2f}s")
            print(f"    📥 Input tokens: {metrics.total_input_tokens:,}")
            print(f"    📤 Output tokens: {metrics.total_output_tokens:,}")
            print(f"    🧠 Thinking tokens: {metrics.total_thinking_tokens:,}")
            print(f"    📦 Total tokens: {metrics.total_tokens:,}")
            print(f"    💵 Cost: ${metrics.total_cost:.6f}")
            print(f"    🔄 LLM calls: {metrics.successful_calls}/{metrics.llm_calls} successful")

            if verbose:
                print(f"\n    Bloom's Scores:")
                for level, score in result.blooms_scores.__dict__.items():
                    if score > 0:
                        print(f"      {level.capitalize()}: {score}%")

            if result.warnings:
                print(f"\n    Warnings:")
                for warning in result.warnings:
                    print(f"      ⚠ {warning}")

            # Save individual result - JSON
            safe_name = assessment.name.replace(" ", "_").replace("/", "_")
            if assessment.assessment_type.startswith("Practice Assessment - "):
                type_safe = assessment.assessment_type.replace(" ", "_").replace("/", "_")
                safe_name = type_safe
            output_file = output_path / f"{safe_name}_aqs.json"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.to_json(indent=2))
            
            # Save individual result - TXT
            txt_file = output_path / f"{safe_name}_aqs.txt"
            write_mode = "w"
            if assessment.assessment_type.startswith("Practice Assessment - "):
                write_mode = "a"
            with open(txt_file, write_mode, encoding="utf-8") as f:
                if write_mode == "a" and txt_file.exists():
                    f.write("\n\n")
                f.write(result_to_txt(result.to_dict(), course_data.metadata.name))
            
            print(f"\n  Saved to: {output_file}")
            print(f"  Saved to: {txt_file}")
            
            # Save checkpoint after successful evaluation
            completed_assessments.append(assessment.name)
            checkpoint_manager.save_checkpoint(
                model_name=model_name,
                course_id=course_id,
                course_name=course_data.metadata.name,
                total_assessments=len(course_data.assessments),
                completed_assessments=completed_assessments
            )

        except Exception as e:
            print(f"  Error evaluating assessment: {e}")
            course_metrics["failed_evaluations"] += 1
            if verbose:
                import traceback
                traceback.print_exc()

    # Finalize course metrics
    course_end_time = time.time()
    course_metrics["end_time"] = datetime.now().isoformat()
    course_metrics["total_duration_seconds"] = round(course_end_time - course_start_time, 2)

    # Print course summary
    print("\n" + "=" * 60)
    print("📈 COURSE EVALUATION SUMMARY")
    print("=" * 60)
    print(f"  Model: {model_name}")
    print(f"  Course: {course_data.metadata.name}")
    print(f"  Total Time: {course_metrics['total_duration_seconds']:.2f}s")
    print(f"  Assessments: {course_metrics['successful_evaluations']}/{course_metrics['total_assessments']} successful")
    print(f"\n  Token Usage:")
    print(f"    📥 Total Input: {course_metrics['total_input_tokens']:,}")
    print(f"    📤 Total Output: {course_metrics['total_output_tokens']:,}")
    print(f"    🧠 Total Thinking: {course_metrics.get('total_thinking_tokens', 0):,}")
    print(f"    📦 Grand Total: {course_metrics['total_tokens']:,}")
    print(f"\n  💰 Cost Summary:")
    print(f"    Input Cost:  ${course_metrics['total_input_cost_usd']:.6f}")
    print(f"    Output Cost: ${course_metrics['total_output_cost_usd']:.6f}")
    print(f"    Total Cost:  ${course_metrics['total_cost_usd']:.6f}")
    print(f"\n  LLM Calls: {course_metrics['successful_llm_calls']}/{course_metrics['total_llm_calls']} successful")
    print("=" * 60)

    # Save combined results
    if all_results:
        combined_data = {
            "course_id": course_id,
            "course_name": course_data.metadata.name,
            "model_name": model_name,
            "total_assessments": len(all_results),
            "assessments": all_results,
            "metrics": {
                "total_duration_seconds": course_metrics["total_duration_seconds"],
                "total_input_tokens": course_metrics["total_input_tokens"],
                "total_output_tokens": course_metrics["total_output_tokens"],
                "total_thinking_tokens": course_metrics["total_thinking_tokens"],
                "total_tokens": course_metrics["total_tokens"],
                "total_input_cost_usd": course_metrics["total_input_cost_usd"],
                "total_output_cost_usd": course_metrics["total_output_cost_usd"],
                "total_cost_usd": course_metrics["total_cost_usd"],
                "total_llm_calls": course_metrics["total_llm_calls"],
                "successful_llm_calls": course_metrics["successful_llm_calls"],
                "failed_llm_calls": course_metrics["failed_llm_calls"]
            }
        }
        
        # JSON format
        combined_file = output_path / "all_assessments_aqs.json"
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=2)
        print(f"\nCombined results saved to: {combined_file}")
        
        # TXT format
        combined_txt_file = output_path / "all_assessments_aqs.txt"
        with open(combined_txt_file, "w", encoding="utf-8") as f:
            f.write(course_summary_to_txt(combined_data))
            f.write("\n\n")
            for result in all_results:
                f.write(result_to_txt(result, course_data.metadata.name))
                f.write("\n\n")
        print(f"Combined results saved to: {combined_txt_file}")

    # Save log file with metrics
    log_file = output_path / "evaluation_log.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(course_metrics, f, indent=2)
    print(f"Metrics log saved to: {log_file}")
    
    # Clear checkpoint after successful completion
    checkpoint_manager.clear_checkpoint(model_name, course_id)
    print(f"✅ Course evaluation complete - checkpoint cleared")


def evaluate_all_courses(
    data_dir: str,
    output_dir: str,
    verbose: bool = False,
    model_name: str = None,
    force_restart: bool = False
) -> None:
    """Evaluate all courses in the data directory."""
    loader = AssessmentDataLoader(data_dir)
    courses = loader.get_available_courses()

    if not courses:
        print("No courses found.")
        return

    print(f"Found {len(courses)} courses to evaluate.\n")

    for course_id in sorted(courses):
        try:
            evaluate_single_course(data_dir, course_id, output_dir, verbose, model_name, force_restart)
        except Exception as e:
            print(f"Error evaluating course {course_id}: {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 60)
    print("Evaluation complete!")


def evaluate_with_multiple_models(
    data_dir: str,
    output_dir: str,
    course_id: str = None,
    verbose: bool = False,
    force_restart: bool = False
) -> None:
    """Evaluate using all models defined in .env file."""
    models = get_models_from_env()
    
    print(f"\n🤖 Running evaluation with {len(models)} models:")
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")
    print()
    
    loader = AssessmentDataLoader(data_dir)
    
    # Get courses to evaluate
    if course_id:
        courses = [course_id]
    else:
        courses = loader.get_available_courses()
    
    if not courses:
        print("No courses found.")
        return
    
    # Evaluate with each model
    for model_idx, model_name in enumerate(models, 1):
        print("\n" + "=" * 70)
        print(f"🤖 MODEL {model_idx}/{len(models)}: {model_name}")
        print("=" * 70)
        
        # Create model-specific output directory
        model_output_dir = Path(output_dir) / model_name
        
        for course_id in sorted(courses):
            try:
                evaluate_single_course(
                    data_dir, 
                    course_id, 
                    str(model_output_dir), 
                    verbose, 
                    model_name,
                    force_restart
                )
            except Exception as e:
                print(f"Error evaluating course {course_id} with model {model_name}: {e}")
                if verbose:
                    import traceback
                    traceback.print_exc()
    
    # Print final summary
    print("\n" + "=" * 70)
    print("🎉 MULTI-MODEL EVALUATION COMPLETE!")
    print("=" * 70)
    print("\nOutput directories created:")
    for model in models:
        model_path = Path(output_dir) / model
        print(f"  📁 {model_path}")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Assessment Quality Score (AQS) Evaluator for iGOT Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available courses
  python main.py --list

  # Evaluate a specific course with all models from .env
  python main.py --course do_113955620332421120130 --multi-model

  # Evaluate all courses with all models
  python main.py --all --multi-model

  # Evaluate with a specific model only
  python main.py --course do_113955620332421120130 --model gemini-2.0-flash

  # Evaluate with verbose output
  python main.py --course do_113955620332421120130 --verbose
        """
    )

    parser.add_argument(
        "--data-dir",
        type=str,
        default="./data/data_point",
        help="Path to data_point directory (default: ./data/data_point)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="./outputs/5/assessment_quality_score",
        help="Path to output directory (default: ./outputs/5/assessment_quality_score)"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available courses"
    )

    parser.add_argument(
        "--course",
        type=str,
        help="Course ID to evaluate (e.g., do_113955620332421120130)"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Evaluate all courses"
    )

    parser.add_argument(
        "--multi-model",
        action="store_true",
        help="Evaluate using all models defined in GEMINI_MODEL_NAME env variable"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Specific Gemini model to use (overrides GEMINI_MODEL_NAME from .env)"
    )

    parser.add_argument(
        "--force-restart",
        action="store_true",
        help="Ignore checkpoints and restart evaluation from beginning"
    )

    args = parser.parse_args()

    # Handle list command
    if args.list:
        list_courses(args.data_dir)
        return

    # Validate we have something to do
    if not args.course and not args.all:
        parser.print_help()
        print("\nError: Please specify --course, --all, or --list")
        sys.exit(1)

    # Validate configuration
    try:
        validate_config()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Run evaluation
    if args.multi_model:
        # Use all models from .env
        evaluate_with_multiple_models(
            args.data_dir,
            args.output_dir,
            course_id=args.course if args.course else None,
            verbose=args.verbose,
            force_restart=args.force_restart
        )
    elif args.course:
        # Single course with optional specific model
        model = args.model if args.model else get_models_from_env()[0]
        model_output_dir = Path(args.output_dir) / model if not args.model else args.output_dir
        evaluate_single_course(
            args.data_dir,
            args.course,
            str(model_output_dir) if args.multi_model or not args.model else args.output_dir,
            args.verbose,
            model,
            args.force_restart
        )
    elif args.all:
        # All courses with optional specific model
        model = args.model if args.model else get_models_from_env()[0]
        evaluate_all_courses(
            args.data_dir,
            args.output_dir,
            args.verbose,
            model,
            args.force_restart
        )


if __name__ == "__main__":
    main()
