# Course Content Extraction Script

## Overview
`extract_course_content.py` is a Python automation script that extracts comprehensive course content including metadata, PDFs, videos, subtitles, and assessments from the Karmayogi Bharat platform.

## Features

✅ **Batch Processing** - Extracts multiple courses from a text file  
✅ **Metadata Extraction** - Saves course metadata (name, description, keywords, competencies, ratings, etc.)  
✅ **PDF Download** - Automatically downloads all PDF resources  
✅ **Video Processing** - Processes video content with English subtitles  
✅ **Assessment Extraction** - Extracts assessment questions, options, and correct answers  
✅ **Hierarchical Structure** - Maintains course hierarchy (root course → modules → lessons)  
✅ **Error Handling** - Graceful error handling with detailed logging  
✅ **Progress Tracking** - Real-time logging of extraction progress  

## Requirements

- Python 3.7+
- `requests` library
- Course IDs file: `courses_with_assessnemt.txt`

## Installation

```bash
pip install requests
```

## Usage

### Basic Usage
```bash
python3 scripts/c_and_q_extractor/extract_course_content.py
```

### Input File
Create/update `courses_with_assessnemt.txt` with course IDs (one per line):
```
do_1136238739591168001278
do_1143470901356625921827
do_1142748906596843521455
```

### Output Structure
Data is saved in `data/data_with_assessment/` folder:

```
data/data_with_assessment/
├── do_1136238739591168001278/          # Course folder
│   ├── metadata.json                    # Course metadata
│   ├── pdf_links.txt                    # PDF links and status
│   ├── english_subtitles.vtt            # Combined video subtitles
│   ├── Assessment_1/                    # Assessment folder
│   │   ├── assessment.json              # Raw assessment data
│   │   ├── assessment_parsed.json       # Structured assessment data
│   │   └── assessment_questions.txt     # Human-readable questions
│   ├── do_113684545312235520140/        # Module/Lesson folder
│   │   ├── metadata.json                # Module metadata
│   │   ├── Assessment_1/                # Module-level assessment
│   │   └── video_name/                  # Video folder
│   │       └── en/                      # English subtitles
│   │           └── subtitle.vtt
│   └── ...
└── do_1143470901356625921827/
    └── ...
```

## Output Files

### metadata.json
Contains course-level information:
```json
{
  "identifier": "do_1136238739591168001278",
  "name": "PM Gatishakti",
  "description": "Course description...",
  "keywords": ["keyword1", "keyword2"],
  "organisation": "Department for Promotion of Industry and Internal Trade",
  "competencies": ["competency1", "competency2"],
  "avgRating": 4.4,
  "totalRatings": 18063
}
```

### assessment_questions.txt
Human-readable assessment format:
```
# Assessment: Assessment
ID: do_11374486952921497618
Total Questions: 10

================================================================================

Question 1: What is PM GatiShakti?
Type: N/A

Options:
  A) Option A
  B) Option B
  C) Option C
  D) Option D

Correct Answer(s): A, C
Explanation: Detailed explanation here...

--------------------------------------------------------------------------------
```

### assessment_parsed.json
Structured assessment data:
```json
{
  "assessmentName": "Assessment",
  "assessmentId": "do_11374486952921497618",
  "totalQuestions": 10,
  "questions": [
    {
      "questionNumber": 1,
      "questionText": "Question text here",
      "questionType": "MCQ",
      "options": ["Option A", "Option B", "Option C"],
      "correctAnswers": ["Option A"],
      "explanation": "Explanation text"
    }
  ]
}
```

## Logging

The script provides detailed logging:

```
2026-02-04 17:44:23,021 - INFO - Loaded 6 course IDs from courses_with_assessnemt.txt
2026-02-04 17:44:23,021 - INFO - Starting extraction of 6 courses
2026-02-04 17:44:23,021 - INFO - Processing course: do_1136238739591168001278
2026-02-04 17:44:23,246 - INFO - Created folder: .../do_1136238739591168001278
2026-02-04 17:44:23,246 - INFO - Saved metadata.json
2026-02-04 17:44:23,265 - INFO - Extracted assessment 1: 10 questions
2026-02-04 17:44:23,302 - INFO - Processed leaf node: State Engagement
```

## API Endpoints Used

1. **Hierarchy API** - Get complete course structure
   ```
   GET /api/private/content/v3/hierarchy/{courseId}
   ```

2. **Read API** - Get individual content details
   ```
   GET /api/content/v1/read/{contentId}
   ```

3. **Transcoder API** - Get video subtitles
   ```
   GET /api/kb-pipeline/v3/transcoder/stats?resource_id={videoId}
   ```

## Error Handling

- Network errors are caught and logged
- Failed downloads are recorded in `pdf_links.txt`
- Invalid JSON in assessments is handled gracefully
- Script continues on individual course failures
- Final summary shows successful vs failed courses

## Performance

- Extraction speed depends on:
  - Number of courses
  - Number of modules/lessons per course
  - Video processing (if subtitles are fetched)
  - Network connectivity
- Typical extraction: ~5-10 seconds per course

## Troubleshooting

### No data extracted
- Verify course IDs are valid
- Check network connectivity
- Verify API token is valid (update HEADERS if needed)

### Missing assessments
- Some courses may not have assessments
- Check `assessment_questions.txt` files are empty

### Failed PDF downloads
- Check `pdf_links.txt` for failed URLs
- Some PDFs may be temporarily unavailable

## Script Functions

| Function | Purpose |
|----------|---------|
| `read_course_ids()` | Read course IDs from text file |
| `fetch_hierarchy()` | Fetch complete course structure |
| `fetch_read()` | Fetch individual content details |
| `find_pdf_resources()` | Find all PDFs in course |
| `find_video_mp4_children()` | Find all videos in course |
| `find_assessment_nodes()` | Find all assessments in course |
| `extract_assessment_content()` | Parse assessment JSON |
| `format_assessment_as_text()` | Convert assessment to readable format |
| `process_course()` | Process single course end-to-end |
| `process_all_courses()` | Process all courses in batch |

## Notes

- The script respects course hierarchy (root → modules → lessons)
- Assessments are extracted at both root and lesson levels
- English subtitles are combined into single file per course
- All metadata is saved in JSON format for easy parsing
- The script creates output directories automatically
