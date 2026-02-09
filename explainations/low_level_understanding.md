# Low-Level Code Understanding

This document provides a technical deep-dive into the codebase implementation details.

## 1. `scripts/assessment_quality_score/aqs_evaluator.py`

This is the backend logic module.

### Core Classes

- **`TokenMetrics`**: Tracks input/output/thinking tokens and costs.
  - Method `add()`: Allows aggregation of metrics across multiple calls.
  - Method `calculate_cost()`: Applies pricing based on the specific model used (e.g., `gemini-3-flash-preview` vs `gemini-2.0-flash`).

- **`AQSResult` (Dataclass)**: The central data structure holding the entire evaluation state.
  - Fields: `difficulty_scores`, `blooms_scores`, `course_fit_details`, `metrics`.
  - Method `to_dict()`: Serializes the object for JSON output.

- **`AQSEvaluator`**: The main controller.
  - `__init__`: Initializes Vertex AI connection and `PromptManager`.
  - `evaluate_assessment`: Orchestrates the flow:
    1.  Checks edge cases (few questions, no questions).
    2.  Formats data using `AssessmentDataLoader`.
    3.  Calls `_analyze_combined` (The main LLM call).
    4.  Parses the JSON response from the LLM.
    5.  Calculates the final score via `_compute_final_aqs`.

### Cost Calculation (`_compute_final_aqs`)

The final score is a weighted sum:

```python
aqs = (Difficulty_Component * 0.25) +
      (Blooms_Component * 0.35) +
      (Course_Fit_Score * 0.40)
```

- **Quality Tiers**:
  - Excellent: ≥ 85
  - Good: ≥ 70
  - Satisfactory: ≥ 55
  - Needs Improvement: ≥ 40
  - Poor: < 40

### Vertex AI Integration (`_call_llm`)

- **Library**: `vertexai.generative_models`.
- **Configuration**:
  - **Supported Models**:
    - `gemini-3-flash-preview`
    - `gemini-2.0-flash`
    - `gemini-2.5-flash`
  - `temperature=0.1`: Low randomness for consistent, deterministic scoring.
- **Parsing**: Includes regex-based JSON extraction (`_extract_json`) to handle potential markdown formatting in LLM responses.

## 2. Data Structures

### Input (Implicit)

- **Course Data**: Content summary, learning objectives, competencies.
- **Assessment Data**: List of questions, options, correct answers.

### Output (`outputs/.../*.json`)

- `all_assessments_aqs.json`: Contains the full `AQSResult` structure.
- `evaluation_log.json`: Tracks timing and costs for the run.
