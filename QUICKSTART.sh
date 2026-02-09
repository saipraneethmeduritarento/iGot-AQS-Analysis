#!/bin/bash
# Quick Start Guide for Course Content Extraction

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║        COURSE CONTENT EXTRACTION - QUICK START GUIDE                  ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

echo "📋 STEP 1: Check Input File"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f "courses_with_assessnemt.txt" ]; then
    echo "✓ File found: courses_with_assessnemt.txt"
    echo "  Contents:"
    head -10 courses_with_assessnemt.txt | sed 's/^/    /'
    COURSE_COUNT=$(wc -l < courses_with_assessnemt.txt)
    echo "  Total courses: $COURSE_COUNT"
else
    echo "✗ File not found: courses_with_assessnemt.txt"
    exit 1
fi
echo ""

echo "🐍 STEP 2: Run Extraction Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: python3 scripts/c_and_q_extractor/extract_course_content.py"
echo ""
echo "This will:"
echo "  • Read all course IDs from the text file"
echo "  • Fetch course hierarchy from API"
echo "  • Extract metadata, PDFs, videos, subtitles"
echo "  • Extract all assessments (questions, options, answers)"
echo "  • Save data to data/data_with_assessment/ folder"
echo ""

echo "📁 STEP 3: Check Output Structure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "After extraction, you'll have:"
echo ""
echo "data/data_with_assessment/"
echo "├── do_1136238739591168001278/        ← Course 1"
echo "│   ├── metadata.json                  ← Course metadata"
echo "│   ├── Assessment_1/                  ← Root assessment"
echo "│   │   ├── assessment.json"
echo "│   │   ├── assessment_parsed.json"
echo "│   │   └── assessment_questions.txt   ← Readable format"
echo "│   ├── do_113684545312235520140/      ← Module/Lesson"
echo "│   │   ├── metadata.json"
echo "│   │   ├── Assessment_1/              ← Module assessment"
echo "│   │   └── [other content]"
echo "│   └── [more modules]"
echo "├── do_1143470901356625921827/        ← Course 2"
echo "└── [more courses...]"
echo ""

echo "📊 STEP 4: View Extracted Assessment Data"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "View assessment questions (readable):"
echo "  $ cat data/data_with_assessment/do_1136238739591168001278/Assessment_1/assessment_questions.txt"
echo ""
echo "View structured assessment JSON:"
echo "  $ cat data/data_with_assessment/do_1136238739591168001278/Assessment_1/assessment_parsed.json"
echo ""
echo "View course metadata:"
echo "  $ cat data/data_with_assessment/do_1136238739591168001278/metadata.json"
echo ""

echo "📈 STEP 5: Get Statistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "data/data_with_assessment" ]; then
    COURSES=$(ls -d data/data_with_assessment/do_* 2>/dev/null | wc -l)
    ASSESSMENTS=$(find data/data_with_assessment -type f -name "assessment_questions.txt" 2>/dev/null | wc -l)
    METADATA=$(find data/data_with_assessment -type f -name "metadata.json" 2>/dev/null | wc -l)
    SIZE=$(du -sh data/data_with_assessment/ | cut -f1)
    
    echo "✓ Extraction Statistics:"
    echo "  • Courses extracted: $COURSES"
    echo "  • Assessment files: $ASSESSMENTS"
    echo "  • Metadata files: $METADATA"
    echo "  • Total size: $SIZE"
else
    echo "⚠ data/data_with_assessment folder not found (run script first)"
fi
echo ""

echo "📚 DOCUMENTATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Detailed Documentation:"
echo "  • EXTRACTION_SCRIPT_README.md - Complete guide"
echo "  • AUTOMATION_SUMMARY.md - Technical summary"
echo ""

echo "🚀 QUICK COMMANDS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Run extraction"
echo "python3 scripts/c_and_q_extractor/extract_course_content.py"
echo ""
echo "# List all courses"
echo "ls -d data/data_with_assessment/do_*"
echo ""
echo "# Count assessments"
echo "find data/data_with_assessment -type f -name 'assessment_questions.txt' | wc -l"
echo ""
echo "# View first assessment"
echo "find data/data_with_assessment -name 'assessment_questions.txt' -type f | head -1 | xargs cat | head -50"
echo ""
echo "# Get extraction stats"
echo "find data/data_with_assessment -type f | wc -l"
echo ""

echo "✨ READY TO START!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
