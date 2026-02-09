# Assessment Quality Score Project

## Overview

This project automates the extraction and analysis of course content and assessments from the Karmayogi Bharat learning platform. It provides tools to extract course materials, organize them by modules, and prepare assessment data for quality analysis.

## Project Structure

```
Assessment_quality_score/
├── data/
│   ├── data_with_assessment/          # Raw extracted course data
│   └── data_by_modules/               # Reorganized data by course modules
├── scripts/
│   └── c_and_q_extractor/             # Course and Question extraction scripts
│       ├── extract_course_content.py   # Main extraction script
│       ├── reorganize_by_modules.py    # Module reorganization script
│       └── extraction_guide.sh         # Quick reference guide
├── courses_with_assessnemt.txt        # List of course IDs to extract
├── EXTRACTION_SCRIPT_README.md        # Detailed extraction documentation
├── AUTOMATION_SUMMARY.md              # Technical summary
├── QUICKSTART.sh                      # Quick start guide
└── README.md                          # This file
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

# Verbose output
python main.py --course do_113955620332421120130 --verbose
```

### Output Format

Each assessment evaluation produces a JSON file with this structure:

```json
{
  "assessment_name": "Final Assessment",
  "assessment_type": "Final Assessment",
  "difficulty_level": "Intermediate",
  "difficulty_rationale": "Explanation of difficulty classification...",
  "blooms_scores": {
    "remember": 20,
    "understand": 35,
    "apply": 25,
    "analyze": 15,
    "evaluate": 5,
    "create": 0
  },
  "blooms_distribution_summary": "The assessment primarily targets...",
  "course_fit_score": 85,
  "course_fit_status": "Well-Aligned",
  "aqs_score": 78.5,
  "confidence_flags": [],
  "warnings": []
}
```

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

| Tier | Score Range | Description |
|------|-------------|-------------|
| Excellent | 85-100 | Exceptional alignment and cognitive depth |
| Good | 70-84 | Meets standards with minor improvements needed |
| Satisfactory | 55-69 | Acceptable but notable areas need attention |
| Needs Improvement | 40-54 | Significant revisions required |
| Poor | 0-39 | Fails minimum quality thresholds |

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

## Documentation

- **[EXTRACTION_SCRIPT_README.md](EXTRACTION_SCRIPT_README.md)** - Complete extraction guide
- **[AUTOMATION_SUMMARY.md](AUTOMATION_SUMMARY.md)** - Technical implementation details
- **[QUICKSTART.sh](QUICKSTART.sh)** - Interactive quick start script

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

## License

[Add your license here]

## Contact

[Add your contact information here]
