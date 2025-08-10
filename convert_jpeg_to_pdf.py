import os
import shutil
from PIL import Image
import sys


def convert_images_to_pdfs():
    """Convert all JPEG images from raws folder to PDF files in published folder."""

    # Define source and destination folders
    source_folder = "raws"
    destination_folder = "published"

    # Check if source folder exists
    if not os.path.exists(source_folder):
        print(f"Error: Source folder '{source_folder}' not found")
        return False

    # Create destination folder if it doesn't exist
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
        print(f"Created destination folder: {destination_folder}")

    # Get all JPEG files from source folder
    jpeg_files = []
    for filename in os.listdir(source_folder):
        if filename.lower().endswith(('.jpeg', '.jpg')):
            jpeg_files.append(filename)

    if not jpeg_files:
        print(f"No JPEG files found in '{source_folder}' folder")
        return False

    print(f"Found {len(jpeg_files)} JPEG files to convert to PDF")

    # Process each JPEG file
    successful_conversions = 0
    failed_conversions = 0

    for filename in jpeg_files:
        source_path = os.path.join(source_folder, filename)

        # Create PDF filename (replace .jpg/.jpeg with .pdf)
        base_name = os.path.splitext(filename)[0]
        pdf_filename = f"{base_name}.pdf"
        destination_path = os.path.join(destination_folder, pdf_filename)

        try:
            # Open and process the image
            with Image.open(source_path) as img:
                # Convert to RGB if necessary (in case of RGBA or other formats)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Save as PDF
                img.save(destination_path, 'PDF', resolution=100.0)

            print("✓ Converted: " + filename + " → " + pdf_filename)
            successful_conversions += 1

        except Exception as e:
            print(f"✗ Failed to convert {filename}: {e}")
            failed_conversions += 1

    # Summary
    print("\nConversion Summary:")
    print(f"  Successful: {successful_conversions}")
    print(f"  Failed: {failed_conversions}")
    print(f"  Total processed: {len(jpeg_files)}")

    if successful_conversions > 0:
        print(f"\nPDFs saved to: {destination_folder}/")

    return successful_conversions > 0


def copy_images_to_published():
    """Simple copy all JPEG images from raws folder to published folder."""

    # Define source and destination folders
    source_folder = "raws"
    destination_folder = "published"

    # Check if source folder exists
    if not os.path.exists(source_folder):
        print(f"Error: Source folder '{source_folder}' not found")
        return False

    # Create destination folder if it doesn't exist
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
        print(f"Created destination folder: {destination_folder}")

    # Get all JPEG files from source folder
    jpeg_files = []
    for filename in os.listdir(source_folder):
        if filename.lower().endswith(('.jpeg', '.jpg')):
            jpeg_files.append(filename)

    if not jpeg_files:
        print(f"No JPEG files found in '{source_folder}' folder")
        return False

    print(f"Found {len(jpeg_files)} JPEG files to copy")

    # Copy each JPEG file
    successful_copies = 0
    failed_copies = 0

    for filename in jpeg_files:
        source_path = os.path.join(source_folder, filename)
        destination_path = os.path.join(destination_folder, filename)

        try:
            # Copy the file
            shutil.copy2(source_path, destination_path)
            print("✓ Copied: " + filename)
            successful_copies += 1

        except Exception as e:
            print(f"✗ Failed to copy {filename}: {e}")
            failed_copies += 1

    # Summary
    print("\nCopy Summary:")
    print(f"  Successful: {successful_copies}")
    print(f"  Failed: {failed_copies}")
    print(f"  Total processed: {len(jpeg_files)}")

    if successful_copies > 0:
        print(f"\nImages copied to: {destination_folder}/")

    return successful_copies > 0


if __name__ == "__main__":
    print("JPEG to PDF Converter")
    print("====================")

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--copy":
        print("Mode: Simple copy images")
        success = copy_images_to_published()
    else:
        print("Mode: Convert JPEG to PDF (use --copy for simple copy)")
        success = convert_images_to_pdfs()

    if success:
        print("\n✅ Processing completed successfully!")
    else:
        print("\n❌ Processing failed or no files found")
        sys.exit(1)
