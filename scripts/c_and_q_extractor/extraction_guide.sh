#!/bin/bash
# Quick extraction guide for course content extraction

# 1. Ensure you have the course IDs file
echo "Step 1: Verify courses_with_assessnemt.txt exists"
if [ -f "courses_with_assessnemt.txt" ]; then
    echo "✓ File found"
    echo "Content:"
    cat courses_with_assessnemt.txt
else
    echo "✗ File not found"
    exit 1
fi

echo ""
echo "Step 2: Run extraction script"
echo "Command: python3 scripts/c_and_q_extractor/extract_course_content.py"
echo ""

echo "Step 3: Check output in data/data_with_assessment/"
echo "Expected structure:"
echo "data/data_with_assessment/"
echo "├── do_1136238739591168001278/"
echo "│   ├── metadata.json"
echo "│   ├── Assessment_1/"
echo "│   │   ├── assessment.json"
echo "│   │   ├── assessment_parsed.json"
echo "│   │   └── assessment_questions.txt"
echo "│   └── [module folders]/"
echo "└── [other courses]/"
echo ""

echo "Step 4: View extraction results"
echo "- Check logs: See INFO messages during extraction"
echo "- View assessments: cat data/data_with_assessment/do_XXXXX/Assessment_1/assessment_questions.txt"
echo "- View metadata: cat data/data_with_assessment/do_XXXXX/metadata.json"
echo ""

echo "📊 QUICK STATS:"
BASE="data/data_with_assessment"
if [ -d "$BASE" ]; then
    COURSES=$(ls -d $BASE/do_* 2>/dev/null | wc -l)
    ASSESSMENTS=$(find $BASE -type f -name "assessment_questions.txt" 2>/dev/null | wc -l)
    METADATA=$(find $BASE -type f -name "metadata.json" 2>/dev/null | wc -l)
    echo "Courses extracted: $COURSES"
    echo "Assessments found: $ASSESSMENTS"
    echo "Metadata files: $METADATA"
fi
