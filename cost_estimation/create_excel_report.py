import sys
import os
import csv
import datetime

# Add local libs to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'libs'))

try:
    import xlsxwriter
except ImportError:
    print("Error: xlsxwriter not found. Please install it using: pip install xlsxwriter --target=libs")
    sys.exit(1)

# Model pricing per 1M tokens (USD)
MODEL_PRICING = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-3-pro-preview": {"input": 2.00, "output": 12.00},
    "gemini-3-flash-preview": {"input": 0.50, "output": 3.00},
}

USD_TO_INR = 90.59

def create_excel_report():
    input_csv = '/home/saipraneethmeduri/Desktop/Projects/Projects/Assessment_quality_score/cost_estimation/cost_summary.csv'
    output_xlsx = '/home/saipraneethmeduri/Desktop/Projects/Projects/Assessment_quality_score/cost_estimation/Cost_estimation_AQS.xlsx'

    # Read CSV data
    with open(input_csv, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Create Excel workbook
    workbook = xlsxwriter.Workbook(output_xlsx)
    
    # Formats
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
    currency_fmt = workbook.add_format({'num_format': '$#,##0.000000'})
    inr_fmt = workbook.add_format({'num_format': '₹#,##0.00'})
    number_fmt = workbook.add_format({'num_format': '#,##0'})
    title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
    
    # -------------------------------------------------------------------------
    # Sheet 1: Summary
    # -------------------------------------------------------------------------
    worksheet = workbook.add_worksheet("Summary")
    
    worksheet.write('A1', 'AQS Cost Estimation Summary', title_fmt)
    worksheet.write('A2', f'Date: {datetime.date.today()}')
    worksheet.write('A3', f'Conversion Rate: 1 USD = {USD_TO_INR} INR')
    
    # Pricing Table
    worksheet.write('A5', 'Model Pricing (per 1M tokens)', title_fmt)
    headers = ['Model Name', 'Input Price ($)', 'Output Price ($)', 'Input Price (₹)', 'Output Price (₹)']
    worksheet.write_row('A6', headers, header_fmt)
    
    row = 6
    for model, pricing in sorted(MODEL_PRICING.items()):
        worksheet.write(row, 0, model)
        worksheet.write(row, 1, pricing['input'], currency_fmt)
        worksheet.write(row, 2, pricing['output'], currency_fmt)
        worksheet.write(row, 3, pricing['input'] * USD_TO_INR, inr_fmt)
        worksheet.write(row, 4, pricing['output'] * USD_TO_INR, inr_fmt)
        row += 1
        
    # Usage Summary Table
    row += 2
    worksheet.write(f'A{row}', 'Usage Summary by Model', title_fmt)
    row += 1
    
    headers = ['Model Name', 'Courses', 'Assessments', 'Input Tokens', 'Output Tokens', 'Total Tokens', 'Cost (USD)', 'Cost (INR)']
    worksheet.write_row(f'A{row}', headers, header_fmt)
    row += 1
    
    # Parse CSV for summary data (rows 2-4 roughly)
    # The CSV structure from extract_cost_data.py is:
    # Row 0: MODEL SUMMARY
    # Row 1: Header
    # Rows 2-N: Model data
    # Empty line
    # GRAND TOTAL header
    # Grand total data
    
    model_start_row = 2
    grand_total_row_index = -1
    
    start_summary_row = row
    
    for i in range(model_start_row, len(rows)):
        if not rows[i]:
            continue
        if rows[i][0] == 'GRAND TOTAL' and len(rows[i]) == 1: # Header
            continue
        if rows[i][0] == '' and len(rows[i]) > 5: # Grand total data line
             grand_total_row_index = i
             break
        if rows[i][0] == 'DETAILED COURSE DATA':
            break

        # Model row
        r = rows[i]
        if len(r) < 10: continue
        
        # CSV Cols: Model, InPrice, OutPrice, Courses, Assess, InTok, OutTok, ThinkTok, TotTok, CostUSD, CostINR
        # We want: Model, Courses, Assess, InTok, OutTok, TotTok, CostUSD, CostINR
        
        worksheet.write(row, 0, r[0]) # Model
        worksheet.write(row, 1, int(r[3]), number_fmt) # Courses
        worksheet.write(row, 2, int(r[4]), number_fmt) # Assess
        worksheet.write(row, 3, int(r[5]), number_fmt) # InTok
        worksheet.write(row, 4, int(r[6]), number_fmt) # OutTok
        worksheet.write(row, 5, int(r[8]), number_fmt) # TotTok
        worksheet.write(row, 6, float(r[9]), currency_fmt) # CostUSD
        worksheet.write(row, 7, float(r[10]), inr_fmt) # CostINR
        row += 1

    # Grand Total
    if grand_total_row_index != -1:
        gt = rows[grand_total_row_index]
        worksheet.write(row, 0, "GRAND TOTAL", header_fmt)
        worksheet.write(row, 1, "", header_fmt)
        worksheet.write(row, 2, "", header_fmt)
        worksheet.write(row, 3, int(gt[5]), number_fmt)
        worksheet.write(row, 4, int(gt[6]), number_fmt)
        worksheet.write(row, 5, int(gt[8]), number_fmt)
        worksheet.write(row, 6, float(gt[9]), currency_fmt)
        worksheet.write(row, 7, float(gt[10]), inr_fmt)

    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:H', 15)

    # -------------------------------------------------------------------------
    # Sheet 2: Detailed Data
    # -------------------------------------------------------------------------
    worksheet = workbook.add_worksheet("Detailed Data")
    
    headers = ['Course ID', 'Course Name', 'Model', 'Assessments', 'Input Tokens', 'Output Tokens', 'Total Tokens', 'Cost (USD)', 'Cost (INR)']
    worksheet.write_row('A1', headers, header_fmt)
    
    row = 1
    
    # Find start of detailed data
    detailed_start = -1
    for i in range(len(rows)):
        if rows[i] and rows[i][0] == 'DETAILED COURSE DATA':
            detailed_start = i + 2 # Skip header and subheader
            break
            
    if detailed_start != -1:
        for i in range(detailed_start, len(rows)):
            r = rows[i]
            if not r or len(r) < 8: continue
            
            # CSV: ID, Name, Model, Assess, In, Out, Think, Tot, USD, INR
            worksheet.write(row, 0, r[0])
            worksheet.write(row, 1, r[1])
            worksheet.write(row, 2, r[2])
            worksheet.write(row, 3, int(r[3]), number_fmt)
            worksheet.write(row, 4, int(r[4]), number_fmt)
            worksheet.write(row, 5, int(r[5]), number_fmt)
            worksheet.write(row, 6, int(r[7]), number_fmt) # Total
            worksheet.write(row, 7, float(r[8]), currency_fmt)
            worksheet.write(row, 8, float(r[9]), inr_fmt)
            row += 1

    worksheet.set_column('A:A', 30)
    worksheet.set_column('B:B', 40)
    worksheet.set_column('C:C', 20)
    worksheet.set_column('D:I', 15)

    workbook.close()
    print(f"Successfully created: {output_xlsx}")

if __name__ == "__main__":
    create_excel_report()
