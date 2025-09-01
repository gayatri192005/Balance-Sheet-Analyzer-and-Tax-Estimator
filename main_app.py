import os
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
import base64
from io import BytesIO
from fpdf import FPDF
from datetime import datetime 
    
google_api_key = st.secrets["GOOGLE_API_KEY"]

# Configure Streamlit
st.set_page_config(page_title="Balance Sheet Analyzer & Tax Estimator", layout="wide")
st.title("Balance Sheet Analyzer & Tax Estimator")

# Initialize session state for chat
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "financial_data" not in st.session_state:
    st.session_state.financial_data = None
if "viz_recommendations" not in st.session_state:
    st.session_state.viz_recommendations = None
if "tax_inputs" not in st.session_state:
    st.session_state.tax_inputs = None

# Initialize Gemini model
def get_gemini_model():
    return ChatGoogleGenerativeAI(
        temperature=0.5,
        model="gemini-1.5-flash",
        google_api_key=st.secrets["GOOGLE_API_KEY"],  
        safety_settings={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
        }
    )

# File upload section
st.sidebar.header("Upload Financial Data")
uploaded_file = st.sidebar.file_uploader(
    "Choose Excel or CSV file", 
    type=["xlsx", "xls", "csv"],
    help="Upload your cash flow, journal, ledgers, or Tally exported data"
)

# Function to collect missing tax inputs

def get_missing_tax_inputs(analysis_text):
    st.sidebar.subheader("Provide Missing Tax Information")
    
    tax_inputs = {}
    missing_fields = []
    
    # More robust detection of missing information
    missing_data_phrases = [
        "not available", "missing", "requires", "needed", 
        "not provided", "not found", "unavailable"
    ]

    # Check each tax component
    if any(phrase in analysis_text.lower() for phrase in missing_data_phrases):
        if "income" in analysis_text.lower():
            missing_fields.extend(["total_income", "business_income", "capital_gains", "other_income", "turnover", "gross_receipts"])
        if "gst" in analysis_text.lower():
            missing_fields.extend(["output_gst", "input_gst", "gst_rate"])
        if "deduction" in analysis_text.lower():
            missing_fields.extend(["section_80c", "section_80d", "hra_exemption", "other_deductions", 
                                "home_loan_interest", "education_loan_interest", "nps_contribution",
                                "standard_deduction"])
        if "tax payable" in analysis_text.lower() or "tax liability" in analysis_text.lower():
            missing_fields.extend(["previous_tax_paid", "tds", "advance_tax_paid"])
        if "depreciation" in analysis_text.lower():
            missing_fields.extend(["depreciation_claimed"])
        if "loss" in analysis_text.lower():
            missing_fields.extend(["carried_forward_losses"])
        if "regime" in analysis_text.lower():
            missing_fields.extend(["regime_type"])
        if "presumptive" in analysis_text.lower():
            missing_fields.extend(["presumptive_scheme_applicable", "presumptive_section"])
        if "audit" in analysis_text.lower():
            missing_fields.extend(["audit_required"])
        if "pan" in analysis_text.lower() or "type" in analysis_text.lower():
            missing_fields.extend(["pan_type"])
        if "age" in analysis_text.lower():
            missing_fields.extend(["age"])
    
    # Remove duplicates while preserving order
    missing_fields = list(dict.fromkeys(missing_fields))
    
    # Dynamically create input fields based on missing information
    if missing_fields:
        # Group fields into categories
        income_fields = [f for f in missing_fields if f in ["total_income", "business_income", "capital_gains", 
                                                          "other_income", "turnover", "gross_receipts"]]
        deduction_fields = [f for f in missing_fields if f in ["section_80c", "section_80d", "hra_exemption", 
                                                             "other_deductions", "home_loan_interest",
                                                             "education_loan_interest", "nps_contribution",
                                                             "standard_deduction", "depreciation_claimed",
                                                             "carried_forward_losses"]]
        gst_fields = [f for f in missing_fields if f in ["output_gst", "input_gst", "gst_rate"]]
        tax_payment_fields = [f for f in missing_fields if f in ["previous_tax_paid", "tds", "advance_tax_paid"]]
        regime_fields = [f for f in missing_fields if f in ["regime_type", "presumptive_scheme_applicable", 
                                                          "presumptive_section", "audit_required", 
                                                          "pan_type", "age"]]
        
        if income_fields:
            with st.sidebar.expander("Income Details", expanded=True):
                if "total_income" in income_fields:
                    tax_inputs['total_income'] = st.number_input("Total Taxable Income (₹)", min_value=0, value=0)
                if "business_income" in income_fields:
                    tax_inputs['business_income'] = st.number_input("Business Income (₹)", min_value=0, value=0)
                if "capital_gains" in income_fields:
                    tax_inputs['capital_gains'] = st.number_input("Capital Gains (₹)", min_value=0, value=0)
                if "other_income" in income_fields:
                    tax_inputs['other_income'] = st.number_input("Other Income (₹)", min_value=0, value=0)
                if "turnover" in income_fields:
                    tax_inputs['turnover'] = st.number_input("Turnover (₹)", min_value=0, value=0)
                if "gross_receipts" in income_fields:
                    tax_inputs['gross_receipts'] = st.number_input("Gross Receipts (₹)", min_value=0, value=0)
        
        if deduction_fields:
            with st.sidebar.expander("Deductions", expanded=False):
                if "section_80c" in deduction_fields:
                    tax_inputs['section_80c'] = st.number_input("Section 80C Deductions (₹)", min_value=0, value=0)
                if "section_80d" in deduction_fields:
                    tax_inputs['section_80d'] = st.number_input("Section 80D (Health Insurance) (₹)", min_value=0, value=0)
                if "hra_exemption" in deduction_fields:
                    tax_inputs['hra_exemption'] = st.number_input("HRA Exemption (₹)", min_value=0, value=0)
                if "other_deductions" in deduction_fields:
                    tax_inputs['other_deductions'] = st.number_input("Other Deductions (₹)", min_value=0, value=0)
                if "home_loan_interest" in deduction_fields:
                    tax_inputs['home_loan_interest'] = st.number_input("Home Loan Interest (₹)", min_value=0, value=0)
                if "education_loan_interest" in deduction_fields:
                    tax_inputs['education_loan_interest'] = st.number_input("Education Loan Interest (₹)", min_value=0, value=0)
                if "nps_contribution" in deduction_fields:
                    tax_inputs['nps_contribution'] = st.number_input("NPS Contribution (₹)", min_value=0, value=0)
                if "standard_deduction" in deduction_fields:
                    tax_inputs['standard_deduction'] = st.number_input("Standard Deduction (₹)", min_value=0, value=0)
                if "depreciation_claimed" in deduction_fields:
                    tax_inputs['depreciation_claimed'] = st.number_input("Depreciation Claimed (₹)", min_value=0, value=0)
                if "carried_forward_losses" in deduction_fields:
                    tax_inputs['carried_forward_losses'] = st.number_input("Carried Forward Losses (₹)", min_value=0, value=0)
        
        if gst_fields:
            with st.sidebar.expander("GST Details", expanded=False):
                if "output_gst" in gst_fields:
                    tax_inputs['output_gst'] = st.number_input("Output GST Collected (₹)", min_value=0, value=0)
                if "input_gst" in gst_fields:
                    tax_inputs['input_gst'] = st.number_input("Input GST Paid (₹)", min_value=0, value=0)
                if "gst_rate" in gst_fields:
                    tax_inputs['gst_rate'] = st.selectbox("Applicable GST Rate", ["5%", "12%", "18%", "28%", "0%"])
        
        if tax_payment_fields:
            with st.sidebar.expander("Tax Payments & Credits", expanded=False):
                if "previous_tax_paid" in tax_payment_fields:
                    tax_inputs['previous_tax_paid'] = st.number_input("Tax Already Paid (₹)", min_value=0, value=0)
                if "tds" in tax_payment_fields:
                    tax_inputs['tds'] = st.number_input("TDS Deducted (₹)", min_value=0, value=0)
                if "advance_tax_paid" in tax_payment_fields:
                    tax_inputs['advance_tax_paid'] = st.number_input("Advance Tax Paid (₹)", min_value=0, value=0)
        
        if regime_fields:
            with st.sidebar.expander("Tax Regime & Status", expanded=False):
                if "regime_type" in regime_fields:
                    tax_inputs['regime_type'] = st.selectbox("Tax Regime", ["Old", "New"])
                if "presumptive_scheme_applicable" in regime_fields:
                    tax_inputs['presumptive_scheme_applicable'] = st.checkbox("Presumptive Scheme Applicable?")
                if "presumptive_section" in regime_fields:
                    tax_inputs['presumptive_section'] = st.selectbox("Presumptive Taxation Section", 
                                                                  ["Not Applicable", "44AD", "44ADA", "44AE"])
                if "audit_required" in regime_fields:
                    tax_inputs['audit_required'] = st.checkbox("Audit Required?")
                if "pan_type" in regime_fields:
                    tax_inputs['pan_type'] = st.selectbox("PAN Type", ["Individual", "HUF", "Company", "Firm", "Others"])
                if "age" in regime_fields:
                    tax_inputs['age'] = st.number_input("Age", min_value=0, max_value=120, value=30)
        
        return tax_inputs

# Function to process uploaded file
def process_file(uploaded_file):
    if uploaded_file is None:
        return None
    
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, sheet_name=None)
        return df
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None

# Function to analyze financial data
def analyze_financials(data, tax_inputs=None):
    llm = get_gemini_model()
    
    # Convert data to string for analysis
    if isinstance(data, dict):
        data_str = "\n\n".join([f"Sheet: {name}\n{df.head().to_string()}" for name, df in data.items()])
    else:
        data_str = data.head().to_string()
    
    # Include tax inputs in the prompt if provided
    tax_inputs_str = ""
    if tax_inputs:
        tax_inputs_str = f"\n\nAdditional Tax Inputs Provided:\n{tax_inputs}"
    
    # Generate financial analysis with strict instructions
    analysis_prompt = f"""
    Analyze the following financial data strictly using only the provided numbers. Parse the data into income, expenses, assets, liabilities, outstanding loans, purchase/sales with GST by auto tagging. 
    Do not assume or generate any hypothetical values. If data is missing for any calculation, 
    clearly state "Data not available" for that specific item. With minimal input and values, you have to be the best financial assisstant by providing reports. Make sure to calculate everything. Use the tax inputs data in updated report.
    
    {tax_inputs_str}
    
    Provide concise, actionable insights in this structure from teh analyzed data: 
    
    1. PROFIT & LOSS STATEMENT: Double check by calculating and checking with all values so that there are no calculation errors.
    - Total Revenue: [actual value if available]
    - Total Expenses: [actual value if available]
    - Net Profit/Loss (before and after tax): [calculated only if both above available]
    - Provide profit and loss statement in the business and financial accountancy format with all the parsed data you obtained (income, expenses, assets, liabilities, outstanding loans, purchase/sales with GST.). Inlude all profits and losse too. If value not available, don't include it in the statement.
    
    2. Generate the estimated tax liability. If it can be calculated, provide the calculation steps.
    3. Generate the summary of input and output GST from the analyzed data in 2-3 lines.
    4. Generate the summary of Tax Deducted Source (TDS) from the analyzed data in 2 -3 lines. You can generate any other most wanted financial related calculations if the data for it is avialable.

    5. KEY OBSERVATIONS:
    - List 3-5 most important findings from the data.
    - Financial summary and insights of the analyzed data in 5-6 lines.

    5. ACTION ITEMS:
    - Include any 2 most important recommendations for improving financial health 
    
    
    Financial Data:
    {data_str}
    """
    
    response = llm.invoke(analysis_prompt)
    return response.content

# Function to get visualization recommendations
def get_visualization_recommendations(data):
    llm = get_gemini_model()
    
    if isinstance(data, dict):
        sample_data = next(iter(data.values())).head().to_string()
    else:
        sample_data = data.head().to_string()
    
    prompt = f"""
    Analyze this financial dataset and after understanding it, recommend 3-5 most valuable visualization types. Make it very short.
    I'm only giving 2 columns option. And these can only be generated: line, bar, pie, scatter, histogram.
    For each recommendation, specify:
    - Chart type, required columns, business insight it would reveal in one line
    
    Don't include any unncessary details/explanations, or columns which might give an error if we used.
    Include only visualization types that would provide meaningful financial insights.
    
    Data Sample:
    {sample_data}
    """
    
    response = llm.invoke(prompt)
    return response.content

# Function to generate visualizations
def generate_visualization(df, chart_type, x_col, y_col=None):
    try:
        if chart_type == "Line Chart":
            fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} Trend")
        elif chart_type == "Bar Chart":
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        elif chart_type == "Pie Chart":
            fig = px.pie(df, names=x_col, values=y_col, title=f"{y_col} Distribution")
        elif chart_type == "Scatter Plot":
            fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
        elif chart_type == "Histogram":
            fig = px.histogram(df, x=x_col, title=f"Distribution of {x_col}")
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Could not generate chart: {str(e)}")

def generate_professional_pdf(analysis_text):
    pdf = FPDF()
    pdf.add_page()
    
    # Set colors and styles
    header_color = (50, 100, 150)  # Dark blue
    section_color = (70, 130, 180)  # Steel blue
    text_color = (0, 0, 0)  # Black
    line_height = 7
    
    # Title and header
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(*header_color)
    pdf.cell(0, 10, "Financial Analysis Report", 0, 1, 'C')
    
    # Date
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(100, 100, 100)  # Gray
    pdf.cell(0, 8, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
    pdf.ln(12)
    
    # Clean up the analysis text first - replace special chars with alternatives
    def clean_text(text):
        replacements = {
            '•': '-',   # Bullet to hyphen
            '≈': '~',   # Approximately equals to tilde
            '–': '-',   # En dash to hyphen
            '—': '-',   # Em dash to hyphen
            '₹': 'Rs.', # Rupee symbol to text
            '×': 'x',   # Multiplication sign to x
            '÷': '/',   # Division sign to slash
            '±': '+/-', # Plus-minus to text
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text
    
    cleaned_text = clean_text(analysis_text.replace("*", "").replace("**", "").replace("====", ""))
    
    # Process each section
    sections = cleaned_text.split('\n\n')
    for section in sections:
        if not section.strip():
            continue
            
        # Section headers
        if section.startswith(('1.', '2.', '3.', '4.', '5.')):
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(*section_color)
            section_title = section.split(':')[0].strip()
            pdf.cell(0, line_height+2, section_title, 0, 1)
            pdf.set_text_color(*text_color)
            pdf.set_font("Arial", '', 10)
            
            # Add underline
            pdf.set_draw_color(*section_color)
            pdf.cell(0, 1, "", "B", 1)
            pdf.ln(3)
            
            content = ':'.join(section.split(':')[1:]).strip()
        else:
            content = section
        
        # Handle tables - improved version with character cleaning
        if '|' in content and any('---' in line or '===' in line for line in content.split('\n')):
            # Extract table data
            table_data = []
            for line in content.split('\n'):
                if '---' in line or '===' in line:
                    continue  # Skip separator lines
                if '|' in line:
                    # Clean and split the row
                    row = [clean_text(cell.strip()) for cell in line.split('|') if cell.strip()]
                    table_data.append(row)
            
            # Calculate column widths
            if table_data:
                col_count = len(table_data[0])
                col_width = 190 / col_count
                
                # Draw table
                for row in table_data:
                    if len(row) == col_count:  # Only process rows with correct column count
                        for cell in row:
                            pdf.cell(col_width, line_height, cell, border=1)
                        pdf.ln()
                pdf.ln(3)
            
        # Handle bullet points
        elif content.strip().startswith('- '):
            items = [clean_text(item.strip('- ').strip()) for item in content.split('\n') if item.strip()]
            for item in items:
                pdf.cell(5, line_height, "", 0, 0)  # Small indent
                pdf.cell(5, line_height, "-", 0, 0)  # Using hyphen for bullet
                pdf.multi_cell(0, line_height, f" {item}", 0, 1)
            pdf.ln(2)
            
        # Regular text
        else:
            clean_content = clean_text(content)
            pdf.multi_cell(0, line_height, clean_content)
            pdf.ln(3)
    
    return pdf

# Modified financial_chat function
def financial_chat(query, analysis, data):
    llm = get_gemini_model()
    
    # Convert data to string for context
    if isinstance(data, dict):
        data_str = "\n\n".join([f"Sheet: {name}\n{df.head().to_string()}" for name, df in data.items()])
    else:
        data_str = data.head().to_string()
    
    # Enhanced prompt with calculation instructions
    prompt = f"""
    You are a indian financial advisor who is upto date with all info, who does Balance Sheet Analyzing and Tax Estimation, while also, helping with financial data analysis. Follow these rules:
    
    1. For direct calculation requests (like tax calculations):
    - Extract required numbers ONLY from this data
    - Perform the math immediately
    - Show the calculation steps concisely
    - Format as: "Tax Liability: [amount] (Calculation: [base] × [rate] = [result])"
    
    2. For general questions:
    - Keep responses very short and to the point, but for questions that needed to be answered lengthy, provide a summary of the analysis in 3-5 bullet points.

    3. If asked for more/elaborate details or if the user indicates in some way that he/she doesn't understand, keep your responses under 12 lines.
    
    Current Analysis:
    {analysis}
    
    Raw Data Reference:
    {data_str}
    
    User Question: {query}
    
    Respond ONLY with the requested calculation or analysis. No disclaimers.
    """
    
    response = llm.invoke(prompt)
    return response.content

# Add this function to your existing code
def tax_news_agent(query=None):
    """
    Simple agent that provides latest tax and financial updates in India
    """
    llm = get_gemini_model()
    
    prompt = f"""
    You are a specialized tax news bot for Indian taxation and finance. Your task is to:
    
    1. Provide the 3-5 most important recent updates in Indian taxation (last 3 months)
    2. Include effective dates and brief impact analysis (1 sentence each)
    3. For financial updates, focus on changes affecting businesses/individual taxes
    Give the above in good, readable format.
    
    Structure your response:
    - Latest Updates (date):
      • [Update 1] (Effective: [date]) - [impact]
      • [Update 2] (Effective: [date]) - [impact]
    
    - Current Important Rules:
      • [Rule 1] - [brief explanation]
    
    Note: Today is {datetime.now().strftime('%Y-%m-%d')}
    """
    
    response = llm.invoke(prompt)
    return response.content

# Main app logic
if uploaded_file:
    data = process_file(uploaded_file)
    
    if data is not None:
        st.session_state.financial_data = data
        st.success("File successfully uploaded!")
        
        if st.button("Generate Financial Analysis", type="primary"):
            with st.spinner("Analyzing financial data..."):
                try:
                    with time_limit(30):  # 30 second timeout
                        analysis = analyze_financials(data)
                        st.session_state.analysis = analysis
                        st.session_state.analysis_done = True
                except TimeoutException:
                    st.error("Analysis timed out after 30 seconds")
                except Exception as e:
                    st.error(f"Failed: {str(e)}")
                                
                st.session_state.analysis = analysis
                st.session_state.analysis_done = True
                st.session_state.messages = []
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "What would you like to discuss about your financials?"
                })
        
        # Create tabs for different sections
        # Modify your tab creation code
        tab1, tab2, tab3, tab4 = st.tabs([
            "Financial Analysis Report", 
            "Raw Data Preview",
            "Visualize your finances",
            "Tax Updates"
            ])

        with tab1:
            if st.session_state.analysis_done:
                st.markdown(st.session_state.analysis)
                missing_data_phrases = [
                    "not available", "missing", "requires", "needed", 
                    "not provided", "not found", "unavailable"
                ]
                
                has_missing_data = any(
                    phrase in st.session_state.analysis.lower() 
                    for phrase in missing_data_phrases
                )
                
                if has_missing_data:
                    st.warning("Additional information may be needed for complete analysis. Please check below.")
                    
                    # Get tax inputs from user based on missing fields
                    st.session_state.tax_inputs = get_missing_tax_inputs(st.session_state.analysis)
                    
                    if st.session_state.tax_inputs and st.button("Update Calculation", key="update_tax"):
                        with st.spinner("Recalculating with provided information..."):
                            updated_analysis = analyze_financials(data, st.session_state.tax_inputs)
                            st.session_state.analysis = updated_analysis
                            st.rerun()
                    elif not st.session_state.tax_inputs:
                        st.info("No additional information needed - analysis is complete!")
                
                # PDF and Save buttons in columns
                col1, col2 = st.columns(2)
                with col1:
                    # Download PDF button
                    pdf = generate_professional_pdf(st.session_state.analysis)

                    # Create a BytesIO buffer to capture the PDF
                    pdf_buffer = BytesIO()
                    try:
                        # First try with Latin-1 encoding
                        pdf_output = pdf.output(dest='S').encode('latin1', 'replace')
                    except UnicodeEncodeError:
                        # If Latin-1 fails, try UTF-8 with replacement
                        try:
                            pdf_output = pdf.output(dest='S').encode('utf-8', 'replace')
                        except Exception as e:
                            st.error(f"Failed to generate PDF: {str(e)}")
                            pdf_output = b''  # Empty bytes as fallback

                    if pdf_output:
                        b64 = base64.b64encode(pdf_output).decode()
                        href = f'<a href="data:application/pdf;base64,{b64}" download="financial_analysis.pdf" style="text-decoration: none; background-color: #4CAF50; color: white; padding: 10px 20px; border-radius: 5px; display: inline-block;">Download PDF Report</a>'
                        st.markdown(href, unsafe_allow_html=True)
                                
        with tab2:
            if isinstance(data, dict):
                sheet_name = st.selectbox("Select sheet to view", list(data.keys()))
                st.dataframe(data[sheet_name].head())
            else:
                st.dataframe(data.head())
        
        with tab3:
            st.subheader("Visualization Assistant")
            
            if isinstance(data, dict):
                selected_sheet = st.selectbox("Select data sheet", list(data.keys()))
                df = data[selected_sheet]
            else:
                df = data
            
            # Show AI recommendations
            with st.expander("Recommended Visualizations"):
                if st.session_state.viz_recommendations is None:
                    with st.spinner("Analyzing for best visualizations..."):
                        st.session_state.viz_recommendations = get_visualization_recommendations(data)
                st.markdown(st.session_state.viz_recommendations)
            
            # Visualization controls
            st.markdown("---")
            st.subheader("Create Custom Visualization")
            
            col1, col2 = st.columns(2)
            with col1:
                chart_type = st.selectbox(
                    "Select Chart Type",
                    ["Line Chart", "Bar Chart", "Pie Chart", "Scatter Plot", "Histogram"]
                )
            with col2:
                numeric_cols = df.select_dtypes(include=['number']).columns
                date_cols = df.select_dtypes(include=['datetime']).columns
                all_cols = df.columns
                
                x_col = st.selectbox("X-Axis Column", all_cols)
                if chart_type != "Histogram":
                    y_col = st.selectbox("Y-Axis Column", numeric_cols)
                else:
                    y_col = None
            
            if st.button("Generate Chart"):
                with st.spinner("Creating visualization..."):
                    generate_visualization(df, chart_type, x_col, y_col if y_col else x_col)
        with tab4:
            st.subheader("Live Tax Updates")
            
            # Display general updates by default
            if "tax_updates" not in st.session_state:
                with st.spinner("Fetching latest tax updates..."):
                    st.session_state.tax_updates = tax_news_agent()
            
            st.markdown(st.session_state.tax_updates)
            
else: 
    st.info("Please upload a financial data file to begin analysis")

# Chat interface (only show if analysis is done)
if st.session_state.analysis_done:
    st.markdown("---")
    st.subheader("Financial Advisor Chat")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about your financial data..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.spinner("Analyzing your question..."):
            response = financial_chat(
                prompt,
                st.session_state.analysis,
                st.session_state.financial_data
            )
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Display assistant response
        with st.chat_message("assistant"):
            st.markdown(response)

# Add custom CSS
st.markdown("""
<style>
    .stMetric {
        border-left: 5px solid #4b8bff;
        padding: 10px;
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #4b8bff;
        color: white;
    }
    .stTabs [aria-selected="true"] {
        font-weight: bold;
        color: #4b8bff;
    }
</style>
""", unsafe_allow_html=True)
