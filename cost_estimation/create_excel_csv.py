import csv

# Model pricing per 1M tokens (USD)
MODEL_PRICING = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-3-pro-preview": {"input": 2.00, "output": 12.00},
    "gemini-3-flash-preview": {"input": 0.50, "output": 3.00},
}

USD_TO_INR = 90.59

# Read the cost summary data
with open('/home/saipraneethmeduri/Desktop/Projects/Projects/Assessment_quality_score/cost_estimation/cost_summary.csv', 'r') as f:
    reader = csv.reader(f)
    rows = list(reader)

# Create a structured CSV for Excel import
output_file = '/home/saipraneethmeduri/Desktop/Projects/Projects/Assessment_quality_score/cost_estimation/Cost_Estimation_Data_For_Excel.csv'

with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    
    # Header section
    writer.writerow(['AQS COST ESTIMATION SUMMARY'])
    writer.writerow([])
    writer.writerow(['Generated from codebase analysis'])
    writer.writerow(['Date:', '2026-02-11'])
    writer.writerow([])
    
    # Pricing table
    writer.writerow(['MODEL PRICING (from aqs_evaluator.py)'])
    writer.writerow(['Model Name', 'Input Price ($/1M tokens)', 'Output Price ($/1M tokens)', 'Input Price (₹/1M tokens)', 'Output Price (₹/1M tokens)'])
    for model_name, pricing in sorted(MODEL_PRICING.items()):
        writer.writerow([
            model_name,
            pricing['input'],
            pricing['output'],
            pricing['input'] * USD_TO_INR,
            pricing['output'] * USD_TO_INR,
        ])
    writer.writerow([])
    
    # Conversion rate
    writer.writerow(['CONVERSION RATE'])
    writer.writerow(['USD to INR', USD_TO_INR])
    writer.writerow([])
    
    # Model summary
    writer.writerow(['USAGE SUMMARY BY MODEL'])
    writer.writerow(['Model Name', 'Input Price ($/1M)', 'Output Price ($/1M)', 'Courses Evaluated', 'Total Assessments', 
                    'Input Tokens', 'Output Tokens', 'Thinking Tokens', 'Total Tokens', 
                    'Input Cost (USD)', 'Output Cost (USD)', 'Total Cost (USD)', 'Total Cost (INR)'])
    
    # Extract model summary data (rows 2-4 from original CSV)
    for i in range(2, 5):
        if i < len(rows) and rows[i]:
            model_name = rows[i][0]
            pricing = MODEL_PRICING.get(model_name, {})
            input_price = pricing.get('input', 0)
            output_price = pricing.get('output', 0)
            courses = rows[i][3]
            assessments = rows[i][4]
            input_tokens = int(rows[i][5])
            output_tokens = int(rows[i][6])
            thinking_tokens = int(rows[i][7])
            total_tokens = int(rows[i][8])
            
            # Calculate costs
            input_cost = (input_tokens / 1_000_000) * input_price
            output_cost = (output_tokens / 1_000_000) * output_price
            total_cost_usd = input_cost + output_cost
            total_cost_inr = total_cost_usd * USD_TO_INR
            
            writer.writerow([
                model_name,
                input_price,
                output_price,
                courses,
                assessments,
                input_tokens,
                output_tokens,
                thinking_tokens,
                total_tokens,
                f'{input_cost:.6f}',
                f'{output_cost:.6f}',
                f'{total_cost_usd:.6f}',
                f'{total_cost_inr:.2f}',
            ])
    
    # Grand total
    if len(rows) > 7:
        grand_total = rows[7]
        total_input = int(grand_total[5])
        total_output = int(grand_total[6])
        total_thinking = int(grand_total[7])
        total_tokens = int(grand_total[8])
        total_cost_usd = float(grand_total[9])
        total_cost_inr = float(grand_total[10])
        
        writer.writerow([])
        writer.writerow(['GRAND TOTAL', '', '', '', '',
                        total_input, total_output, total_thinking, total_tokens,
                        '', '', total_cost_usd, total_cost_inr])
    
    writer.writerow([])
    writer.writerow([])
    
    # Formulas section
    writer.writerow(['CALCULATION FORMULAS'])
    writer.writerow(['Formula Name', 'Formula'])
    writer.writerow(['Input Cost (USD)', '= (Input Tokens / 1,000,000) × Input Price ($/1M)'])
    writer.writerow(['Output Cost (USD)', '= (Output Tokens / 1,000,000) × Output Price ($/1M)'])
    writer.writerow(['Total Cost (USD)', '= Input Cost (USD) + Output Cost (USD)'])
    writer.writerow(['Total Cost (INR)', '= Total Cost (USD) × USD_TO_INR_RATE'])
    writer.writerow([])
    
    # Detailed course data
    writer.writerow(['DETAILED COURSE DATA'])
    writer.writerow(['Course ID', 'Course Name', 'Model', 'Assessments', 
                    'Input Tokens', 'Output Tokens', 'Thinking Tokens', 'Total Tokens',
                    'Input Cost (USD)', 'Output Cost (USD)', 'Total Cost (USD)', 'Total Cost (INR)'])
    
    for i in range(11, len(rows)):
        if rows[i] and len(rows[i]) > 5:
            course_id = rows[i][0]
            course_name = rows[i][1]
            model = rows[i][2]
            assessments = rows[i][3]
            input_tokens = int(rows[i][4]) if rows[i][4] else 0
            output_tokens = int(rows[i][5]) if rows[i][5] else 0
            thinking_tokens = int(rows[i][6]) if rows[i][6] else 0
            total_tokens = int(rows[i][7]) if rows[i][7] else 0
            
            # Calculate costs
            pricing = MODEL_PRICING.get(model, {})
            input_price = pricing.get('input', 0)
            output_price = pricing.get('output', 0)
            input_cost = (input_tokens / 1_000_000) * input_price
            output_cost = (output_tokens / 1_000_000) * output_price
            total_cost_usd = input_cost + output_cost
            total_cost_inr = total_cost_usd * USD_TO_INR
            
            writer.writerow([
                course_id,
                course_name,
                model,
                assessments,
                input_tokens,
                output_tokens,
                thinking_tokens,
                total_tokens,
                f'{input_cost:.6f}',
                f'{output_cost:.6f}',
                f'{total_cost_usd:.6f}',
                f'{total_cost_inr:.2f}',
            ])

print(f"Created structured CSV file: {output_file}")
print("\nThis CSV file can be opened in Excel and the data can be copied to the Cost_estimation_AQS.xlsx file.")
print("\nKey data points:")
print(f"  - Total courses analyzed: 44")
print(f"  - Models used: 3 (gemini-2.0-flash, gemini-2.5-flash, gemini-3-flash-preview)")
print(f"  - Total tokens: 269,733")
print(f"  - Total cost: $0.731 USD (₹66.21 INR)")
