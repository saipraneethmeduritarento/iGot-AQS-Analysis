#!/usr/bin/env python3
"""
Generate a self-contained HTML report for Assessment Quality Score (AQS) data.
This script reads all JSON files from output folders and creates a beautiful,
portable HTML report with embedded data displayed as rich UI elements.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def collect_json_data(base_dir):
    """Collect all JSON data organized by model and do_id."""
    data_structure = defaultdict(lambda: defaultdict(dict))
    
    # Search in the new outputs/5/assessment_quality_score folder
    output_path = base_dir / 'outputs' / '5' / 'assessment_quality_score'
    
    if not output_path.exists():
        print(f"Warning: Directory not found: {output_path}")
        return data_structure
        
    # Find all JSON files
    for json_file in output_path.rglob('*.json'):
        parts = json_file.relative_to(output_path).parts
        
        # Expected structure: model_name/do_id/file.json
        if len(parts) >= 3:
            model_name = parts[0]
            do_id = parts[1]
            file_name = parts[2]
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    
                # Store the data
                if do_id not in data_structure[model_name]:
                    data_structure[model_name][do_id] = {}
                
                data_structure[model_name][do_id][file_name] = json_data
                
            except Exception as e:
                print(f"Error reading {json_file}: {e}")
    
    return data_structure


def generate_html_report(data_structure, output_file):
    """Generate a beautiful, self-contained HTML report using an external template."""
    
    # Convert data to JSON string for embedding
    # Use ensure_ascii=False to handle special characters properly
    embedded_data = json.dumps(dict(data_structure), indent=2, ensure_ascii=False)
    
    # Resolve template path relative to this script
    script_dir = Path(__file__).resolve().parent
    # Assuming script is in 'scripts/' and template is in 'template/' sibling directory
    template_path = script_dir.parent / 'template' / 'aqs_report_template.html'
    
    if not template_path.exists():
        print(f"Error: Template file not found at {template_path}")
        return

    try:
        template_content = template_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading template file: {e}")
        return
    
    # Inject data into the template
    # The template should contain {{AQS_DATA}} placeholder
    if '{{AQS_DATA}}' not in template_content:
        print("Warning: {{AQS_DATA}} placeholder not found in template. Data will not be injected.")
    
    html_content = template_content.replace('{{AQS_DATA}}', embedded_data)
    
    # Write the HTML file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML report generated successfully: {output_file}")
    except Exception as e:
        print(f"Error writing output file: {e}")


def main():
    """Main function to generate the report."""
    base_dir = Path(__file__).parent.parent
    
    print("Collecting JSON data from output folders...")
    data_structure = collect_json_data(base_dir)
    
    # Count total files
    total_files = sum(
        len(files) 
        for model_data in data_structure.values() 
        for files in model_data.values()
    )
    
    print(f"Found {len(data_structure)} models")
    print(f"Total JSON files: {total_files}")
    
    output_file = base_dir / 'scripts' / 'aqs_report.html'
    print(f"\nGenerating HTML report...")
    generate_html_report(data_structure, output_file)
    
    print(f"\nReport saved to: {output_file}")
    print("\nYou can now open this file in any web browser!")
    print("The report is fully self-contained and portable.")


if __name__ == '__main__':
    main()
