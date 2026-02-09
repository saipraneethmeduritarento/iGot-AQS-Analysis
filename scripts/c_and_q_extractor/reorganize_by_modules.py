#!/usr/bin/env python3
"""
Reorganize extracted course content by modules based on hierarchy structure.
Organizes assessments and content into module-based folders.
"""

import json
import shutil
from pathlib import Path
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SOURCE_DIR = Path(__file__).parent.parent.parent / "data" / "data_with_assessment"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "data_by_modules"


class ContentReorganizer:
    """Reorganize course content by modules"""
    
    def __init__(self, source_dir: Path = SOURCE_DIR, output_dir: Path = OUTPUT_DIR):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_module_path(self, node: dict, parent_path: str = "") -> str:
        """Build module path from hierarchy"""
        name = node.get('name', '').strip()
        # Clean up name for folder
        safe_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in name)
        safe_name = safe_name.replace(' ', '_')
        
        if parent_path:
            return f"{parent_path}/{safe_name}"
        return safe_name
    
    def is_final_assessment(self, name: str) -> bool:
        """Check if assessment is final"""
        name_lower = name.lower()
        return 'final' in name_lower or 'course assessment' in name_lower
    
    def is_practice_quiz(self, name: str) -> bool:
        """Check if assessment is practice quiz"""
        name_lower = name.lower()
        return 'practice' in name_lower or 'quiz' in name_lower
    
    def get_assessment_id(self, folder: Path) -> tuple:
        """Get assessment ID and name from folder"""
        assessment_json = folder / 'assessment_parsed.json'
        if assessment_json.exists():
            try:
                with open(assessment_json) as f:
                    data = json.load(f)
                    return data.get('assessmentId', ''), data.get('assessmentName', '')
            except:
                pass
        
        # Try assessment.json
        assessment_json = folder / 'assessment.json'
        if assessment_json.exists():
            try:
                with open(assessment_json) as f:
                    data = json.load(f)
                    result = data.get('result', {}).get('questionset', {})
                    return result.get('identifier', ''), result.get('name', '')
            except:
                pass
        
        return '', ''
    
    def copy_assessment_files(self, src_folder: Path, dest_folder: Path):
        """Copy all files from assessment folder to destination"""
        dest_folder.mkdir(parents=True, exist_ok=True)
        for file in src_folder.iterdir():
            if file.is_file():
                shutil.copy2(file, dest_folder / file.name)
    
    def find_node_in_hierarchy(self, hierarchy: dict, identifier: str) -> tuple:
        """Find a node and its parent path in hierarchy"""
        def search(node, parent_path="", parent_name=""):
            node_id = node.get('identifier')
            if node_id == identifier:
                return node, parent_path, parent_name
            
            # Search in children
            children = node.get('children', [])
            for child in children:
                node_name = node.get('name', '')
                child_path = self.get_module_path(node, parent_path)
                result = search(child, child_path, node_name)
                if result[0]:
                    return result
            
            return None, None, None
        
        return search(hierarchy)
    
    def organize_course(self, course_folder: Path):
        """Reorganize a single course by modules"""
        course_id = course_folder.name
        logger.info(f"Reorganizing course: {course_id}")
        
        # Create output course folder
        output_course = self.output_dir / course_id
        output_course.mkdir(parents=True, exist_ok=True)
        
        # Copy metadata
        metadata_file = course_folder / 'metadata.json'
        if metadata_file.exists():
            shutil.copy2(metadata_file, output_course / 'metadata.json')
        
        # Copy course-level subtitles if they exist
        subtitles_file = course_folder / 'english_subtitles.vtt'
        if subtitles_file.exists():
            shutil.copy2(subtitles_file, output_course / 'english_subtitles.vtt')
        
        # Create main folders
        course_content_dir = output_course / 'Course'
        assessments_dir = output_course / 'Assessments'
        course_content_dir.mkdir(parents=True, exist_ok=True)
        assessments_dir.mkdir(parents=True, exist_ok=True)
        
        assessment_count = 0
        module_count = 0
        quiz_counter = 0  # Track actual quiz number for practice quizzes
        
        # Track assessment IDs to avoid duplicates
        copied_assessment_ids = set()
        
        # Track content folder names to avoid duplicates
        copied_content_names = set()
        
        # Sort items to process do_* folders first (they have metadata with proper names)
        # Then process standalone folders which might be duplicates
        items = sorted(course_folder.iterdir(), key=lambda x: (0 if x.name.startswith('do_') else 1, x.name))
        
        for item in items:
            if not item.is_dir():
                continue
            
            item_name = item.name
            
            # Handle Quiz folders (Quiz_1, Quiz_2, etc.)
            if item_name.startswith('Quiz_'):
                # Check if this is a duplicate (same assessment ID already copied)
                assessment_id, assessment_name = self.get_assessment_id(item)
                
                # If it's actually a final assessment, put it there instead
                if assessment_id and self.is_final_assessment(assessment_name):
                    if assessment_id not in copied_assessment_ids:
                        dest_folder = assessments_dir / 'Final_Assessment'
                        self.copy_assessment_files(item, dest_folder)
                        copied_assessment_ids.add(assessment_id)
                        assessment_count += 1
                        logger.info(f"  Moved {item_name} as Final Assessment (was mislabeled as quiz)")
                    else:
                        logger.info(f"  Skipping duplicate: {item_name} (ID: {assessment_id})")
                elif assessment_id and assessment_id in copied_assessment_ids:
                    logger.info(f"  Skipping duplicate quiz: {item_name} (ID: {assessment_id})")
                else:
                    quiz_counter += 1
                    dest_folder = assessments_dir / 'Practice_Quizzes' / f'Quiz_{quiz_counter}'
                    self.copy_assessment_files(item, dest_folder)
                    if assessment_id:
                        copied_assessment_ids.add(assessment_id)
                    assessment_count += 1
                    logger.info(f"  Moved quiz: {item_name} -> Assessments/Practice_Quizzes/Quiz_{quiz_counter}")
            
            # Handle root-level assessments (Assessment_1, Assessment_2, etc.)
            elif item_name.startswith('Assessment_'):
                # Check if it's a final assessment
                assessment_id, assessment_name = self.get_assessment_id(item)
                
                # Skip if duplicate
                if assessment_id and assessment_id in copied_assessment_ids:
                    logger.info(f"  Skipping duplicate assessment: {item_name} (ID: {assessment_id})")
                    continue
                
                if self.is_final_assessment(assessment_name):
                    dest_folder = assessments_dir / 'Final_Assessment'
                elif self.is_practice_quiz(assessment_name):
                    quiz_counter += 1
                    dest_folder = assessments_dir / 'Practice_Quizzes' / f'Quiz_{quiz_counter}'
                else:
                    dest_folder = assessments_dir / 'Other_Assessments' / item_name
                
                self.copy_assessment_files(item, dest_folder)
                if assessment_id:
                    copied_assessment_ids.add(assessment_id)
                assessment_count += 1
                logger.info(f"  Moved assessment: {assessment_name} -> {dest_folder.relative_to(output_course)}")
            
            # Handle root-level Final_Assessment folder
            elif item_name == 'Final_Assessment':
                assessment_id, assessment_name = self.get_assessment_id(item)
                if assessment_id and assessment_id in copied_assessment_ids:
                    logger.info(f"  Skipping duplicate final assessment: {item_name} (ID: {assessment_id})")
                else:
                    dest_folder = assessments_dir / 'Final_Assessment'
                    self.copy_assessment_files(item, dest_folder)
                    if assessment_id:
                        copied_assessment_ids.add(assessment_id)
                    assessment_count += 1
                    logger.info(f"  Moved final assessment -> Assessments/Final_Assessment/")
            
            # Handle leaf nodes (content modules and special folders)
            elif item_name.startswith('do_'):
                # Read metadata to get module name
                module_metadata = item / 'metadata.json'
                if module_metadata.exists():
                    with open(module_metadata) as f:
                        meta = json.load(f)
                        module_name = meta.get('name', item_name)
                        
                        # Create safe folder name
                        safe_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in module_name)
                        safe_name = safe_name.replace(' ', '_')
                        
                        # Determine if this is a module or session
                        primary_category = meta.get('primaryCategory', '').lower()
                        content_type = meta.get('contentType', '').lower()
                        
                        # Check if this is an assessment container, not a content module
                        is_assessment_container = (
                            'assessment' in primary_category or 
                            'selfassess' in content_type or
                            self.is_final_assessment(module_name) or
                            self.is_practice_quiz(module_name)
                        )
                        
                        if is_assessment_container:
                            # This do_ folder is an assessment container, handle its nested assessments
                            for sub_item in item.iterdir():
                                if sub_item.is_dir():
                                    if sub_item.name == 'Final_Assessment' or sub_item.name.startswith('Quiz_'):
                                        nested_id, nested_name = self.get_assessment_id(sub_item)
                                        if nested_id and nested_id in copied_assessment_ids:
                                            logger.info(f"    Skipping duplicate in assessment container: {sub_item.name}")
                                        else:
                                            if self.is_final_assessment(nested_name) or sub_item.name == 'Final_Assessment':
                                                final_dest = assessments_dir / 'Final_Assessment'
                                                self.copy_assessment_files(sub_item, final_dest)
                                            else:
                                                quiz_counter += 1
                                                quiz_dest = assessments_dir / 'Practice_Quizzes' / f'Quiz_{quiz_counter}'
                                                self.copy_assessment_files(sub_item, quiz_dest)
                                            if nested_id:
                                                copied_assessment_ids.add(nested_id)
                                            assessment_count += 1
                            logger.info(f"  Processed assessment container: {module_name[:50]}...")
                            continue
                        
                        module_count += 1
                        
                        # Track this content name to avoid duplicates from standalone folders
                        copied_content_names.add(module_name.strip())
                        
                        if 'session' in module_name.lower() or 'session' in primary_category:
                            dest_folder = course_content_dir / 'Sessions' / safe_name
                        elif 'module' in module_name.lower() or 'module' in primary_category:
                            dest_folder = course_content_dir / 'Modules' / safe_name
                        else:
                            dest_folder = course_content_dir / 'Content' / safe_name
                        
                        dest_folder.mkdir(parents=True, exist_ok=True)
                        
                        # Copy all content
                        for sub_item in item.iterdir():
                            if sub_item.is_file():
                                shutil.copy2(sub_item, dest_folder / sub_item.name)
                            elif sub_item.is_dir():
                                # Handle nested quizzes
                                if sub_item.name.startswith('Quiz_'):
                                    # Check for duplicates
                                    nested_id, nested_name = self.get_assessment_id(sub_item)
                                    
                                    # If it's actually a final assessment
                                    if nested_id and self.is_final_assessment(nested_name):
                                        if nested_id not in copied_assessment_ids:
                                            final_dest = assessments_dir / 'Final_Assessment'
                                            self.copy_assessment_files(sub_item, final_dest)
                                            copied_assessment_ids.add(nested_id)
                                            assessment_count += 1
                                            logger.info(f"    Moved {sub_item.name} as Final Assessment")
                                        else:
                                            logger.info(f"    Skipping duplicate: {sub_item.name}")
                                    elif nested_id and nested_id in copied_assessment_ids:
                                        logger.info(f"    Skipping duplicate quiz: {sub_item.name}")
                                    else:
                                        quiz_counter += 1
                                        quiz_dest = assessments_dir / 'Practice_Quizzes' / f'Quiz_{quiz_counter}'
                                        self.copy_assessment_files(sub_item, quiz_dest)
                                        if nested_id:
                                            copied_assessment_ids.add(nested_id)
                                        assessment_count += 1
                                        logger.info(f"    Added quiz: {sub_item.name} -> Practice_Quizzes/Quiz_{quiz_counter}")
                                # Handle nested final assessments
                                elif sub_item.name == 'Final_Assessment':
                                    nested_id, nested_name = self.get_assessment_id(sub_item)
                                    if nested_id and nested_id in copied_assessment_ids:
                                        logger.info(f"    Skipping duplicate final assessment")
                                    else:
                                        final_dest = assessments_dir / 'Final_Assessment'
                                        self.copy_assessment_files(sub_item, final_dest)
                                        if nested_id:
                                            copied_assessment_ids.add(nested_id)
                                        assessment_count += 1
                                        logger.info(f"    Added final assessment -> Assessments/Final_Assessment/")
                                # Handle nested assessments
                                elif sub_item.name.startswith('Assessment_'):
                                    nested_id, nested_name = self.get_assessment_id(sub_item)
                                    if nested_id and nested_id in copied_assessment_ids:
                                        logger.info(f"    Skipping duplicate assessment: {sub_item.name}")
                                    else:
                                        assessment_dest = assessments_dir / 'Other_Assessments' / safe_name
                                        self.copy_assessment_files(sub_item, assessment_dest)
                                        if nested_id:
                                            copied_assessment_ids.add(nested_id)
                                        assessment_count += 1
                                else:
                                    # Other nested content (videos, etc.)
                                    shutil.copytree(sub_item, dest_folder / sub_item.name, dirs_exist_ok=True)
                        
                        logger.info(f"  Organized module: {module_name[:50]}...")
            
            # Handle standalone module-like folders (not starting with do_)
            # Skip assessment folders - they are handled separately
            elif item_name not in ['metadata.json', 'english_subtitles.vtt', 'Final_Assessment', 'pdf_links.txt'] and not item_name.startswith('Quiz_') and not item_name.startswith('Assessment_'):
                # Check if this content was already copied from a do_ folder (by matching name)
                if item_name.strip() in copied_content_names:
                    logger.info(f"  Skipping duplicate content folder: {item_name}")
                    continue
                
                # These could be content folders (PDFs, videos, etc.)
                dest_folder = course_content_dir / item_name
                dest_folder.mkdir(parents=True, exist_ok=True)
                
                # Copy folder contents, but skip assessment subfolders
                if item.is_dir():
                    for sub_item in item.iterdir():
                        if sub_item.is_file():
                            shutil.copy2(sub_item, dest_folder / sub_item.name)
                        elif sub_item.is_dir():
                            # Skip assessment folders inside content folders
                            if sub_item.name in ['Final_Assessment'] or sub_item.name.startswith('Quiz_') or sub_item.name.startswith('Assessment_'):
                                logger.info(f"    Skipping assessment folder in content: {sub_item.name}")
                                continue
                            shutil.copytree(sub_item, dest_folder / sub_item.name, dirs_exist_ok=True)
                
                logger.info(f"  Organized content folder: {item_name}")
        
        logger.info(f"✓ Reorganized {course_id}: {module_count} modules, {assessment_count} assessments\n")
    
    def reorganize_all(self):
        """Reorganize all courses"""
        if not self.source_dir.exists():
            logger.error(f"Source directory not found: {self.source_dir}")
            return
        
        course_folders = [f for f in self.source_dir.iterdir() if f.is_dir()]
        
        logger.info(f"Found {len(course_folders)} courses to reorganize")
        logger.info(f"Source: {self.source_dir}")
        logger.info(f"Output: {self.output_dir}\n")
        
        for course_folder in course_folders:
            try:
                self.organize_course(course_folder)
            except Exception as e:
                logger.error(f"Failed to reorganize {course_folder.name}: {e}")
        
        logger.info("=" * 80)
        logger.info("REORGANIZATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Output directory: {self.output_dir}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reorganize extracted course content by modules')
    parser.add_argument(
        '--section',
        type=str,
        default='courses_with_assessment',
        choices=['courses_with_assessment', 'standalone_assessment'],
        help='Section of courses to reorganize (default: courses_with_assessment)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Reorganize both courses_with_assessment and standalone_assessment'
    )
    args = parser.parse_args()
    
    if args.all:
        sections = ['courses_with_assessment', 'standalone_assessment']
    else:
        sections = [args.section]
    
    for section in sections:
        logger.info(f"\n{'='*80}")
        logger.info(f"Reorganizing {section}")
        logger.info(f"{'='*80}\n")
        
        # Set source directory based on section
        source_dir = Path(__file__).parent.parent.parent / "data" / "data_with_assessment"
        output_dir = Path(__file__).parent.parent.parent / "data" / "data_by_modules"
        
        # For standalone assessments, we might want different handling
        if section == 'standalone_assessment':
            logger.info("Note: Standalone assessments may have different structure")
        
        reorganizer = ContentReorganizer(source_dir=source_dir, output_dir=output_dir)
        reorganizer.reorganize_all()


if __name__ == "__main__":
    main()
