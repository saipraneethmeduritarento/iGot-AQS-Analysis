import os
import json
import requests
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = "https://portal.igotkarmayogi.gov.in/api"
HIERARCHY_ENDPOINT = f"{API_BASE_URL}/private/content/v3/hierarchy"
READ_ENDPOINT = f"{API_BASE_URL}/content/v1/read"
QUESTIONSET_READ_ENDPOINT = f"{API_BASE_URL}/questionset/v1/read"
QUESTION_READ_ENDPOINT = f"{API_BASE_URL}/question/v1/read"
TRANSCODER_API = "https://learning-ai.prod.karmayogibharat.net/api/kb-pipeline/v3/transcoder/stats"

# API Headers
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI5a04xTW1TcGVuVTAyam8zVHg1U2p0amhTOFVXeGVSUiJ9.LWAgFust4e0wntxqY8_MQjf5WQ9RSD6Hg45jX_NoCXY',
    'org': 'dopt',
    'rootorg': 'igot',
    'locale': 'en',
    'hostpath': 'portal.uat.karmayogibharat.net',
    'Content-Type': 'application/json'
}

OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "data_with_assessment"


class CourseContentExtractor:
    """Extract course content including PDFs, videos, subtitles, and assessments"""

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()

    @staticmethod
    def strip_html(text: str) -> str:
        """Remove HTML tags from text and clean up whitespace"""
        if not text or not isinstance(text, str):
            return text
        
        # Parse HTML and extract text
        soup = BeautifulSoup(text, 'html.parser')
        clean_text = soup.get_text(separator=' ', strip=True)
        
        # Clean up extra whitespace
        clean_text = ' '.join(clean_text.split())
        
        return clean_text

    def read_course_ids(self, file_path: Path, section: str = "courses_with_assessment") -> List[str]:
        """Read course IDs from text file by section.
        
        Args:
            file_path: Path to the file containing course IDs
            section: Section to extract ('courses_with_assessment' or 'standalone_assessment')
        
        Returns:
            List of course IDs from the specified section
        """
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            course_ids = []
            current_section = None
            
            logger.debug(f"Looking for section: '{section}'")
            
            for line in lines:
                line = line.strip()
                
                # Check for section headers
                if line.startswith('#'):
                    current_section = line[1:]  # Remove '#'
                    logger.debug(f"Found section header: '{current_section}'")
                    continue
                
                # Add IDs from the matching section
                if current_section == section and line:
                    course_ids.append(line)
                    logger.debug(f"Added course ID: {line}")
            
            logger.info(f"Loaded {len(course_ids)} course IDs from section '{section}' in {file_path}")
            return course_ids
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return []

    def fetch_hierarchy(self, course_id: str) -> Optional[Dict]:
        """Fetch course hierarchy"""
        try:
            url = f"{HIERARCHY_ENDPOINT}/{course_id}"
            response = self.session.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('responseCode') == 'OK':
                return data.get('result', {}).get('content')
            logger.warning(f"Hierarchy fetch failed for {course_id}: {data.get('params', {}).get('errmsg')}")
            return None
        except Exception as e:
            logger.error(f"Error fetching hierarchy for {course_id}: {e}")
            return None

    def fetch_read(self, content_id: str) -> Optional[Dict]:
        """Fetch content details via read endpoint"""
        try:
            url = f"{READ_ENDPOINT}/{content_id}"
            response = self.session.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('responseCode') == 'OK':
                return data.get('result', {}).get('content')
            return None
        except Exception as e:
            logger.error(f"Error fetching read for {content_id}: {e}")
            return None

    def find_pdf_resources(self, node: Dict, found_pdfs: List[Dict] = None) -> List[Dict]:
        """Recursively find all PDF resources"""
        if found_pdfs is None:
            found_pdfs = []
        
        if not node or not isinstance(node, dict):
            return found_pdfs
        
        if node.get('mimeType') == 'application/pdf' and node.get('artifactUrl'):
            found_pdfs.append({
                'name': node.get('name', 'Unnamed PDF'),
                'url': node.get('artifactUrl'),
                'identifier': node.get('identifier')
            })
        
        if 'children' in node and isinstance(node['children'], list):
            for child in node['children']:
                self.find_pdf_resources(child, found_pdfs)
        
        return found_pdfs

    def find_video_mp4_children(self, node: Dict, found_videos: List[Dict] = None) -> List[Dict]:
        """Recursively find all video resources"""
        if found_videos is None:
            found_videos = []
        
        if not node or not isinstance(node, dict):
            return found_videos
        
        if node.get('mimeType') == 'video/mp4':
            found_videos.append(node)
        
        if 'children' in node and isinstance(node['children'], list):
            for child in node['children']:
                self.find_video_mp4_children(child, found_videos)
        
        return found_videos

    def find_assessment_nodes(self, node: Dict, found_assessments: List[Dict] = None) -> List[Dict]:
        """Recursively find all assessment nodes"""
        if found_assessments is None:
            found_assessments = []
        
        if not node or not isinstance(node, dict):
            return found_assessments
        
        primary_category = (node.get('primaryCategory') or '').lower()
        mime_type = (node.get('mimeType') or '').lower()
        object_type = (node.get('objectType') or '').lower()
        name = (node.get('name') or '').lower()

        is_assessment = False

        if mime_type == 'application/json' and 'assessment' in name:
            is_assessment = True

        if mime_type == 'application/vnd.sunbird.questionset':
            is_assessment = True

        if object_type == 'questionset':
            is_assessment = True

        if 'assessment' in primary_category or primary_category in {
            'course assessment',
            'final assessment',
            'practice assessment',
            'practice question set',
            'question set'
        }:
            is_assessment = True

        if is_assessment:
            found_assessments.append(node)
        
        if 'children' in node and isinstance(node['children'], list):
            for child in node['children']:
                self.find_assessment_nodes(child, found_assessments)
        
        return found_assessments

    def find_vtt_urls(self, obj: Any, found: List[str] = None) -> List[str]:
        """Recursively find all VTT subtitle URLs"""
        if found is None:
            found = []
        
        if isinstance(obj, str) and obj.endswith('.vtt'):
            found.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                self.find_vtt_urls(item, found)
        elif isinstance(obj, dict):
            for value in obj.values():
                self.find_vtt_urls(value, found)
        
        return found

    def extract_metadata(self, node: Dict) -> Dict:
        """Extract key metadata from content node"""
        competencies_list = []
        if 'competencies_v6' in node:
            competencies_list = [
                c.get('competencyAreaName', '') 
                for c in node.get('competencies_v6', [])
            ]
        
        return {
            'identifier': node.get('identifier', ''),
            'name': node.get('name', 'N/A'),
            'description': node.get('description', ''),
            'keywords': node.get('keywords', []),
            'organisation': node.get('organisation', [None])[0] if node.get('organisation') else 'N/A',
            'competencies': competencies_list,
            'primaryCategory': node.get('primaryCategory', ''),
            'contentType': node.get('contentType', ''),
            'creator': node.get('creator', ''),
            'createdOn': node.get('createdOn', ''),
            'lastUpdatedOn': node.get('lastUpdatedOn', ''),
            'status': node.get('status', ''),
            'avgRating': node.get('avgRating', 0),
            'totalRatings': node.get('totalNoOfRating', 0)
        }

    def download_file(self, url: str, file_path: Path) -> bool:
        """Download file from URL"""
        try:
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Downloaded: {file_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False

    def fetch_subtitles(self, video_id: str) -> Dict[str, str]:
        """Fetch English subtitles for a video"""
        subtitles = {}
        try:
            url = f"{TRANSCODER_API}?resource_id={video_id}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            stats_data = response.json()
            vtt_urls = self.find_vtt_urls(stats_data)
            
            for vtt_url in vtt_urls:
                lang_match = vtt_url.lower().find('/en/')
                if lang_match == -1:
                    continue
                
                try:
                    vtt_resp = self.session.get(vtt_url, timeout=30)
                    if vtt_resp.ok:
                        subtitles[vtt_url.split('/')[-1]] = vtt_resp.text
                except Exception as e:
                    logger.warning(f"Failed to fetch subtitle {vtt_url}: {e}")
        except Exception as e:
            logger.warning(f"Failed to fetch transcoder stats for {video_id}: {e}")
        
        return subtitles

    def extract_assessment_content(self, assessment_node: Dict) -> Optional[Dict]:
        """Extract assessment questions and answers"""
        try:
            questions = []
            assessment_data = None

            mime_type = (assessment_node.get('mimeType') or '').lower()
            object_type = (assessment_node.get('objectType') or '').lower()

            # Case 1: JSON assessment with artifactUrl
            artifact_url = assessment_node.get('artifactUrl')
            if artifact_url and mime_type == 'application/json':
                response = self.session.get(artifact_url, timeout=30)
                response.raise_for_status()
                assessment_data = response.json()

                # Handle different assessment JSON formats
                assessment_list = None
                if isinstance(assessment_data, dict):
                    if 'assessment' in assessment_data and isinstance(assessment_data['assessment'], list):
                        assessment_list = assessment_data['assessment']
                    elif 'questions' in assessment_data and isinstance(assessment_data['questions'], list):
                        assessment_list = assessment_data['questions']
                elif isinstance(assessment_data, list):
                    assessment_list = assessment_data

                if assessment_list:
                    for idx, q in enumerate(assessment_list, 1):
                        options = []
                        if 'options' in q:
                            options = [opt if isinstance(opt, str) else opt.get('text', opt.get('label', str(opt)))
                                      for opt in q['options']]
                        elif 'choices' in q:
                            options = [opt if isinstance(opt, str) else opt.get('text', opt.get('label', str(opt)))
                                      for opt in q['choices']]

                        # Extract and clean question text and options
                        question_text = q.get('question', q.get('text', 'N/A'))
                        question_text = self.strip_html(question_text)
                        options = [self.strip_html(opt) for opt in options]
                        explanation = q.get('explanation', '')
                        explanation = self.strip_html(explanation) if explanation else ''

                        questions.append({
                            'questionNumber': idx,
                            'questionText': question_text,
                            'questionType': q.get('type', 'N/A'),
                            'options': options,
                            'correctAnswers': q.get('correctAnswers', q.get('answer', q.get('correct', []))),
                            'explanation': explanation
                        })

            # Case 2: QuestionSet assessment (Sunbird)
            if not questions and (mime_type == 'application/vnd.sunbird.questionset' or object_type == 'questionset'):
                questionset_id = assessment_node.get('identifier')
                if questionset_id:
                    qs_url = f"{QUESTIONSET_READ_ENDPOINT}/{questionset_id}"
                    qs_resp = self.session.get(qs_url, headers=HEADERS, timeout=30)
                    if qs_resp.ok:
                        qs_data = qs_resp.json()
                        assessment_data = qs_data
                        result = qs_data.get('result', {})
                        
                        # Get questions list from different possible locations
                        questions_list = result.get('questions', [])
                        
                        # If questions list is empty, try fetching from questionset childNodes
                        if not questions_list:
                            questionset = result.get('questionset', {})
                            child_nodes = questionset.get('childNodes', [])
                            
                            # Fetch each child question with full fields
                            for qid in child_nodes:
                                try:
                                    # Request additional fields to get full question text and answers
                                    params = {'fields': 'body,question,name,editorState,responseDeclaration,answer,hints,solutions,explanation,primaryCategory,questionType,bloomsLevel,difficultyLevel,marks,choices'}
                                    q_resp = self.session.get(f"{QUESTION_READ_ENDPOINT}/{qid}", params=params, headers=HEADERS, timeout=30)
                                    if q_resp.ok:
                                        q_result = q_resp.json().get('result', {})
                                        q_data = q_result.get('question')
                                        if q_data:
                                            questions_list.append(q_data)
                                        else:
                                            logger.warning(f"No question data found for {qid}")
                                    else:
                                        logger.warning(f"Failed to fetch question {qid}: {q_resp.status_code}")
                                except Exception as e:
                                    logger.warning(f"Error fetching question {qid}: {e}")

                        # Parse extracted questions
                        for idx, q in enumerate(questions_list, 1):
                            options = []
                            
                            # Extract options from various formats
                            # Format 1: editorState.options (when fetched with fields parameter)
                            if 'editorState' in q and isinstance(q.get('editorState'), dict):
                                editor_options = q['editorState'].get('options', [])
                                for opt in editor_options:
                                    if isinstance(opt, dict):
                                        opt_val = opt.get('value', {})
                                        if isinstance(opt_val, dict):
                                            opt_text = opt_val.get('body') or opt_val.get('text') or str(opt_val.get('value', ''))
                                        else:
                                            opt_text = str(opt_val)
                                        options.append(opt_text.strip())
                            
                            # Format 2: choices.options array (Sunbird QuestionSet format)
                            if not options and 'choices' in q and isinstance(q.get('choices'), dict):
                                choices_options = q['choices'].get('options', [])
                                for opt in choices_options:
                                    if isinstance(opt, dict):
                                        # Structure: {"value": {"body": "text", "value": 0}}
                                        opt_val = opt.get('value', {})
                                        if isinstance(opt_val, dict):
                                            opt_text = opt_val.get('body') or opt_val.get('text') or str(opt_val.get('value', ''))
                                        else:
                                            opt_text = str(opt_val)
                                        options.append(opt_text.strip())
                            # Format 3: options array (direct list)
                            elif not options and 'options' in q and isinstance(q['options'], list):
                                for opt in q['options']:
                                    if isinstance(opt, str):
                                        options.append(opt)
                                    elif isinstance(opt, dict):
                                        # Try different fields for option text
                                        opt_text = (opt.get('value', {}).get('body') if isinstance(opt.get('value'), dict) else opt.get('value')) or \
                                                   opt.get('body') or \
                                                   opt.get('text') or \
                                                   opt.get('label') or \
                                                   str(opt)
                                        options.append(opt_text)
                            # Format 4: choices as array (not dict)
                            elif not options and 'choices' in q and isinstance(q['choices'], list):
                                for opt in q['choices']:
                                    if isinstance(opt, str):
                                        options.append(opt)
                                    elif isinstance(opt, dict):
                                        opt_text = (opt.get('value', {}).get('body') if isinstance(opt.get('value'), dict) else opt.get('value')) or \
                                                   opt.get('body') or \
                                                   opt.get('text') or \
                                                   opt.get('label') or \
                                                   str(opt)
                                        options.append(opt_text)
                            
                            # Extract question text from various fields
                            question_text = q.get('body') or \
                                          q.get('name') or \
                                          q.get('question') or \
                                          q.get('text') or \
                                          q.get('title') or \
                                          'N/A'
                            
                            # Strip HTML tags from question text
                            question_text = self.strip_html(question_text)
                            
                            # Strip HTML from all options
                            options = [self.strip_html(opt) for opt in options]
                            
                            # Extract correct answers from various sources
                            correct_ans = []
                            
                            # Method 1: Direct answer field (single value or array)
                            if 'answer' in q:
                                ans = q['answer']
                                if isinstance(ans, list):
                                    correct_ans = ans
                                else:
                                    correct_ans = [ans]
                            
                            # Method 2: editorState with answer flags
                            elif 'editorState' in q and isinstance(q['editorState'], dict):
                                editor_options = q['editorState'].get('options', [])
                                for idx, opt in enumerate(editor_options):
                                    if isinstance(opt, dict) and opt.get('answer') is True:
                                        correct_ans.append(idx)
                            
                            # Method 3: Other formats
                            elif 'correctAnswers' in q:
                                correct_ans = q.get('correctAnswers', [])
                            elif 'correct' in q:
                                correct_ans = q.get('correct', [])
                            elif 'responseDeclaration' in q:
                                correct_ans = q.get('responseDeclaration', {}).get('response1', {}).get('correctResponse', {}).get('value', [])
                            
                            # Ensure correct_ans is always a list
                            if not isinstance(correct_ans, list):
                                correct_ans = [correct_ans] if correct_ans else []
                            
                            # Get explanation and strip HTML
                            explanation = q.get('explanation') or q.get('solution') or q.get('hints') or ''
                            explanation = self.strip_html(explanation) if explanation else ''
                            
                            questions.append({
                                'questionNumber': idx,
                                'questionText': question_text,
                                'questionType': q.get('questionType') or q.get('type') or q.get('primaryCategory') or 'N/A',
                                'options': options,
                                'correctAnswers': correct_ans,
                                'explanation': explanation,
                                'bloomsLevel': q.get('bloomsLevel', ''),
                                'difficultyLevel': q.get('difficultyLevel', ''),
                                'marks': q.get('marks', 0)
                            })

            if not questions and assessment_data is None:
                return None

            return {
                'assessmentName': assessment_node.get('name', 'Assessment'),
                'assessmentId': assessment_node.get('identifier', ''),
                'totalQuestions': len(questions),
                'questions': questions,
                'rawData': assessment_data
            }
        except Exception as e:
            logger.error(f"Failed to extract assessment: {e}")
            return None

    def format_assessment_as_text(self, assessment_data: Dict) -> str:
        """Format assessment data as readable text"""
        text = f"# Assessment: {assessment_data['assessmentName']}\n"
        text += f"ID: {assessment_data['assessmentId']}\n"
        text += f"Total Questions: {assessment_data['totalQuestions']}\n\n"
        text += f"{'=' * 80}\n\n"
        
        for q in assessment_data['questions']:
            text += f"Question {q['questionNumber']}: {q['questionText']}\n"
            text += f"Type: {q['questionType']}\n\n"
            text += "Options:\n"
            for i, opt in enumerate(q['options']):
                text += f"  {chr(65 + i)}) {opt}\n"
            
            correct_ans = q['correctAnswers']
            if isinstance(correct_ans, list):
                correct_ans = ', '.join(map(str, correct_ans))
            text += f"\nCorrect Answer(s): {correct_ans}\n"
            
            if q['explanation']:
                text += f"Explanation: {q['explanation']}\n"
            
            text += f"\n{'-' * 80}\n\n"
        
        return text

    def process_course(self, course_id: str) -> bool:
        """Process a single course"""
        logger.info(f"Processing course: {course_id}")
        
        # Fetch hierarchy
        course_data = self.fetch_hierarchy(course_id)
        if not course_data:
            logger.error(f"Failed to fetch hierarchy for {course_id}")
            return False
        
        # Create course folder
        course_folder = self.output_dir / course_data.get('identifier', course_id)
        course_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created folder: {course_folder}")
        
        # Save metadata
        metadata = self.extract_metadata(course_data)
        with open(course_folder / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info("Saved metadata.json")
        
        # Extract and download PDFs
        pdfs = self.find_pdf_resources(course_data)
        pdf_links = []
        for pdf in pdfs:
            try:
                pdf_file = course_folder / f"{pdf['name']}.pdf"
                if self.download_file(pdf['url'], pdf_file):
                    pdf_links.append(f"{pdf['name']} - {pdf['url']}")
                else:
                    pdf_links.append(f"{pdf['name']} - [FAILED] {pdf['url']}")
            except Exception as e:
                logger.error(f"Failed to process PDF {pdf['name']}: {e}")
                pdf_links.append(f"{pdf['name']} - [ERROR] {pdf['url']}")
        
        if pdf_links:
            with open(course_folder / 'pdf_links.txt', 'w') as f:
                f.write('\n'.join(pdf_links))
            logger.info(f"Saved {len(pdfs)} PDF links")
        
        # Extract videos and subtitles
        videos = self.find_video_mp4_children(course_data)
        course_english_vtt = []
        for video in videos:
            video_id = video.get('identifier') or video.get('id')
            video_folder = course_folder / (video.get('name') or video_id)
            video_folder.mkdir(parents=True, exist_ok=True)
            
            # Fetch subtitles
            subtitles = self.fetch_subtitles(video_id)
            for subtitle_name, subtitle_content in subtitles.items():
                lang_folder = video_folder / 'en'
                lang_folder.mkdir(parents=True, exist_ok=True)
                with open(lang_folder / subtitle_name, 'w') as f:
                    f.write(subtitle_content)
                course_english_vtt.append(f"\n\nNOTE: From video \"{video.get('name') or video_id}\" - {subtitle_name}\n\n{subtitle_content.strip()}\n")
            
            logger.info(f"Processed video: {video.get('name')}")
        
        if course_english_vtt:
            with open(course_folder / 'english_subtitles.vtt', 'w') as f:
                f.write('\n'.join(course_english_vtt))
            logger.info("Saved English subtitles")
        
        # Extract assessments
        assessments = self.find_assessment_nodes(course_data)
        for idx, assessment in enumerate(assessments, 1):
            try:
                assessment_data = self.extract_assessment_content(assessment)
                if assessment_data:
                    # Check if this is a final assessment
                    assessment_name = assessment_data['assessmentName'].lower()
                    if 'final' in assessment_name or 'course assessment' in assessment_name:
                        assessment_folder = course_folder / 'Final_Assessment'
                    else:
                        assessment_folder = course_folder / f'Quiz_{idx}'
                    assessment_folder.mkdir(parents=True, exist_ok=True)
                    
                    # Save raw data
                    with open(assessment_folder / 'assessment.json', 'w') as f:
                        json.dump(assessment_data['rawData'], f, indent=2)
                    
                    # Save parsed data
                    with open(assessment_folder / 'assessment_parsed.json', 'w') as f:
                        parsed = {k: v for k, v in assessment_data.items() if k != 'rawData'}
                        json.dump(parsed, f, indent=2)
                    
                    # Save readable format
                    with open(assessment_folder / 'assessment_questions.txt', 'w') as f:
                        f.write(self.format_assessment_as_text(assessment_data))
                    
                    logger.info(f"Extracted assessment {idx}: {assessment_data['totalQuestions']} questions")
            except Exception as e:
                logger.error(f"Failed to process assessment {idx}: {e}")
        
        # Process leaf nodes
        leaf_nodes = course_data.get('leafNodes', [])
        for leaf_id in leaf_nodes:
            try:
                leaf_data = self.fetch_read(leaf_id)
                if leaf_data:
                    leaf_folder = course_folder / (leaf_data.get('identifier') or leaf_id)
                    leaf_folder.mkdir(parents=True, exist_ok=True)
                    
                    # Save metadata
                    with open(leaf_folder / 'metadata.json', 'w') as f:
                        json.dump(self.extract_metadata(leaf_data), f, indent=2)
                    
                    # Extract PDFs from leaf
                    leaf_pdfs = self.find_pdf_resources(leaf_data)
                    for pdf in leaf_pdfs:
                        try:
                            pdf_file = leaf_folder / f"{pdf['name']}.pdf"
                            self.download_file(pdf['url'], pdf_file)
                        except Exception as e:
                            logger.warning(f"Failed to download leaf PDF: {e}")
                    
                    # Extract videos and subtitles from leaf
                    leaf_videos = self.find_video_mp4_children(leaf_data)
                    for video in leaf_videos:
                        video_id = video.get('identifier') or video.get('id')
                        video_folder = leaf_folder / (video.get('name') or video_id)
                        video_folder.mkdir(parents=True, exist_ok=True)
                        
                        subtitles = self.fetch_subtitles(video_id)
                        for subtitle_name, subtitle_content in subtitles.items():
                            lang_folder = video_folder / 'en'
                            lang_folder.mkdir(parents=True, exist_ok=True)
                            with open(lang_folder / subtitle_name, 'w') as f:
                                f.write(subtitle_content)
                    
                    # Extract assessments from leaf
                    leaf_assessments = self.find_assessment_nodes(leaf_data)
                    for idx, assessment in enumerate(leaf_assessments, 1):
                        try:
                            assessment_data = self.extract_assessment_content(assessment)
                            if assessment_data:
                                # Check if this is a final assessment
                                assessment_name = assessment_data['assessmentName'].lower()
                                if 'final' in assessment_name or 'course assessment' in assessment_name:
                                    assessment_folder = leaf_folder / 'Final_Assessment'
                                else:
                                    assessment_folder = leaf_folder / f'Quiz_{idx}'
                                assessment_folder.mkdir(parents=True, exist_ok=True)
                                
                                with open(assessment_folder / 'assessment.json', 'w') as f:
                                    json.dump(assessment_data['rawData'], f, indent=2)
                                
                                with open(assessment_folder / 'assessment_parsed.json', 'w') as f:
                                    parsed = {k: v for k, v in assessment_data.items() if k != 'rawData'}
                                    json.dump(parsed, f, indent=2)
                                
                                with open(assessment_folder / 'assessment_questions.txt', 'w') as f:
                                    f.write(self.format_assessment_as_text(assessment_data))
                                
                                logger.info(f"Extracted leaf assessment: {assessment_data['totalQuestions']} questions")
                        except Exception as e:
                            logger.error(f"Failed to process leaf assessment: {e}")
                    
                    logger.info(f"Processed leaf node: {leaf_data.get('name')}")
            except Exception as e:
                logger.error(f"Failed to process leaf node {leaf_id}: {e}")
        
        logger.info(f"✓ Successfully processed course: {course_id}\n")
        return True

    def process_all_courses(self, course_ids: List[str]) -> Dict[str, bool]:
        """Process all courses"""
        results = {}
        
        logger.info(f"Starting extraction of {len(course_ids)} courses")
        logger.info(f"Output directory: {self.output_dir}\n")
        
        for course_id in course_ids:
            try:
                results[course_id] = self.process_course(course_id)
            except KeyboardInterrupt:
                logger.warning("Extraction interrupted by user")
                sys.exit(1)
            except Exception as e:
                logger.error(f"Unexpected error processing {course_id}: {e}")
                results[course_id] = False
        
        return results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract course content from course IDs')
    parser.add_argument(
        '--section',
        type=str,
        default='courses_with_assessment',
        choices=['courses_with_assessment', 'standalone_assessment'],
        help='Section of courses to extract (default: courses_with_assessment)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Extract both courses_with_assessment and standalone_assessment'
    )
    args = parser.parse_args()
    
    # Read course IDs
    course_file = Path(__file__).parent.parent.parent / "courses_with_assessnemt.txt"
    
    if not course_file.exists():
        logger.error(f"Course file not found: {course_file}")
        sys.exit(1)
    
    # Initialize extractor
    extractor = CourseContentExtractor()
    all_results = {}
    
    if args.all:
        # Process both sections
        sections = ['courses_with_assessment', 'standalone_assessment']
    else:
        sections = [args.section]
    
    for section in sections:
        logger.info(f"\n{'='*80}")
        logger.info(f"Extracting {section}")
        logger.info(f"{'='*80}\n")
        
        course_ids = extractor.read_course_ids(course_file, section=section)
        
        if not course_ids:
            logger.warning(f"No course IDs found in section '{section}'")
            continue
        
        # Process courses
        results = extractor.process_all_courses(course_ids)
        all_results.update(results)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTION SUMMARY")
    logger.info("=" * 80)
    
    successful = sum(1 for v in all_results.values() if v)
    failed = len(all_results) - successful
    
    logger.info(f"Total courses: {len(all_results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Output directory: {extractor.output_dir}")
    logger.info("=" * 80)
    
    if failed > 0:
        logger.warning("\nFailed courses:")
        for course_id, success in all_results.items():
            if not success:
                logger.warning(f"  - {course_id}")
    
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
