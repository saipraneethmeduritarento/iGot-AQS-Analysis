import json
import os
from pathlib import Path
from collections import defaultdict
import csv

# Model pricing per 1M tokens (USD) - from aqs_evaluator.py
MODEL_PRICING = {
    "gemini-2.0-flash": {
        "input": 0.10,
        "output": 0.40,
    },
    "gemini-2.5-flash": {
        "input": 0.30,
        "output": 2.50,
    },
    "gemini-3-pro-preview": {
        "input": 2.00,
        "output": 12.00,
    },
    "gemini-3-flash-preview": {
        "input": 0.50,
        "output": 3.00,
    },
}

# USD to INR conversion rate (approximate)
USD_TO_INR = 90.59

def extract_cost_data_from_json(json_path):
    """Extract cost and token data from a single JSON file."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Check if this is an all_assessments file or individual assessment
        if 'assessments' in data:
            # This is an all_assessments file
            total_cost = 0
            total_input_tokens = 0
            total_output_tokens = 0
            total_thinking_tokens = 0
            
            for assessment in data.get('assessments', []):
                metrics = assessment.get('metrics', {})
                cost_data = metrics.get('cost', {})
                token_data = metrics.get('token_usage', {})
                
                total_cost += cost_data.get('total_cost_usd', 0)
                
                # Handle nested token_usage (check for 'totals' key)
                if 'totals' in token_data:
                    totals = token_data['totals']
                    total_input_tokens += totals.get('input_tokens', 0)
                    total_output_tokens += totals.get('output_tokens', 0)
                    total_thinking_tokens += totals.get('thinking_tokens', 0)
                else:
                    total_input_tokens += token_data.get('input_tokens', 0)
                    total_output_tokens += token_data.get('output_tokens', 0)
                    total_thinking_tokens += token_data.get('thinking_tokens', 0)
            
            return {
                'course_id': data.get('course_id', 'Unknown'),
                'course_name': data.get('course_name', 'Unknown'),
                'model_name': data.get('model_name', 'Unknown'),
                'total_assessments': data.get('total_assessments', 0),
                'total_cost_usd': total_cost,
                'total_cost_inr': total_cost * USD_TO_INR,
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'total_thinking_tokens': total_thinking_tokens,
                'total_tokens': total_input_tokens + total_output_tokens + total_thinking_tokens,
            }
        else:
            # This is an individual assessment file
            metrics = data.get('metrics', {})
            cost_data = metrics.get('cost', {})
            token_data = metrics.get('token_usage', {})
            
            return {
                'assessment_name': data.get('assessment_name', 'Unknown'),
                'assessment_type': data.get('assessment_type', 'Unknown'),
                'model_name': metrics.get('model_name', 'Unknown'),
                'total_cost_usd': cost_data.get('total_cost_usd', 0),
                'total_cost_inr': cost_data.get('total_cost_usd', 0) * USD_TO_INR,
                'input_tokens': token_data.get('input_tokens', 0),
                'output_tokens': token_data.get('output_tokens', 0),
                'thinking_tokens': token_data.get('thinking_tokens', 0),
                'total_tokens': token_data.get('total_tokens', 0),
                'duration_seconds': metrics.get('duration_seconds', 0),
            }
    except Exception as e:
        print(f"Error processing {json_path}: {e}")
        return None

def aggregate_all_data(outputs_dir):
    """Aggregate data from all JSON files in the outputs directory."""
    all_data = []
    model_summary = defaultdict(lambda: {
        'total_cost_usd': 0,
        'total_cost_inr': 0,
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'total_thinking_tokens': 0,
        'total_tokens': 0,
        'course_count': 0,
        'assessment_count': 0,
    })
    
    # Find all all_assessments_aqs.json files
    for json_file in Path(outputs_dir).rglob('all_assessments_aqs.json'):
        data = extract_cost_data_from_json(json_file)
        if data:
            all_data.append(data)
            model_name = data['model_name']
            model_summary[model_name]['total_cost_usd'] += data['total_cost_usd']
            model_summary[model_name]['total_cost_inr'] += data['total_cost_inr']
            model_summary[model_name]['total_input_tokens'] += data['total_input_tokens']
            model_summary[model_name]['total_output_tokens'] += data['total_output_tokens']
            model_summary[model_name]['total_thinking_tokens'] += data['total_thinking_tokens']
            model_summary[model_name]['total_tokens'] += data['total_tokens']
            model_summary[model_name]['course_count'] += 1
            model_summary[model_name]['assessment_count'] += data['total_assessments']
    
    return all_data, dict(model_summary)

def print_summary(all_data, model_summary):
    """Print a formatted summary of the cost data."""
    print("=" * 100)
    print("COST AND TOKEN SUMMARY BY MODEL")
    print("=" * 100)
    
    grand_total_usd = 0
    grand_total_inr = 0
    grand_total_input = 0
    grand_total_output = 0
    grand_total_thinking = 0
    grand_total_tokens = 0
    
    for model_name, summary in sorted(model_summary.items()):
        print(f"\nModel: {model_name}")
        print(f"  Pricing: ${MODEL_PRICING.get(model_name, {}).get('input', 0)}/1M input tokens, "
              f"${MODEL_PRICING.get(model_name, {}).get('output', 0)}/1M output tokens")
        print(f"  Courses Evaluated: {summary['course_count']}")
        print(f"  Total Assessments: {summary['assessment_count']}")
        print(f"  Input Tokens: {summary['total_input_tokens']:,}")
        print(f"  Output Tokens: {summary['total_output_tokens']:,}")
        print(f"  Thinking Tokens: {summary['total_thinking_tokens']:,}")
        print(f"  Total Tokens: {summary['total_tokens']:,}")
        print(f"  Total Cost (USD): ${summary['total_cost_usd']:.6f}")
        print(f"  Total Cost (INR): ₹{summary['total_cost_inr']:.2f}")
        
        grand_total_usd += summary['total_cost_usd']
        grand_total_inr += summary['total_cost_inr']
        grand_total_input += summary['total_input_tokens']
        grand_total_output += summary['total_output_tokens']
        grand_total_thinking += summary['total_thinking_tokens']
        grand_total_tokens += summary['total_tokens']
    
    print("\n" + "=" * 100)
    print("GRAND TOTAL (ALL MODELS)")
    print("=" * 100)
    print(f"  Total Input Tokens: {grand_total_input:,}")
    print(f"  Total Output Tokens: {grand_total_output:,}")
    print(f"  Total Thinking Tokens: {grand_total_thinking:,}")
    print(f"  Total Tokens: {grand_total_tokens:,}")
    print(f"  Total Cost (USD): ${grand_total_usd:.6f}")
    print(f"  Total Cost (INR): ₹{grand_total_inr:.2f}")
    print("=" * 100)

def export_to_csv(all_data, model_summary, output_file):
    """Export the summary data to CSV format."""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write model summary
        writer.writerow(['MODEL SUMMARY'])
        writer.writerow(['Model Name', 'Input Price ($/1M)', 'Output Price ($/1M)', 
                        'Courses', 'Assessments', 'Input Tokens', 'Output Tokens', 
                        'Thinking Tokens', 'Total Tokens', 'Cost (USD)', 'Cost (INR)'])
        
        for model_name, summary in sorted(model_summary.items()):
            pricing = MODEL_PRICING.get(model_name, {})
            writer.writerow([
                model_name,
                pricing.get('input', 0),
                pricing.get('output', 0),
                summary['course_count'],
                summary['assessment_count'],
                summary['total_input_tokens'],
                summary['total_output_tokens'],
                summary['total_thinking_tokens'],
                summary['total_tokens'],
                f"{summary['total_cost_usd']:.6f}",
                f"{summary['total_cost_inr']:.2f}",
            ])
        
        # Write grand total
        writer.writerow([])
        writer.writerow(['GRAND TOTAL'])
        grand_total_usd = sum(s['total_cost_usd'] for s in model_summary.values())
        grand_total_inr = sum(s['total_cost_inr'] for s in model_summary.values())
        grand_total_input = sum(s['total_input_tokens'] for s in model_summary.values())
        grand_total_output = sum(s['total_output_tokens'] for s in model_summary.values())
        grand_total_thinking = sum(s['total_thinking_tokens'] for s in model_summary.values())
        grand_total_tokens = sum(s['total_tokens'] for s in model_summary.values())
        
        writer.writerow(['', '', '', '', '',
                        grand_total_input, grand_total_output, grand_total_thinking,
                        grand_total_tokens, f"{grand_total_usd:.6f}", f"{grand_total_inr:.2f}"])
        
        # Write detailed course data
        writer.writerow([])
        writer.writerow(['DETAILED COURSE DATA'])
        writer.writerow(['Course ID', 'Course Name', 'Model', 'Assessments', 
                        'Input Tokens', 'Output Tokens', 'Thinking Tokens', 
                        'Total Tokens', 'Cost (USD)', 'Cost (INR)'])
        
        for data in sorted(all_data, key=lambda x: (x['model_name'], x['course_id'])):
            writer.writerow([
                data['course_id'],
                data['course_name'],
                data['model_name'],
                data['total_assessments'],
                data['total_input_tokens'],
                data['total_output_tokens'],
                data['total_thinking_tokens'],
                data['total_tokens'],
                f"{data['total_cost_usd']:.6f}",
                f"{data['total_cost_inr']:.2f}",
            ])

if __name__ == "__main__":
    # Set the outputs directory
    outputs_dir = "/home/saipraneethmeduri/Desktop/Projects/Projects/Assessment_quality_score/outputs/4"
    output_csv = "/home/saipraneethmeduri/Desktop/Projects/Projects/Assessment_quality_score/cost_estimation/cost_summary.csv"
    
    print("Extracting cost data from JSON files...")
    all_data, model_summary = aggregate_all_data(outputs_dir)
    
    print(f"\nFound {len(all_data)} courses across {len(model_summary)} models\n")
    
    # Print summary to console
    print_summary(all_data, model_summary)
    
    # Export to CSV
    print(f"\nExporting data to {output_csv}...")
    export_to_csv(all_data, model_summary, output_csv)
    print("Export complete!")
