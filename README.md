
# Balance Sheet Analyzer & Tax Estimator

This is a powerful Streamlit-based financial analysis tool that allows users to upload financial files and receive insights, Profit & Loss statements, estimated tax liability, and GST/TDS summaries using AI (Gemini Pro). It supports chat-based interaction and live tax updates.

## Features

- Upload `.csv`, `.xls`, or `.xlsx` financial data files (cash flow, ledgers, journal entries, or Tally exports).
- AI-powered analysis that:
  - Parses and classifies income, expenses, assets, liabilities, GST
  - Generates Profit & Loss statements in accounting format
  - Estimates tax liability with detailed calculation steps
  - Summarizes input/output GST and TDS
  - Extracts key insights and action recommendations
- Asks for missing tax data interactively
- Offers visualizations (bar, line, pie, scatter, histogram) with AI recommendations
- Generates a professional PDF report
- Includes live tax updates from Indian regulations (last 3 months)
- Built-in chat assistant to answer financial questions

## Tech Stack

- **Frontend**: Streamlit
- **Backend/AI**: LangChain with Gemini 1.5 Flash
- **PDF Generation**: FPDF
- **Visualization**: Plotly
- **Environment Variables**: Python-dotenv for API key

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/JUSTWANTTODO/Balance-Sheet-Analyzer-and-Tax-Estimator.git
   cd Balance-Sheet-Analyzer-and-Tax-Estimator
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the root directory:
   ```
   GOOGLE_API_KEY=your_google_gemini_api_key
   ```

4. **Run the Streamlit app**:
   ```bash
   streamlit run main_app.py
   ```

## Notes

- You must have a valid Gemini API key from Google AI Studio.
- Tested with Tally and accounting exports in Excel/CSV formats.
- Alternate file (for main_app.py) - AlterForDotEnv.py

## License

MIT License. Feel free to use, modify, and contribute.
