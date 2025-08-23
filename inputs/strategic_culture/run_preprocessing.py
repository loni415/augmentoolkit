#!/usr/bin/env python3
"""
Simple script to run the markdown preprocessing
"""

import os
from preprocess_md_files import MarkdownPreprocessor

def main():
    # Get current directory (where the .md files are)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("🚀 Starting Markdown Preprocessing for RAG")
    print("=" * 50)
    
    # Create preprocessor
    preprocessor = MarkdownPreprocessor(
        input_dir=current_dir,
        output_dir=os.path.join(current_dir, "preprocessed"),
        backup=True
    )
    
    # Run preprocessing
    preprocessor.process_directory()
    
    print("\n🎉 Preprocessing complete!")
    print("\nNext steps:")
    print("1. Check the 'preprocessed' folder for cleaned files")
    print("2. Review the 'backup' folder for originals")
    print("3. Test RAG with the cleaned files")

if __name__ == "__main__":
    main()
