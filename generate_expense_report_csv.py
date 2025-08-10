import csv
import re
import os
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPEN_API_DEV_KEY'))


def parse_metadata_file(metadata_file_path):
    """Parse metadata file and extract relevant information."""
    try:
        with open(metadata_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract vendor
        vendor_match = re.search(r'Vendor:\s*(.+?)(?:\n|$)', content)
        vendor = vendor_match.group(1).strip(
        ) if vendor_match else "Not specified"

        # Extract date
        date_match = re.search(r'Date:\s*(.+?)(?:\n|$)', content)
        date_str = date_match.group(1).strip() if date_match else ""

        # Extract total amount
        total_match = re.search(r'Total:\s*\$?([\d,]+\.?\d*)', content)
        total = total_match.group(1).replace(
            ',', '') if total_match else "0.00"

        # Extract notes
        notes_match = re.search(r'Notes:\s*(.+?)(?:\n|$)', content)
        notes = notes_match.group(1).strip() if notes_match else ""

        return {
            'vendor': vendor,
            'date': date_str,
            'total': total,
            'notes': notes
        }
    except Exception as e:
        print(f"Error parsing {metadata_file_path}: {e}")
        return {
            'vendor': "Error parsing",
            'date': "",
            'total': "0.00",
            'notes': f"Error: {e}"
        }


def determine_category(vendor, notes, filename):
    """Determine the expense category using GPT-5 for intelligent categorization."""
    # Define the available categories
    categories = [
        "Personnel",
        "Travel",
        "Contracts",
        "Materials",
        "Overhead",
        "Fiscal sponsor fee",
        "Other"
    ]

    # Prepare the prompt for GPT-5
    prompt = f"""Categorize this expense into one of the following categories:
{', '.join(categories)}

Expense details:
- Vendor: {vendor}
- Notes: {notes}
- Filename: {filename}

Please respond with ONLY the category name from the list above.
Do not include any explanation or additional text."""

    try:
        # Call GPT-5 for categorization
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are an expert financial analyst who categorizes "
                 "business expenses accurately and consistently."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent categorization
            max_tokens=10
        )

        # Extract the category from the response
        category = response.choices[0].message.content.strip()

        # Validate that the response is one of our expected categories
        if category in categories:
            return category
        else:
            print(f"Warning: GPT returned unexpected category '{category}' "
                  f"for vendor '{vendor}'. Defaulting to 'Other'.")
            return "Other"

    except Exception as e:
        print(
            f"Error calling GPT API for vendor '{vendor}': {e}. Defaulting to 'Other'.")
        return "Other"


def format_date(date_str):
    """Format date string to MM/DD/YYYY format."""
    if not date_str:
        return ""

    # Try to parse various date formats
    date_patterns = [
        r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # July 9, 2025 or July 9 2025
        r'(\d{1,2})/(\d{1,2})/(\d{4})',   # 07/01/25
        r'(\d{1,2})-(\d{1,2})-(\d{4})',   # 07-01-2025
    ]

    for pattern in date_patterns:
        match = re.search(pattern, date_str)
        if match:
            if pattern == date_patterns[0]:  # Month name format
                month_name = match.group(1)
                day = match.group(2)
                year = match.group(3)
                # Convert month name to number
                month_names = {
                    'january': '01', 'february': '02', 'march': '03', 'april': '04',
                    'may': '05', 'june': '06', 'july': '07', 'august': '08',
                    'september': '09', 'october': '10', 'november': '11', 'december': '12'
                }
                month = month_names.get(month_name.lower(), '01')
            else:  # Numeric format
                month = match.group(1).zfill(2)
                day = match.group(2).zfill(2)
                year = match.group(3)
                # Handle 2-digit years
                if len(year) == 2:
                    year = '20' + year

            return f"{month}/{day}/{year}"

    return date_str


def generate_expense_report():
    """Generate expense report CSV from renamed files and metadata."""

    # Paths
    base_dir = Path(__file__).parent
    summary_file = base_dir / "receipts" / "receipts_processing_summary.csv"

    now = datetime.now()
    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"{now.month:02d}-{now.day:02d}-{now.year}-{unique_id}.csv"
    output_file = base_dir / output_filename

    # Read the processing summary to map renamed files to metadata
    file_mapping = {}
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                renamed_filename = row['Renamed Filename']
                metadata_filename = row['Metadata Filename']
                if renamed_filename and metadata_filename:
                    file_mapping[renamed_filename] = metadata_filename
    except Exception as e:
        print(f"Error reading summary file: {e}")
        return

    # CSV headers matching the target format
    headers = [
        'LINE ITEM CATEGORY',
        'EXPENSE DESCRIPTION',
        'NAME OF VENDOR\n(if applicable)',
        'DOCUMENTATION TYPE',
        'DATE OF EXPENSE\n(e.g. invoice date)',
        'AMOUNT PAID WITH GRANT FUNDS',
        'SOURCE IMAGE FILE'
    ]

    # Generate CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)

        # Process each renamed file
        for renamed_file in sorted(file_mapping.keys()):
            metadata_filename = file_mapping[renamed_file]
            metadata_path = base_dir / "receipts" / metadata_filename

            if not metadata_path.exists():
                print(f"Warning: Metadata file not found: {metadata_filename}")
                continue

            # Parse metadata
            metadata = parse_metadata_file(metadata_path)

            # Determine category
            category = determine_category(
                metadata['vendor'], metadata['notes'], renamed_file)

            # Create expense description
            if metadata['notes'] and metadata['notes'] != "None":
                description = metadata['notes']
            else:
                description = f"Purchase from {metadata['vendor']}"

            # Format date
            formatted_date = format_date(metadata['date'])

            # Write row
            row = [
                category,
                description,
                metadata['vendor'],
                'Receipt',
                formatted_date,
                f"${metadata['total']}",
                renamed_file
            ]
            writer.writerow(row)

    print(f"Expense report generated successfully: {output_file}")
    print(f"Processed {len(file_mapping)} files")


if __name__ == "__main__":
    generate_expense_report()
