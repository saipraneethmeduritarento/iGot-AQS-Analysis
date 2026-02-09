# Assessment Quality Score Project

## Overview

This project provides an end‑to‑end AI‑powered pipeline that automates the extraction and organization of course content from the Karmayogi Bharat (iGOT) platform and evaluates assessment quality using an AI‑driven Assessment Quality Score (AQS) framework. It processes course materials (transcripts, PDFs, metadata) and assessment data to classify question difficulty, map cognitive levels using Bloom’s taxonomy, assess content alignment, and generate transparent explanations. The system outputs a composite AQS score to ensure consistent, objective, and scalable assessment quality across all iGOT courses.

## Project Structure

```
Assessment_quality_score/
├── .checkpoints/                      # Checkpoint data for resume functionality
├── .env                               # Environment configuration
├── data/
│   ├── data_point/                    # Processed course data for AQS
│   ├── data_with_assessment/          # Raw extracted course data
│   └── data_by_modules/               # Reorganized data by course modules
├── outputs/
│   └── 4/
│       └── assessment_quality_score/  # AQS evaluation results
│           ├── gemini-2.0-flash/  # Model-specific results
│           ├── gemini-2.5-flash/
│           └── gemini-3-flash-preview/
├── scripts/
│   ├── assessment_quality_score/      # AQS evaluation engine
│   │   ├── aqs_evaluator.py          # Core evaluator
│   │   ├── checkpoint_manager.py     # Resume functionality
│   │   ├── data_loader.py            # Data loading utilities
│   │   └── config.py                 # Configuration management
│   ├── c_and_q_extractor/            # Course and Question extraction scripts
│   │   ├── extract_course_content.py # Main extraction script
│   │   ├── reorganize_by_modules.py  # Module reorganization script
│   │   └── extraction_guide.sh       # Quick reference guide
│   └── generate_aqs_report.py        # HTML report generator
├── prompts/
│   └── aqs_system_prompts.yaml       # LLM prompts for evaluation
├── explainations/
│   └── design_document.md            # System design documentation
├── main.py                           # Main entry point for AQS
├── courses_with_assessnemt.txt       # List of course IDs to extract
├── EXTRACTION_SCRIPT_README.md       # Detailed extraction documentation
├── AUTOMATION_SUMMARY.md             # Technical summary
├── QUICKSTART.sh                     # Quick start guide
└── README.md                         # This file
```

## Quick Start

### 1. Prerequisites

- Python 3.7+
- Required packages: `requests`, `beautifulsoup4`

```bash
# Install dependencies
pip install requests beautifulsoup4
```

### 2. Prepare Course IDs

Create or update `courses_with_assessnemt.txt` with course IDs (one per line):

```
do_1136238739591168001278
do_1143470901356625921827
do_1142748906596843521455
```

### 3. Extract Course Content

```bash
python3 scripts/c_and_q_extractor/extract_course_content.py
```

This will:

- Extract course metadata, PDFs, videos, and subtitles
- Extract all assessments with questions, options, and answers
- Save data to `data/data_with_assessment/`

### 4. Reorganize by Modules (Optional)

```bash
python3 scripts/c_and_q_extractor/reorganize_by_modules.py
```

This will reorganize the extracted data into a module-based structure in `data/data_by_modules/`.

## AQS (Assessment Quality Score) Analyzer

The AQS system evaluates educational assessments and generates quality scores based on:

- **Difficulty Analysis** - Classifies assessments as Basic, Intermediate, or Advanced
- **Bloom's Taxonomy** - Evaluates cognitive depth across all six levels
- **Course Fit** - Measures alignment with course content and objectives
- **Final AQS Score** - Combined metric (0-100) for overall quality

### Quick Start

```bash
# Set your API key
export GOOGLE_API_KEY="your-gemini-api-key"

# List available courses

python main.py --list

# Evaluate a specific course

python main.py --course do_113955620332421120130

# Evaluate all courses

python main.py --all

# Evaluate with multiple models (defined in .env)

python main.py --course do_113955620332421120130 --multi-model

# Evaluate with a specific model

python main.py --course do_113955620332421120130 --model gemini-2.5-flash

# Force restart (ignore checkpoints)

python main.py --course do_113955620332421120130 --force-restart

# Verbose output

python main.py --course do_113955620332421120130 --verbose

```

### Output Format

Each assessment evaluation produces multiple output files:

#### 1. Individual Assessment Files

**JSON Format** (`<assessment_name>_aqs.json`):

```json
{
  "assessment_name": "Final Assessment",
  "assessment_type": "Final Assessment",
  "difficulty_level": "Intermediate",
  "difficulty_rationale": "Explanation of difficulty classification...",
  "difficulty_scores": {
    "complexity_score": 7,
    "language_difficulty_score": 5,
    "cognitive_effort_score": 6,
    "course_alignment_score": 8
  },
  "blooms_scores": {
    "remember": 20,
    "understand": 35,
    "apply": 25,
    "analyze": 15,
    "evaluate": 5,
    "create": 0
  },
  "blooms_distribution_summary": "The assessment primarily targets...",
  "question_classifications": [
    {
      "question_number": 1,
      "blooms_level": "Understand",
      "justification": "Requires comprehension..."
    }
  ],
  "course_fit_score": 85,
  "course_fit_status": "Well-Aligned",
  "course_fit_details": {
    "content_coverage_score": 88,
    "objective_alignment_score": 85,
    "difficulty_appropriateness_score": 82,
    "completeness_score": 90,
    "alignment_details": "Analysis of alignment...",
    "improvement_suggestions": ["Suggestion 1...", "Suggestion 2..."]
  },
  "aqs_score": 78.5,
  "quality_tier": "Good",
  "confidence_flags": [],
  "warnings": [],
  "metrics": {
    "duration_seconds": 45.2,
    "token_usage": {
      "input_tokens": 15420,
      "output_tokens": 2847,
      "thinking_tokens": 1235,
      "total_tokens": 19502
    },
    "llm_calls": {
      "total": 3,
      "successful": 3,
      "failed": 0
    },
    "cost": {
      "pricing_model": "gemini-2.0-flash",
      "input_cost_usd": 0.001542,
      "output_cost_usd": 0.002847,
      "total_cost_usd": 0.004389
    }
  }
}
```

**Text Format** (`<assessment_name>_aqs.txt`):
Human-readable report with formatted sections for scores, analysis, and recommendations.

#### 2. Combined Results

**all_assessments_aqs.json**: Contains all assessments for a course with aggregated metrics
**all_assessments_aqs.txt**: Combined text report for all assessments

#### 3. Evaluation Log

**evaluation_log.json**: Detailed metrics for the entire course evaluation including:

- Course-level statistics
- Per-assessment metrics
- Total token usage and costs
- Timestamp information

### System Prompts

LLM prompts are configured in `prompts/aqs_system_prompts.yaml`:

- `difficulty_analysis` - Prompts for difficulty classification
- `blooms_taxonomy` - Prompts for cognitive level evaluation
- `course_fit_analysis` - Prompts for alignment assessment
- `edge_case_handlers` - Configuration for warnings and alerts

### AQS Calculation

The final AQS score is computed as:

```
AQS = (Difficulty × 0.25) + (Bloom's × 0.35) + (Course Fit × 0.40)
```

For standalone assessments (no course content):

```
AQS = (Difficulty × 0.40) + (Bloom's × 0.60)
```

### Quality Tiers

| Tier              | Score Range | Description                                    |
| ----------------- | ----------- | ---------------------------------------------- |
| Excellent         | 85-100      | Exceptional alignment and cognitive depth      |
| Good              | 70-84       | Meets standards with minor improvements needed |
| Satisfactory      | 55-69       | Acceptable but notable areas need attention    |
| Needs Improvement | 40-54       | Significant revisions required                 |
| Poor              | 0-39        | Fails minimum quality thresholds               |

### Edge Cases

The system handles:

- **Missing transcripts/PDFs** - Proceeds with reduced accuracy warning
- **Few questions (<5)** - Flags low confidence
- **Standalone assessments** - Course-fit marked "Not Applicable"
- **Difficulty mismatch** - Generates misalignment alert

### Enable Gemini (Vertex AI) (optional)

Set env vars (ADC required):

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="your-gcp-project"
export GOOGLE_CLOUD_LOCATION="global"
export GEMINI_MODEL="your-gemini-model"
export GEMINI_EMBED_MODEL="your-embed-model"   # optional
```

Then run:

```bash
python3 scripts/assessment_quailty_score/run.py --gemini
```

### Flags

- `--course-ids do_... do_...` analyze a subset
- `--final-only` / `--practice-only`
- `--top-k 5` evidence chunks per question
- `--align-threshold 0.12`
- `--force` recompute even if inputs unchanged

## Features

### AQS System Features

✅ **Multi-Model Support** - Compare results across different Gemini models
✅ **Checkpoint/Resume** - Automatically resume interrupted evaluations
✅ **Cost Tracking** - Detailed token usage and cost analysis
✅ **HTML Reports** - Interactive, beautiful reports with charts
✅ **Comprehensive Metrics** - LLM calls, duration, token usage
✅ **Vertex AI Integration** - Uses Google Cloud Vertex AI for inference

### Course Content Extraction

✅ **Batch Processing** - Extract multiple courses automatically
✅ **Metadata** - Course name, description, keywords, competencies, ratings
✅ **Resources** - PDFs, videos with English subtitles
✅ **Assessments** - Questions, options, correct answers, explanations
✅ **Clean Data** - HTML tags removed from all text content
✅ **Complete Questions** - Full question text (not truncated)

### Module Organization

✅ **Final Assessments** - Separated into dedicated folders
✅ **Practice Quizzes** - Organized by quiz number
✅ **Module Content** - Structured by course hierarchy
✅ **Sessions & Modules** - Categorized appropriately

## Output Structure

### Raw Extraction (`data/data_with_assessment/`)

```
data/data_with_assessment/
├── do_1136238739591168001278/
│   ├── metadata.json                    # Course metadata
│   ├── english_subtitles.vtt            # Combined subtitles
│   ├── Assessment_1/                    # Assessment folder
│   │   ├── assessment.json              # Raw assessment data
│   │   ├── assessment_parsed.json       # Structured data
│   │   └── assessment_questions.txt     # Human-readable format
│   └── do_113684545312235520140/        # Module/Lesson folder
│       ├── metadata.json
│       └── Assessment_1/
└── ...
```

### Module-Based Organization (`data/data_by_modules/`)

```
data/data_by_modules/
├── do_1136238739591168001278/
│   ├── metadata.json
│   ├── Final_Assessment/                # Final course assessment
│   │   ├── assessment.json
│   │   ├── assessment_parsed.json
│   │   └── assessment_questions.txt
│   ├── Practice_Quizzes/                # Practice assessments
│   │   ├── Quiz_1/
│   │   └── Quiz_2/
│   ├── Modules/                         # Course modules
│   │   └── Module_01_Introduction/
│   ├── Sessions/                        # Course sessions
│   │   └── Session_01_Overview/
│   └── Content/                         # Other content
└── ...
```

## Assessment Data Format

Each assessment contains three files:

### `assessment.json`

Raw assessment data from the API

### `assessment_parsed.json`

Structured JSON format:

```json
{
  "assessmentName": "Final Assessment",
  "assessmentId": "do_11374486952921497618",
  "totalQuestions": 10,
  "questions": [
    {
      "questionNumber": 1,
      "questionText": "What is PM GatiShakti?",
      "questionType": "Multiple Choice Question",
      "options": ["Option A", "Option B", "Option C"],
      "correctAnswers": ["Option A"],
      "explanation": "Detailed explanation..."
    }
  ]
}
```

### `assessment_questions.txt`

Human-readable text format with questions, options, correct answers, and explanations

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
GOOGLE_PROJECT_ID=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1 # global for gemini 3 flash preview

# Optional
GEMINI_MODEL_NAME=gemini-2.0-flash
# For multiple models:
# GEMINI_MODEL_NAME=["gemini-2.0-flash", "gemini-2.5-flash", "gemini-3-flash-preview"]
```

### Google Cloud Authentication

The system uses Application Default Credentials (ADC):

```bash
# Login to Google Cloud
gcloud auth application-default login

# Or use service account credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
```

## Documentation

- **[EXTRACTION_SCRIPT_README.md](EXTRACTION_SCRIPT_README.md)** - Complete extraction guide
- **[AUTOMATION_SUMMARY.md](AUTOMATION_SUMMARY.md)** - Technical implementation details
- **[QUICKSTART.sh](QUICKSTART.sh)** - Interactive quick start script
- **[design_document.md](explainations/design_document.md)** - System design and architecture

## Usage Examples

### View Extracted Assessments

```bash
# View human-readable assessment
cat data/data_with_assessment/do_1136238739591168001278/Assessment_1/assessment_questions.txt

# View structured JSON
cat data/data_with_assessment/do_1136238739591168001278/Assessment_1/assessment_parsed.json

# View course metadata
cat data/data_with_assessment/do_1136238739591168001278/metadata.json
```

### Get Statistics

```bash
# Count extracted courses
ls -d data/data_with_assessment/do_* | wc -l

# Count total assessments
find data/data_with_assessment -name "assessment_questions.txt" | wc -l

# View extraction logs
# (Displayed during script execution)
```

## Script Details

### `extract_course_content.py`

Main extraction script with:

- API integration for course hierarchy and content
- Recursive content discovery
- Assessment parsing (multiple JSON formats)
- HTML tag removal (BeautifulSoup4)
- Full question text extraction
- Comprehensive error handling

### `reorganize_by_modules.py`

Reorganization script that:

- Parses course hierarchy
- Separates final vs practice assessments
- Organizes content by modules and sessions
- Preserves all data files

## API Endpoints

The scripts use the following Karmayogi Bharat APIs:

- **Hierarchy API**: `/api/private/content/v3/hierarchy/{courseId}`
- **Read API**: `/api/content/v1/read/{contentId}`
- **QuestionSet API**: `/api/questionset/v1/read/{questionsetId}`
- **Question API**: `/api/question/v1/read/{questionId}`
- **Transcoder API**: `/api/kb-pipeline/v3/transcoder/stats`

## Logging

All scripts provide detailed logging:

- Course processing progress
- File creation/download status
- Assessment extraction results
- Error messages and warnings
- Summary statistics
