#!/usr/bin/env python3
"""
Helper script to set up environment variables for the BFF PCEF Expense
Reporter. This script will create a .env file with the required
environment variables.
"""

import os
import sys


def create_env_file():
    """Create a .env file with the required environment variables."""
    env_file = ".env"

    if os.path.exists(env_file):
        print(f"Warning: {env_file} already exists.")
        response = input(
            "Do you want to overwrite it? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled.")
            return False

    # Get API key from user
    print("Please enter your OpenAI API key:")
    api_key = input("OPEN_API_DEV_KEY: ").strip()

    if not api_key:
        print("Error: API key cannot be empty.")
        return False

    # Write to .env file
    try:
        with open(env_file, 'w') as f:
            f.write(f"OPEN_API_DEV_KEY={api_key}\n")

        print(f"\n✅ Successfully created {env_file}")
        print("⚠️  Remember: Never commit this file to version control!")
        print("   It's already added to .gitignore for safety.")

        return True

    except Exception as e:
        print(f"Error creating {env_file}: {e}")
        return False


def main():
    """Main function."""
    print("BFF PCEF Expense Reporter - Environment Setup")
    print("=" * 50)

    success = create_env_file()

    if success:
        print("\n🎉 Setup complete! You can now run the expense processing scripts.")
        print("\nNext steps:")
        print("1. Activate your virtual environment: source venv/bin/activate")
        print("2. Run: python parse_receipts_to_csv.py")
    else:
        print("\n❌ Setup failed. Please try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
