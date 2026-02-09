"""
Data Loader Module for Assessment Quality Score System

Handles loading and parsing of:
- Course metadata
- Assessment data
- Course content (transcripts, VTT files, PDFs)
"""

import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# PDF parsing
try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


@dataclass
class Question:
    """Represents a single assessment question."""
    question_number: int
    question_text: str
    question_type: str
    options: list[str] = field(default_factory=list)
    correct_answers: list[str] = field(default_factory=list)
    explanation: str = ""
    blooms_level: str = ""
    difficulty_level: str = ""
    marks: int = 0


@dataclass
class ModuleContent:
    """Represents content for a single module."""
    module_name: str
    transcript: str = ""
    pdf_text: str = ""


@dataclass
class Assessment:
    """Represents an assessment with all its questions."""
    name: str
    assessment_id: str
    assessment_type: str
    total_questions: int
    expected_duration: int  # in seconds
    questions: list[Question] = field(default_factory=list)
    description: str = ""
    purpose: str = ""
    # Module-specific fields
    associated_module: str = ""  # Empty for final assessments
    is_final_assessment: bool = False
    module_content: Optional[ModuleContent] = None  # Content for associated module only


@dataclass
class CourseMetadata:
    """Represents course metadata."""
    identifier: str
    name: str
    description: str
    keywords: list[str] = field(default_factory=list)
    organisation: str = ""
    competencies: list[str] = field(default_factory=list)
    primary_category: str = ""
    content_type: str = ""
    creator: str = ""
    status: str = ""
    avg_rating: float = 0.0
    total_ratings: int = 0


@dataclass
class CourseContent:
    """Represents course content including transcripts."""
    transcripts: list[str] = field(default_factory=list)
    pdf_texts: list[str] = field(default_factory=list)
    module_names: list[str] = field(default_factory=list)
    # Per-module content for module-wise assessment comparison
    module_contents: dict[str, ModuleContent] = field(default_factory=dict)


@dataclass
class CourseData:
    """Complete course data including metadata, content, and assessments."""
    metadata: CourseMetadata
    content: CourseContent
    assessments: list[Assessment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class AssessmentDataLoader:
    """Loads and parses assessment and course data from the file system."""

    def __init__(self, data_dir: str):
        """
        Initialize the data loader.

        Args:
            data_dir: Path to the data directory containing course modules
        """
        self.data_dir = Path(data_dir)
        self.warnings: list[str] = []

    def load_course(self, course_id: str) -> Optional[CourseData]:
        """
        Load complete course data for a given course ID.

        Args:
            course_id: The course identifier (e.g., 'do_113955620332421120130')

        Returns:
            CourseData object or None if course not found
        """
        course_path = self.data_dir / course_id

        if not course_path.exists():
            self.warnings.append(f"Course directory not found: {course_id}")
            return None

        # Load metadata
        metadata = self._load_metadata(course_path)
        if not metadata:
            return None

        # Load course content first (needed for module mapping)
        content = self._load_course_content(course_path)

        # Load assessments with module content mapping
        assessments = self._load_assessments(course_path, content)

        return CourseData(
            metadata=metadata,
            content=content,
            assessments=assessments,
            warnings=self.warnings.copy()
        )

    def _load_metadata(self, course_path: Path) -> Optional[CourseMetadata]:
        """Load course metadata from metadata.json."""
        metadata_file = course_path / "metadata.json"

        if not metadata_file.exists():
            self.warnings.append("Missing metadata.json - reduced accuracy")
            return None

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return CourseMetadata(
                identifier=data.get("identifier", ""),
                name=data.get("name", ""),
                description=data.get("description", ""),
                keywords=data.get("keywords", []),
                organisation=data.get("organisation", ""),
                competencies=data.get("competencies", []),
                primary_category=data.get("primaryCategory", ""),
                content_type=data.get("contentType", ""),
                creator=data.get("creator", ""),
                status=data.get("status", ""),
                avg_rating=data.get("avgRating", 0.0),
                total_ratings=data.get("totalRatings", 0)
            )
        except json.JSONDecodeError as e:
            self.warnings.append(f"Error parsing metadata.json: {e}")
            return None

    def _load_course_content(self, course_path: Path) -> CourseContent:
        """Load course content including transcripts and PDFs."""
        transcripts = []
        pdf_texts = []
        module_names = []
        module_contents = {}  # Per-module content storage

        # Load VTT subtitles/transcripts at course level
        for vtt_file in course_path.glob("*.vtt"):
            try:
                transcript = self._parse_vtt_file(vtt_file)
                if transcript:
                    transcripts.append(transcript)
            except Exception as e:
                self.warnings.append(f"Error reading VTT file {vtt_file.name}: {e}")

        # Folders to exclude from module list (assessment folders)
        exclude_folders = {"Content", "Final_Assessment", "Final Assessment", "Practice_Quizzes", "Practice_Quiz", "Practice Quiz", "Assessments"}

        # Load content from Course directory
        course_dir = course_path / "Course"
        if course_dir.exists():
            # Iterate through all directories in Course/
            for item in sorted(course_dir.iterdir()):
                if item.is_dir() and item.name not in exclude_folders:
                    module_name = item.name.replace("_", " ")
                    module_names.append(module_name)
                    
                    # Load module-specific transcript
                    module_transcript = ""
                    module_vtt_files = list(item.glob("**/*.vtt"))
                    for vtt_file in module_vtt_files:
                        try:
                            transcript = self._parse_vtt_file(vtt_file)
                            if transcript:
                                module_transcript += " " + transcript
                                transcripts.append(transcript)
                        except Exception as e:
                            self.warnings.append(f"Error reading VTT file {vtt_file.name}: {e}")
                    
                    # Store module content
                    module_contents[item.name] = ModuleContent(
                        module_name=module_name,
                        transcript=module_transcript.strip()
                    )
            
            # Also load from Content subdirectory if it exists (for backward compatibility)
            content_dir = course_dir / "Content"
            if content_dir.exists():
                for item in sorted(content_dir.iterdir()):
                    # Skip excluded folders and duplicates
                    if item.is_dir() and item.name not in exclude_folders:
                        module_name = item.name.replace("_", " ")
                        if module_name not in module_names:
                            module_names.append(module_name)
                        
                        # Load module-specific transcript
                        module_transcript = ""
                        module_vtt_files = list(item.glob("**/*.vtt"))
                        for vtt_file in module_vtt_files:
                            try:
                                transcript = self._parse_vtt_file(vtt_file)
                                if transcript:
                                    module_transcript += " " + transcript
                                    transcripts.append(transcript)
                            except Exception as e:
                                self.warnings.append(f"Error reading VTT file {vtt_file.name}: {e}")
                        
                        # Store module content
                        if item.name not in module_contents:
                            module_contents[item.name] = ModuleContent(
                                module_name=module_name,
                                transcript=module_transcript.strip()
                            )

        if not transcripts:
            self.warnings.append("No transcripts found - reduced accuracy for content analysis")

        # Parse PDF files for course content
        pdf_files = list(course_path.glob("**/*.pdf"))
        for pdf_file in pdf_files:
            try:
                pdf_text = self._parse_pdf_file(pdf_file)
                if pdf_text:
                    pdf_texts.append(pdf_text)
                    
                    # Try to associate PDF with a module based on directory structure
                    # Check if PDF is inside a module directory
                    relative_path = pdf_file.relative_to(course_path)
                    path_parts = relative_path.parts
                    
                    # Look for module directory in the path
                    for part in path_parts:
                        if part in module_contents:
                            # Append PDF text to module content
                            existing_content = module_contents[part]
                            existing_content.pdf_text = (existing_content.pdf_text + "\n\n" + pdf_text).strip()
                            break
            except Exception as e:
                self.warnings.append(f"Error parsing PDF file {pdf_file.name}: {e}")

        if pdf_texts:
            self.warnings.append(f"Successfully parsed {len(pdf_texts)} PDF files")

        return CourseContent(
            transcripts=transcripts,
            pdf_texts=pdf_texts,
            module_names=module_names,
            module_contents=module_contents
        )

    def _parse_pdf_file(self, pdf_path: Path) -> str:
        """Parse PDF file and extract text content."""
        if not PDF_SUPPORT:
            self.warnings.append(f"PDF parsing not available (pypdf not installed) - skipping {pdf_path.name}")
            return ""
        
        try:
            reader = PdfReader(pdf_path)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text.strip())
                except Exception as e:
                    self.warnings.append(f"Error extracting text from page {page_num + 1} of {pdf_path.name}: {e}")
            
            full_text = "\n\n".join(text_parts)
            
            # Clean up the extracted text
            # Remove excessive whitespace
            import re
            full_text = re.sub(r'\n{3,}', '\n\n', full_text)
            full_text = re.sub(r' {2,}', ' ', full_text)
            
            return full_text.strip()
            
        except Exception as e:
            self.warnings.append(f"Error reading PDF {pdf_path.name}: {e}")
            return ""

    def _parse_vtt_file(self, vtt_path: Path) -> str:
        """Parse VTT file and extract text content."""
        with open(vtt_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        text_lines = []

        for line in lines:
            line = line.strip()
            # Skip empty lines, WEBVTT header, timestamps, and NOTE lines
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
            # Skip music/silence markers
            if line.startswith("[") and line.endswith("]"):
                continue

            text_lines.append(line)

        return " ".join(text_lines)

    def _load_assessments(self, course_path: Path, course_content: Optional[CourseContent] = None) -> list[Assessment]:
        """Load all assessments from the course directory."""
        assessments = []
        
        # Folders to exclude from module list
        exclude_folders = {"Content", "Final_Assessment", "Final Assessment", "Practice_Quizzes", "Practice_Quiz", "Practice Quiz", "Assessments"}
        
        # Get module names for mapping quizzes to modules
        course_dir = course_path / "Course"
        module_dirs = []
        if course_dir.exists():
            module_dirs = sorted([
                d.name for d in course_dir.iterdir() 
                if d.is_dir() and d.name not in exclude_folders
            ])
            
            # Also include modules from Content subdirectory if it exists
            content_dir = course_dir / "Content"
            if content_dir.exists():
                for d in sorted(content_dir.iterdir()):
                    if d.is_dir() and d.name not in module_dirs:
                        module_dirs.append(d.name)

        # Load assessments from the Assessments directory
        assessments_dir = course_path / "Assessments"
        if not assessments_dir.exists():
            self.warnings.append("No Assessments directory found")
            return assessments

        # Load Final Assessment
        final_assessment_path = assessments_dir / "Final_Assessment"
        if final_assessment_path.exists():
            assessment = self._load_assessment_from_dir(
                final_assessment_path, "Final Assessment"
            )
            if assessment:
                assessment.is_final_assessment = True
                assessment.associated_module = ""  # Final assessment covers all modules
                assessments.append(assessment)

        # Load Practice Quizzes (module-wise assessments)
        practice_path = assessments_dir / "Practice_Quizzes"
        if practice_path.exists():
            quiz_dirs = sorted([d for d in practice_path.iterdir() if d.is_dir() and d.name.startswith("Quiz")])
            
            for i, quiz_dir in enumerate(quiz_dirs):
                assessment = self._load_assessment_from_dir(
                    quiz_dir, f"Practice Assessment - {quiz_dir.name}"
                )
                if assessment:
                    assessment.is_final_assessment = False
                    
                    # Map quiz to corresponding module (Quiz_1 -> Module 1, etc.)
                    if i < len(module_dirs):
                        module_dir_name = module_dirs[i]
                        assessment.associated_module = module_dir_name
                        
                        # Attach module content if available
                        if course_content and module_dir_name in course_content.module_contents:
                            assessment.module_content = course_content.module_contents[module_dir_name]
                    
                    assessments.append(assessment)

        if not assessments:
            self.warnings.append("No assessments found in course directory")

        return assessments

    def _load_assessment_from_dir(
        self, assessment_path: Path, assessment_type: str
    ) -> Optional[Assessment]:
        """Load a single assessment from a directory."""
        parsed_file = assessment_path / "assessment_parsed.json"
        raw_file = assessment_path / "assessment.json"

        # Prefer parsed file if available
        if parsed_file.exists():
            return self._parse_assessment_parsed(parsed_file, assessment_type)
        elif raw_file.exists():
            return self._parse_assessment_raw(raw_file, assessment_type)
        else:
            self.warnings.append(f"No assessment files found in {assessment_path.name}")
            return None

    def _parse_assessment_parsed(
        self, file_path: Path, assessment_type: str
    ) -> Optional[Assessment]:
        """Parse the pre-parsed assessment JSON format."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            questions = []
            for q_data in data.get("questions", []):
                question = Question(
                    question_number=q_data.get("questionNumber", 0),
                    question_text=q_data.get("questionText", ""),
                    question_type=q_data.get("questionType", ""),
                    options=q_data.get("options", []),
                    correct_answers=q_data.get("correctAnswers", []),
                    explanation=q_data.get("explanation", ""),
                    blooms_level=q_data.get("bloomsLevel", ""),
                    difficulty_level=q_data.get("difficultyLevel", ""),
                    marks=q_data.get("marks", 0)
                )
                questions.append(question)

            return Assessment(
                name=data.get("assessmentName", ""),
                assessment_id=data.get("assessmentId", ""),
                assessment_type=assessment_type,
                total_questions=data.get("totalQuestions", len(questions)),
                expected_duration=0,  # Will be updated from raw file if available
                questions=questions
            )
        except Exception as e:
            self.warnings.append(f"Error parsing {file_path.name}: {e}")
            return None

    def _parse_assessment_raw(
        self, file_path: Path, assessment_type: str
    ) -> Optional[Assessment]:
        """Parse the raw assessment JSON format from API response."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            result = data.get("result", {}).get("questionset", {})

            return Assessment(
                name=result.get("name", ""),
                assessment_id=result.get("identifier", ""),
                assessment_type=assessment_type,
                total_questions=result.get("totalQuestions", 0),
                expected_duration=result.get("expectedDuration", 0),
                questions=[],  # Questions not available in raw format
                description=result.get("description", ""),
                purpose=result.get("purpose", "")
            )
        except Exception as e:
            self.warnings.append(f"Error parsing {file_path.name}: {e}")
            return None

    def get_available_courses(self) -> list[str]:
        """Get list of available course IDs."""
        if not self.data_dir.exists():
            return []

        return [
            d.name for d in self.data_dir.iterdir()
            if d.is_dir() and d.name.startswith("do_")
        ]

    def format_questions_for_prompt(self, assessment: Assessment) -> str:
        """Format assessment questions for LLM prompt."""
        lines = []
        for q in assessment.questions:
            lines.append(f"\nQuestion {q.question_number}: {q.question_text}")
            lines.append(f"Type: {q.question_type}")
            if q.options:
                lines.append("Options:")
                for i, opt in enumerate(q.options):
                    lines.append(f"  {chr(65 + i)}) {opt}")
        return "\n".join(lines)

    def format_course_content_summary(self, content: CourseContent) -> str:
        """Format course content for LLM prompt."""
        summary_parts = []

        if content.module_names:
            summary_parts.append("Course Modules:")
            for name in content.module_names:
                summary_parts.append(f"  - {name}")

        if content.transcripts:
            # Truncate transcripts for prompt
            combined = " ".join(content.transcripts)
            if len(combined) > 8000:
                combined = combined[:8000] + "... [truncated]"
            summary_parts.append(f"\nCourse Transcript:\n{combined}")

        if content.pdf_texts:
            # Add PDF content
            combined_pdf = "\n\n".join(content.pdf_texts)
            if len(combined_pdf) > 5000:
                combined_pdf = combined_pdf[:5000] + "... [truncated]"
            summary_parts.append(f"\nPDF Course Materials:\n{combined_pdf}")

        return "\n".join(summary_parts)
