# bff-pcef-expense-reporter

Processing and Reporting on BFF PCEF Expenses

## Setup

### Environment Variables

This project requires an OpenAI API key to process receipt images. You can set this up in two ways:

#### Option 1: Use the setup script (Recommended)

```bash
python setup_env.py
```

#### Option 2: Manual setup

Set the environment variable:

```bash
export OPEN_API_DEV_KEY="your-openai-api-key-here"
```

Or create a `.env` file in the project root:

```bash
OPEN_API_DEV_KEY=your-openai-api-key-here
```

**Note**: The `.env` file is already included in `.gitignore` to prevent accidentally committing API keys.

### Installation

1. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Process Raw Receipts

Processing Involves
    - Extracting and synthesizing receipt metadata using OpenAI's GPT-4o LLM via the API for each images in the `receipts` folder
    - Writing this metadata as a text file per image with the name of the image file the metadata was generated from
    - Creating renamed copy of file using generated metadata in `renamed` subfolder
    - Creating tracking spreadsheet that links the the three above artifacts as a line item for each processed image `receipts_processing_summary.csv `

```bash
python process_raw_receipts.py
```

Post-processing manaul steps (as needed)
- Create manually renamed copy of any files that failed the renaming step (field value for `renamed_filename` will be blank or say `No date`), UPDATE SPREADSHEET `receipts_processing_summary.csv ` with manually renamed copy filename
- Rename and UPDATE SPREADSHEET `receipts_processing_summary.csv` for any renamed files that have `Unknown` for the fiscal quarter or `08-1619` for the receipt month and year timestamp

### Create Itemized Expense Report

```bash
python parse_receipts_to_csv.py
```

### Converting All Processed Receipt Images to PDF

```bash
python convert_jpeg_to_pdf.py
```
