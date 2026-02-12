"""
Checkpoint Manager for AQS Evaluation System

Handles checkpoint creation, loading, and management to allow
resuming evaluations from where they stopped.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


class CheckpointManager:
    """Manages checkpoints for AQS evaluation progress."""
    
    def __init__(self, checkpoint_dir: str = "./outputs/5/assessment_quality_score/.checkpoints"):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_checkpoint_path(self, model_name: str, course_id: str) -> Path:
        """Get the checkpoint file path for a model-course combination."""
        safe_model = model_name.replace("/", "_").replace(":", "_")
        safe_course = course_id.replace("/", "_")
        return self.checkpoint_dir / f"{safe_model}_{safe_course}_checkpoint.json"
    
    def load_checkpoint(self, model_name: str, course_id: str) -> Optional[Dict]:
        """
        Load checkpoint for a model-course combination.
        
        Args:
            model_name: Name of the model
            course_id: Course identifier
            
        Returns:
            Checkpoint data dictionary or None if no checkpoint exists
        """
        checkpoint_path = self._get_checkpoint_path(model_name, course_id)
        
        if not checkpoint_path.exists():
            return None
        
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            # Validate checkpoint
            if checkpoint.get('model_name') != model_name or checkpoint.get('course_id') != course_id:
                print(f"⚠️  Warning: Checkpoint mismatch, ignoring checkpoint")
                return None
            
            return checkpoint
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Warning: Failed to load checkpoint: {e}")
            return None
    
    def save_checkpoint(
        self,
        model_name: str,
        course_id: str,
        course_name: str,
        total_assessments: int,
        completed_assessments: List[str]
    ) -> None:
        """
        Save checkpoint for a model-course combination.
        
        Args:
            model_name: Name of the model
            course_id: Course identifier
            course_name: Human-readable course name
            total_assessments: Total number of assessments in course
            completed_assessments: List of completed assessment names
        """
        checkpoint_path = self._get_checkpoint_path(model_name, course_id)
        
        checkpoint_data = {
            "model_name": model_name,
            "course_id": course_id,
            "course_name": course_name,
            "total_assessments": total_assessments,
            "completed_assessments": completed_assessments,
            "completed_count": len(completed_assessments),
            "last_updated": datetime.now().isoformat(),
            "status": "completed" if len(completed_assessments) >= total_assessments else "in_progress"
        }
        
        try:
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2)
        except IOError as e:
            print(f"⚠️  Warning: Failed to save checkpoint: {e}")
    
    def clear_checkpoint(self, model_name: str, course_id: str) -> None:
        """
        Clear/delete checkpoint for a model-course combination.
        
        Args:
            model_name: Name of the model
            course_id: Course identifier
        """
        checkpoint_path = self._get_checkpoint_path(model_name, course_id)
        
        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
            except IOError as e:
                print(f"⚠️  Warning: Failed to delete checkpoint: {e}")
    
    def is_assessment_completed(self, assessment_name: str, checkpoint: Optional[Dict]) -> bool:
        """
        Check if an assessment is already completed in the checkpoint.
        
        Args:
            assessment_name: Name of the assessment
            checkpoint: Checkpoint data dictionary
            
        Returns:
            True if assessment is completed, False otherwise
        """
        if not checkpoint:
            return False
        
        completed = checkpoint.get('completed_assessments', [])
        return assessment_name in completed
    
    def get_completed_assessments(self, checkpoint: Optional[Dict]) -> List[str]:
        """
        Get list of completed assessments from checkpoint.
        
        Args:
            checkpoint: Checkpoint data dictionary
            
        Returns:
            List of completed assessment names
        """
        if not checkpoint:
            return []
        
        return checkpoint.get('completed_assessments', [])
    
    def list_all_checkpoints(self) -> List[Dict]:
        """
        List all existing checkpoints.
        
        Returns:
            List of checkpoint data dictionaries
        """
        checkpoints = []
        
        for checkpoint_file in self.checkpoint_dir.glob("*_checkpoint.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                    checkpoints.append(checkpoint)
            except (json.JSONDecodeError, IOError):
                continue
        
        return checkpoints
