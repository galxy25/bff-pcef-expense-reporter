import os
import csv
import base64
from openai import OpenAI
from datetime import datetime
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if API key is set
api_key = os.getenv("OPEN_API_DEV_KEY")
if not api_key:
    raise ValueError(
        "OPEN_API_DEV_KEY environment variable is not set. "
        "Please run 'python setup_env.py' or set the environment variable "
        "manually."
    )

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Folder containing the receipt images
FOLDER_PATH = "processed"

# Define the prompt for receipt extraction
EXTRACTION_PROMPT = (
    "Extract the following information from this receipt image:\n"
    "- Vendor/store name (the business that issued the receipt)\n"
    "- Total cost (currency and amount)\n"
    "- Date of purchase\n"
    "- Any handwritten notes or markings\n"
    "- Line item category (Materials, Contracts, Personnel, Other, Overhead)\n"
    "- Expense description (e.g., Farm Supplies, Staff Meal, etc.)\n\n"
    "Format the result as:\n"
    "Vendor: <vendor/store name>\n"
    "Date: <date>\n"
    "Total: <amount>\n"
    "Category: <line item category>\n"
    "Description: <expense description>\n"
    "Notes: <handwritten notes or 'None'>"
)


def parse_amount(amount_str):
    """Parse amount string and return numeric value."""
    if not amount_str:
        return None

    # Remove currency symbols and commas
    cleaned = re.sub(r'[$,]', '', amount_str.strip())

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(date_str):
    """Parse date string and return formatted date."""
    if not date_str:
        return None

    # Common date formats to try
    date_formats = [
        "%m/%d/%Y",   # 05/29/2025
        "%m/%d/%y",   # 05/29/25
        "%B %d, %Y",  # May 29, 2025
        "%b %d, %Y",  # May 29, 2025
        "%Y-%m-%d",   # 2025-05-29
        "%d/%m/%Y",   # 29/05/2025
    ]

    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt)
            return parsed_date.strftime("%m/%d/%Y")
        except ValueError:
            continue

    return None


def determine_category_and_description(vendor_name, total_amount, notes):
    """Determine line item category and expense description based on vendor and context."""
    vendor_lower = vendor_name.lower()

    # Default values
    category = "Materials"
    description = "Farm Supplies"

    # Staff meals
    staff_meal_vendors = [
        "whole bowl", "new seasons", "thai sunflower", "super torta",
        "grocery outlet", "7/11", "oui presse", "observatory"
    ]
    if any(keyword in vendor_lower for keyword in staff_meal_vendors):
        category = "Materials"
        description = "Staff Meal"

    # Hardware and supplies
    elif any(keyword in vendor_lower for keyword in [
        "home depot", "hardware", "amazon", "do it best", "woodstock"
    ]):
        category = "Materials"
        description = "Farm Supplies"

    # Nursery and garden supplies
    elif any(keyword in vendor_lower for keyword in [
        "nursery", "portland nursery", "xera plants"
    ]):
        category = "Materials"
        description = "Farm Supplies"

    # Feed and supplies
    elif any(keyword in vendor_lower for keyword in [
        "wichita feed", "feed", "supplies"
    ]):
        category = "Materials"
        description = "Farm Supplies"

    # Office supplies and services
    elif any(keyword in vendor_lower for keyword in [
        "office depot", "office max", "quickbooks", "fli social ink"
    ]):
        category = "Other"
        description = "Office Supplies"

    # Postal services
    elif any(keyword in vendor_lower for keyword in [
        "usps", "postal", "mail"
    ]):
        category = "Materials"
        description = "Farm Supplies"

    # Testing and quality assurance
    elif any(keyword in vendor_lower for keyword in [
        "matrix sciences", "testing", "quality"
    ]):
        category = "Other"
        description = "Quality Assurance"

    # If notes contain specific information, use that
    if notes and notes.lower() != "none":
        if "meal" in notes.lower():
            category = "Materials"
            description = "Staff Meal"
        elif "supplies" in notes.lower():
            category = "Materials"
            description = "Farm Supplies"

    return category, description


def extract_info_from_image(image_path):
    """Send an image to OpenAI's Vision API and return the extracted info."""
    try:
        with open(image_path, "rb") as img_file:
            image_data = img_file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": ("You are a document parser that extracts "
                                    "structured data from receipt images.")
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": EXTRACTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ],
                    },
                ],
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error extracting info from {image_path}: {e}")
        return None


def parse_extracted_text(extracted_text):
    """Parse the extracted text and return structured data."""
    if not extracted_text:
        return None

    lines = extracted_text.split('\n')
    data = {
        'vendor': 'Unknown',
        'date': None,
        'total': None,
        'category': 'Materials',
        'description': 'Farm Supplies',
        'notes': 'None'
    }

    for line in lines:
        line = line.strip()
        if line.startswith('Vendor:'):
            data['vendor'] = line.replace('Vendor:', '').strip()
        elif line.startswith('Date:'):
            date_str = line.replace('Date:', '').strip()
            data['date'] = parse_date(date_str)
        elif line.startswith('Total:'):
            total_str = line.replace('Total:', '').strip()
            data['total'] = parse_amount(total_str)
        elif line.startswith('Category:'):
            data['category'] = line.replace('Category:', '').strip()
        elif line.startswith('Description:'):
            data['description'] = line.replace('Description:', '').strip()
        elif line.startswith('Notes:'):
            data['notes'] = line.replace('Notes:', '').strip()

    # Determine category and description if not provided
    if (data['category'] == 'Materials' and
            data['description'] == 'Farm Supplies'):
        category, description = determine_category_and_description(
            data['vendor'], data['total'], data['notes']
        )
        data['category'] = category
        data['description'] = description

    return data


def process_receipts_to_csv(folder_path, output_csv):
    """Process all JPEG files in the folder and create a CSV file."""
    # CSV headers based on receipts.csv format with added image filename column
    headers = [
        'LINE ITEM CATEGORY',
        'EXPENSE DESCRIPTION',
        'NAME OF VENDOR\n(if applicable)',
        'DOCUMENTATION TYPE',
        'DATE OF EXPENSE\n(e.g. invoice date)',
        'AMOUNT PAID WITH GRANT FUNDS',
        'SOURCE IMAGE FILE'
    ]

    rows = []

    # Process each JPEG file
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.jpeg', '.jpg')):
            image_path = os.path.join(folder_path, filename)
            print(f"Processing: {filename}")

            try:
                # Extract information from image
                extracted_text = extract_info_from_image(image_path)

                if extracted_text:
                    # Parse the extracted text
                    data = parse_extracted_text(extracted_text)

                    if data:
                        # Format amount for CSV
                        amount_str = ""
                        if data['total'] is not None:
                            amount_str = f"${data['total']:.2f}"

                        # Create row for CSV
                        row = [
                            data['category'],
                            data['description'],
                            data['vendor'],
                            'Receipt',
                            data['date'] or '',
                            amount_str,
                            filename
                        ]

                        rows.append(row)
                        print(f"  Extracted: {data['vendor']} - {amount_str}")
                    else:
                        print("  Failed to parse extracted text")
                else:
                    print("  Failed to extract information from image")

            except Exception as e:
                print(f"  Error processing {filename}: {e}")

    # Write to CSV file
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter='\t')
            writer.writerow(headers)
            writer.writerows(rows)

        print(f"\nSuccessfully created {output_csv} with {len(rows)} entries")

    except Exception as e:
        print(f"Error writing CSV file: {e}")


if __name__ == "__main__":
    # Check if the folder exists
    if not os.path.exists(FOLDER_PATH):
        print(f"Error: Folder '{FOLDER_PATH}' not found")
        exit(1)

    # Process receipts and create CSV
    process_receipts_to_csv(FOLDER_PATH, "expenses.csv")
