import os
from openai import OpenAI
import base64
from datetime import datetime
import shutil
import re
from dotenv import load_dotenv
import fitz  # PyMuPDF for PDF processing
import csv

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
FOLDER_PATH = "receipts"  # change to your actual folder path

# Define the prompt for receipt extraction
EXTRACTION_PROMPT = (
    "Extract the following from this receipt image:\n"
    "- Vendor/store name (the business that issued the receipt)\n"
    "- Total cost (currency and amount)\n"
    "- Date of purchase\n"
    "- Any handwritten notes or markings\n\n"
    "Format the result as:\n"
    "Vendor: <vendor/store name>\nDate: <date>\nTotal: <amount>\n"
    "Notes: <handwritten notes or 'None'>"
)


def get_fiscal_quarter(date_str: str) -> str:
    """Determine the fiscal quarter based on the date string."""
    try:
        # Parse the date string - handle common formats
        date_formats = [
            "%B %d, %Y",  # May 29, 2025
            "%b %d, %Y",  # May 29, 2025
            "%m/%d/%Y",   # 05/29/2025
            "%Y-%m-%d",   # 2025-05-29
            "%d/%m/%Y",   # 29/05/2025
        ]

        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                break
            except ValueError:
                continue

        if parsed_date is None:
            return "Unknown"

        month = parsed_date.month

        if month in [1, 2, 3]:
            return "Q1"
        elif month in [4, 5, 6]:
            return "Q2"
        elif month in [7, 8, 9]:
            return "Q3"
        elif month in [10, 11, 12]:
            return "Q4"
        else:
            return "Unknown"

    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return "Unknown"


def parse_date_for_filename(date_str: str) -> tuple:
    """Parse date string and return month and year for filename."""
    try:
        # Parse the date string - handle common formats
        date_formats = [
            "%B %d, %Y",  # May 29, 2025
            "%b %d, %Y",  # May 29, 2025
            "%m/%d/%Y",   # 05/29/2025
            "%Y-%m-%d",   # 2025-05-29
            "%d/%m/%Y",   # 29/05/2025
        ]

        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                break
            except ValueError:
                continue

        if parsed_date is None:
            return "08", "1619"  # Default fallback

        return f"{parsed_date.month:02d}", str(parsed_date.year)

    except Exception as e:
        print(f"Error parsing date '{date_str}' for filename: {e}")
        return "01", "2025"  # Default fallback


def sanitize_vendor_name(vendor_name: str) -> str:
    """Sanitize vendor name for use in filename."""
    # Remove common prefixes and clean up the name
    vendor = vendor_name.strip()

    # Remove common business suffixes
    suffixes_to_remove = [' Inc', ' LLC', ' Ltd',
                          ' Corp', ' Corporation', ' Company', ' Co']
    for suffix in suffixes_to_remove:
        if vendor.endswith(suffix):
            vendor = vendor[:-len(suffix)]

    # Replace spaces and special characters with hyphens
    # Remove special chars except hyphens
    vendor = re.sub(r'[^\w\s-]', '', vendor)
    # Replace spaces and multiple hyphens with single hyphen
    vendor = re.sub(r'[-\s]+', '-', vendor)
    # Remove leading/trailing hyphens
    vendor = vendor.strip('-')

    # Limit length and ensure it's not empty
    if not vendor:
        vendor = "Unknown-Vendor"
    elif len(vendor) > 50:
        vendor = vendor[:50].rstrip('-')

    return vendor


def create_renamed_copy(file_path: str, vendor: str, fiscal_quarter: str,
                        date_str: str) -> str:
    """Create a copy of the document with the new naming template in a renamed subfolder."""
    try:
        # Parse date for filename
        month, year = parse_date_for_filename(date_str)

        # Sanitize vendor name
        sanitized_vendor = sanitize_vendor_name(vendor)

        # Create new filename
        file_extension = os.path.splitext(file_path)[1].lower()
        new_filename = (f"PCEF-{fiscal_quarter}-BFF-{sanitized_vendor}-{month}-"
                        f"{year}{file_extension}")

        # Create renamed subfolder path
        original_dir = os.path.dirname(file_path)
        renamed_dir = os.path.join(original_dir, "renamed")

        # Create the renamed subfolder if it doesn't exist
        os.makedirs(renamed_dir, exist_ok=True)

        # Create the new file path in the renamed subfolder
        new_file_path = os.path.join(renamed_dir, new_filename)

        # Check if file already exists and add counter if needed
        counter = 1
        original_new_file_path = new_file_path
        while os.path.exists(new_file_path):
            name_without_ext = os.path.splitext(original_new_file_path)[0]
            ext = os.path.splitext(original_new_file_path)[1]
            new_file_path = (f"{name_without_ext}-{counter}{ext}")
            counter += 1

        # Copy the file to the renamed subfolder
        shutil.copy2(file_path, new_file_path)
        return new_file_path

    except Exception as e:
        print(f"Error creating renamed copy: {e}")
        return None


def extract_info_from_document(file_path: str) -> str:
    """Send a document (image or PDF) to OpenAI's Vision API and return the extracted info."""
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext in ['.pdf']:
        # Handle PDF files
        return extract_info_from_pdf(file_path)
    elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
        # Handle image files
        return extract_info_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")


def extract_info_from_image(image_path: str) -> str:
    """Send an image to OpenAI's Vision API and return the extracted info."""
    with open(image_path, "rb") as img_file:
        image_data = img_file.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')

        # Determine MIME type based on file extension
        file_ext = os.path.splitext(image_path)[1].lower()
        if file_ext in ['.jpg', '.jpeg']:
            mime_type = "image/jpeg"
        elif file_ext == '.png':
            mime_type = "image/png"
        elif file_ext == '.gif':
            mime_type = "image/gif"
        elif file_ext == '.bmp':
            mime_type = "image/bmp"
        elif file_ext == '.tiff':
            mime_type = "image/tiff"
        else:
            mime_type = "image/jpeg"  # Default fallback

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": ("You are a document parser that extracts "
                                "structured data from images.")
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (f"data:{mime_type};base64,"
                                        f"{base64_image}")
                            }
                        }
                    ],
                },
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()


def extract_info_from_pdf(pdf_path: str) -> str:
    """Send a PDF to OpenAI's Vision API and return the extracted info."""
    try:
        # Open PDF and get first page
        pdf_document = fitz.open(pdf_path)
        if len(pdf_document) == 0:
            raise ValueError("PDF file is empty or corrupted")

        # Convert first page to image
        page = pdf_document[0]  # Process first page
        # 2x zoom for better quality
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        # Convert to PNG bytes
        png_bytes = pix.tobytes("png")

        # Encode to base64
        base64_image = base64.b64encode(png_bytes).decode('utf-8')

        # Close the PDF document
        pdf_document.close()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": ("You are a document parser that extracts "
                                "structured data from PDF documents.")
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ],
                },
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        raise Exception(f"Error processing PDF {pdf_path}: {e}")


def process_receipts(folder: str):
    """Process all supported document files in the folder and create corresponding .txt summaries."""
    supported_extensions = ['.jpg', '.jpeg',
                            '.png', '.gif', '.bmp', '.tiff', '.pdf']

    # Create renamed subfolder at the beginning
    renamed_dir = os.path.join(folder, "renamed")
    os.makedirs(renamed_dir, exist_ok=True)
    print(f"Created/using renamed subfolder: {renamed_dir}")

    # Prepare CSV data
    csv_data = []
    csv_headers = ['Original Filename',
                   'Renamed Filename', 'Metadata Filename']

    for filename in os.listdir(folder):
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in supported_extensions:
            file_path = os.path.join(folder, filename)
            print(f"Processing: {file_path}")

            # Initialize CSV row data
            csv_row = {
                'Original Filename': filename,
                'Renamed Filename': '',
                'Metadata Filename': ''
            }

            try:
                extracted_text = extract_info_from_document(file_path)

                # Parse the extracted text to add fiscal quarter
                lines = extracted_text.split('\n')
                date_line = None
                vendor_line = None
                total_line = None
                notes_line = None

                for line in lines:
                    if line.startswith('Date:'):
                        date_line = line
                    elif line.startswith('Vendor:'):
                        vendor_line = line
                    elif line.startswith('Total:'):
                        total_line = line
                    elif line.startswith('Notes:'):
                        notes_line = line

                # Extract date for fiscal quarter calculation
                if date_line:
                    date_str = date_line.replace('Date:', '').strip()
                    fiscal_quarter = get_fiscal_quarter(date_str)
                else:
                    fiscal_quarter = "Unknown"

                # Extract vendor name
                vendor_name = "Unknown-Vendor"
                if vendor_line:
                    vendor_name = vendor_line.replace('Vendor:', '').strip()

                # Reconstruct the output with fiscal quarter
                output_lines = []
                if vendor_line:
                    output_lines.append(vendor_line)
                if date_line:
                    output_lines.append(date_line)
                output_lines.append(f"Fiscal Quarter: {fiscal_quarter}")
                if total_line:
                    output_lines.append(total_line)
                if notes_line:
                    output_lines.append(notes_line)

                # If parsing failed, use original extracted text and add fiscal quarter
                if not output_lines:
                    output_lines = lines
                    if date_line:
                        date_str = date_line.replace('Date:', '').strip()
                        fiscal_quarter = get_fiscal_quarter(date_str)
                        # Insert fiscal quarter after date
                        for i, line in enumerate(output_lines):
                            if line.startswith('Date:'):
                                output_lines.insert(
                                    i + 1, f"Fiscal Quarter: {fiscal_quarter}")
                                break

                final_output = '\n'.join(output_lines)

                txt_path = os.path.splitext(file_path)[0] + ".txt"
                metadata_filename = os.path.basename(txt_path)
                with open(txt_path, "w") as txt_file:
                    txt_file.write(final_output)
                print(f"Saved extracted data to {txt_path}")

                # Update CSV row with metadata filename
                csv_row['Metadata Filename'] = metadata_filename

                # Create renamed copy of the document
                if date_line:
                    date_str = date_line.replace('Date:', '').strip()
                    new_file_path = create_renamed_copy(
                        file_path, vendor_name, fiscal_quarter, date_str)
                    if new_file_path:
                        renamed_filename = os.path.basename(new_file_path)
                        print(f"Created renamed copy: {renamed_filename}")
                        # Update CSV row with renamed filename
                        csv_row['Renamed Filename'] = renamed_filename
                    else:
                        print("Failed to create renamed copy")
                        csv_row['Renamed Filename'] = 'Failed'
                else:
                    print("No date found, skipping renamed copy creation")
                    csv_row['Renamed Filename'] = 'No Date'

            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                csv_row['Renamed Filename'] = 'Error'
                csv_row['Metadata Filename'] = 'Error'

            # Add the row to CSV data
            csv_data.append(csv_row)

    # Write CSV file
    csv_filename = os.path.join(folder, "receipts_processing_summary.csv")
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(csv_data)

    print(f"\nCSV summary created: {csv_filename}")
    print(f"Processed {len(csv_data)} files")


if __name__ == "__main__":
    process_receipts(FOLDER_PATH)
