import json
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

# USD to INR conversion rate
USD_TO_INR = 90.59

def create_excel_population_guide():
    """Create a detailed guide for populating the Excel file."""
    
    # Read the CSV summary
    with open('/home/saipraneethmeduri/Desktop/Projects/Projects/Assessment_quality_score/cost_estimation/cost_summary.csv', 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    guide = []
    guide.append("=" * 100)
    guide.append("GUIDE TO POPULATE Cost_estimation_AQS.xlsx")
    guide.append("=" * 100)
    guide.append("")
    guide.append("This guide provides the data extracted from the codebase to fill in the Excel file.")
    guide.append("The pricing columns in the Excel file should be used for calculations as specified.")
    guide.append("")
    
    guide.append("=" * 100)
    guide.append("SECTION 1: MODEL PRICING (from aqs_evaluator.py)")
    guide.append("=" * 100)
    guide.append("")
    guide.append("Model Name                  | Input Price ($/1M tokens) | Output Price ($/1M tokens)")
    guide.append("-" * 90)
    for model_name, pricing in MODEL_PRICING.items():
        guide.append(f"{model_name:27} | ${pricing['input']:24.2f} | ${pricing['output']:25.2f}")
    guide.append("")
    
    guide.append("=" * 100)
    guide.append("SECTION 2: ACTUAL USAGE DATA (from output JSON files)")
    guide.append("=" * 100)
    guide.append("")
    
    # Parse model summary from CSV
    guide.append("MODEL SUMMARY:")
    guide.append("-" * 100)
    guide.append(f"{'Model Name':<25} | {'Courses':<8} | {'Assessments':<12} | {'Input Tokens':<15} | {'Output Tokens':<15} | {'Total Tokens':<15} | {'Cost (USD)':<12} | {'Cost (INR)':<12}")
    guide.append("-" * 100)
    
    # Find model summary rows (rows 3-5 in CSV)
    for i in range(2, 5):
        if i < len(rows) and rows[i]:
            model_name = rows[i][0]
            courses = rows[i][3]
            assessments = rows[i][4]
            input_tokens = rows[i][5]
            output_tokens = rows[i][6]
            total_tokens = rows[i][8]
            cost_usd = rows[i][9]
            cost_inr = rows[i][10]
            guide.append(f"{model_name:<25} | {courses:<8} | {assessments:<12} | {input_tokens:<15} | {output_tokens:<15} | {total_tokens:<15} | ${cost_usd:<11} | ₹{cost_inr:<11}")
    
    guide.append("-" * 100)
    guide.append("")
    
    # Grand total (row 8 in CSV)
    if len(rows) > 7:
        grand_total = rows[7]
        guide.append("GRAND TOTAL (ALL MODELS):")
        guide.append("-" * 100)
        guide.append(f"Total Input Tokens:    {grand_total[5]:>15}")
        guide.append(f"Total Output Tokens:   {grand_total[6]:>15}")
        guide.append(f"Total Tokens:          {grand_total[8]:>15}")
        guide.append(f"Total Cost (USD):      ${grand_total[9]:>14}")
        guide.append(f"Total Cost (INR):      ₹{grand_total[10]:>14}")
        guide.append("")
    
    guide.append("=" * 100)
    guide.append("SECTION 3: COST CALCULATION FORMULAS")
    guide.append("=" * 100)
    guide.append("")
    guide.append("The following formulas should be used in the Excel file:")
    guide.append("")
    guide.append("1. Input Cost (USD) = (Input Tokens / 1,000,000) × Input Price ($/1M)")
    guide.append("2. Output Cost (USD) = (Output Tokens / 1,000,000) × Output Price ($/1M)")
    guide.append("3. Total Cost (USD) = Input Cost (USD) + Output Cost (USD)")
    guide.append("4. Total Cost (INR) = Total Cost (USD) × USD_TO_INR_RATE")
    guide.append("")
    guide.append(f"Current USD to INR conversion rate used: {USD_TO_INR}")
    guide.append("")
    
    guide.append("=" * 100)
    guide.append("SECTION 4: DETAILED BREAKDOWN BY COURSE AND MODEL")
    guide.append("=" * 100)
    guide.append("")
    
    # Group courses by model
    courses_by_model = {}
    for i in range(11, len(rows)):
        if rows[i] and len(rows[i]) > 5:
            model = rows[i][2]
            if model not in courses_by_model:
                courses_by_model[model] = []
            courses_by_model[model].append(rows[i])
    
    for model_name in sorted(courses_by_model.keys()):
        guide.append(f"\n{model_name}:")
        guide.append("-" * 100)
        guide.append(f"{'Course ID':<30} | {'Course Name':<40} | {'Assessments':<12} | {'Input':<12} | {'Output':<12} | {'Total':<12} | {'USD':<10} | {'INR':<10}")
        guide.append("-" * 100)
        
        for row in courses_by_model[model_name]:
            course_id = row[0][:28]
            course_name = row[1][:38]
            assessments = row[3]
            input_tokens = row[4]
            output_tokens = row[5]
            total_tokens = row[7]
            cost_usd = row[8]
            cost_inr = row[9]
            guide.append(f"{course_id:<30} | {course_name:<40} | {assessments:<12} | {input_tokens:<12} | {output_tokens:<12} | {total_tokens:<12} | ${cost_usd:<9} | ₹{cost_inr:<9}")
    
    guide.append("")
    guide.append("=" * 100)
    guide.append("END OF GUIDE")
    guide.append("=" * 100)
    
    return "\n".join(guide)

if __name__ == "__main__":
    guide_text = create_excel_population_guide()
    
    # Save to file
    output_file = "/home/saipraneethmeduri/Desktop/Projects/Projects/Assessment_quality_score/cost_estimation/excel_population_guide.txt"
    with open(output_file, 'w') as f:
        f.write(guide_text)
    
    print(guide_text)
    print(f"\n\nGuide saved to: {output_file}")
