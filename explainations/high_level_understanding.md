# High-Level Understanding of Assessment Quality Score (AQS) System

## Overview

The **Assessment Quality Score (AQS)** system is an automated framework designed to evaluate the quality of educational assessments using advanced AI models (Google Gemini). It analyzes assessments based on pedagogical standards.

The core component is:

- **The Evaluator (`aqs_evaluator.py`)**: The engine that processes assessments, interacts with AI models, and calculates scores.

## Key Components

### 1. The Evaluator (Core Logic)

The evaluator is responsible for the actual "thinking" and analysis. It takes course content and assessment questions as input and produces detailed metrics.

- **Input**: Course metadata, learning objectives, content summaries, and assessment questions.
- **Process**: It constructs complex prompts for the Gemini AI model to analyze the assessment from multiple dimensions simultaneously.
- **Output**: JSON files containing detailed scores, rationale, and metadata, saved in the `outputs/` directory.

## Evaluation Metrics (The "AQS")

The system calculates a final **Assessment Quality Score (AQS)** based on three primary dimensions:

1.  **Difficulty Analysis (25%)**:
    - Evaluates complexity, language difficulty, cognitive effort, and course alignment.
    - Ensures the assessment is appropriate for the target audience.

2.  **Bloom's Taxonomy (35%)**:
    - Classifies questions into cognitive levels: Remember, Understand, Apply, Analyze, Evaluate, Create.
    - Ensures a balanced distribution of cognitive challenge.

3.  **Course Fit Analysis (40%)**:
    - Checks content coverage, objective alignment, and completeness.
    - Ensures the assessment actually tests what was taught.

_Note: For standalone assessments without course context, simple weights are used (40% Difficulty, 60% Bloom's)._

## Data Flow Summary

1.  **Data Loading**: Course and assessment data is loaded from source files.
2.  **AI Evaluation**: `aqs_evaluator.py` sends this data to Gemini.
3.  **JSON Storage**: Results are saved as JSON files in `outputs/4/assessment_quality_score/` for downstream use.
