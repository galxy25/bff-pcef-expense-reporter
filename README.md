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

   Or install individually:

   ```bash
   pip install openai python-dotenv
   ```

## Usage

### Process Receipts to CSV

```bash
python parse_receipts_to_csv.py
```

### Extract Expense Metadata

```bash
python extract_expense_metadata.py
```

## Files

- `parse_receipts_to_csv.py` - Processes receipt images and outputs CSV data
- `extract_expense_metadata.py` - Extracts metadata from receipt images
- `setup_env.py` - Helper script to set up environment variables
- `raws/` - Directory containing receipt images to process
- `expenses.csv` - Output CSV file with processed expense data
