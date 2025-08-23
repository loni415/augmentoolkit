#!/usr/bin/env python3
"""
Comprehensive Markdown Preprocessing Script for RAG
Cleans OCR artifacts, formatting issues, and optimizes for RAG processing
"""

import os
import re
import glob
import shutil
from pathlib import Path
from datetime import datetime

class MarkdownPreprocessor:
    def __init__(self, input_dir, output_dir=None, backup=True):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir / "preprocessed"
        self.backup_dir = self.input_dir / "backup" if backup else None
        self.stats = {
            'files_processed': 0,
            'files_split': 0,
            'ocr_fixes': 0,
            'header_fixes': 0,
            'whitespace_cleaned': 0,
            'long_lines_wrapped': 0
        }
        
    def create_directories(self):
        """Create necessary directories"""
        self.output_dir.mkdir(exist_ok=True)
        if self.backup_dir:
            self.backup_dir.mkdir(exist_ok=True)
            
    def backup_file(self, filepath):
        """Create backup of original file"""
        if self.backup_dir:
            backup_path = self.backup_dir / Path(filepath).name
            shutil.copy2(filepath, backup_path)
            
    def clean_ocr_artifacts(self, text):
        """Clean common OCR artifacts"""
        fixes = 0
        
        # Fix spaced letters (e.g., "T h i s" -> "This")
        spaced_pattern = r'\b([A-Za-z])\s+([A-Za-z])\s+([A-Za-z])\b'
        matches = len(re.findall(spaced_pattern, text))
        text = re.sub(spaced_pattern, r'\1\2\3', text)
        fixes += matches
        
        # Fix more complex spaced patterns
        spaced_pattern2 = r'\b([A-Za-z])\s+([A-Za-z])\s+([A-Za-z])\s+([A-Za-z])\b'
        matches = len(re.findall(spaced_pattern2, text))
        text = re.sub(spaced_pattern2, r'\1\2\3\4', text)
        fixes += matches
        
        # Clean excessive special characters (4+ consecutive)
        special_pattern = r'[^\w\s\-\.\,\;\:\!\?\(\)\[\]\{\}\'\"\/\\]{4,}'
        matches = len(re.findall(special_pattern, text))
        text = re.sub(special_pattern, '---', text)
        fixes += matches
        
        # Fix mixed numbers and letters (common OCR error)
        mixed_pattern = r'\b(\d+)([A-Za-z]+)(\d+)\b'
        def fix_mixed(match):
            return f"{match.group(1)} {match.group(2)} {match.group(3)}"
        matches = len(re.findall(mixed_pattern, text))
        text = re.sub(mixed_pattern, fix_mixed, text)
        fixes += matches
        
        self.stats['ocr_fixes'] += fixes
        return text
        
    def fix_headers(self, text):
        """Fix malformed markdown headers"""
        fixes = 0
        
        # Fix headers without space after #
        pattern = r'^(#+)([^\s#])'
        matches = len(re.findall(pattern, text, re.MULTILINE))
        text = re.sub(pattern, r'\1 \2', text, flags=re.MULTILINE)
        fixes += matches
        
        self.stats['header_fixes'] += fixes
        return text
        
    def clean_whitespace(self, text):
        """Clean excessive whitespace and empty lines"""
        fixes = 0
        
        # Remove trailing whitespace
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
        
        # Reduce multiple empty lines to maximum 2
        pattern = r'\n{3,}'
        matches = len(re.findall(pattern, text))
        text = re.sub(pattern, '\n\n', text)
        fixes += matches
        
        # Clean up tabs
        text = text.replace('\t', '    ')
        
        self.stats['whitespace_cleaned'] += fixes
        return text
        
    def wrap_long_lines(self, text, max_length=120):
        """Wrap very long lines while preserving markdown structure"""
        lines = text.split('\n')
        wrapped_lines = []
        fixes = 0
        
        for line in lines:
            if len(line) <= max_length:
                wrapped_lines.append(line)
                continue
                
            # Don't wrap headers, code blocks, or tables
            if (line.strip().startswith('#') or 
                line.strip().startswith('```') or 
                '|' in line):
                wrapped_lines.append(line)
                continue
                
            # Wrap long paragraphs
            words = line.split()
            current_line = ""
            
            for word in words:
                if len(current_line + " " + word) <= max_length:
                    current_line += " " + word if current_line else word
                else:
                    if current_line:
                        wrapped_lines.append(current_line)
                    current_line = word
                    
            if current_line:
                wrapped_lines.append(current_line)
                
            fixes += 1
            
        self.stats['long_lines_wrapped'] += fixes
        return '\n'.join(wrapped_lines)
        
    def clean_image_references(self, text):
        """Clean up image references"""
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def fix_image(match):
            alt_text = match.group(1)
            img_path = match.group(2)
            
            # If image path looks broken, convert to text
            if not os.path.exists(img_path) and not img_path.startswith('http'):
                return f"[Image: {alt_text if alt_text else 'Missing image'}]"
            
            return match.group(0)
        
        return re.sub(img_pattern, fix_image, text)
        
    def split_large_file(self, filepath, content, max_size=500000):
        """Split large files into smaller chunks"""
        if len(content) <= max_size:
            return [content]
            
        # Split by major headers
        sections = re.split(r'\n(?=# [^#])', content)
        
        chunks = []
        current_chunk = ""
        
        for section in sections:
            if len(current_chunk + section) > max_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = section
            else:
                current_chunk += "\n" + section if current_chunk else section
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        self.stats['files_split'] += len(chunks) - 1 if len(chunks) > 1 else 0
        return chunks
        
    def process_file(self, filepath):
        """Process a single markdown file"""
        print(f"Processing: {Path(filepath).name}")
        
        # Backup original
        self.backup_file(filepath)
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            original_length = len(content)
            
            # Apply cleaning functions
            content = self.clean_ocr_artifacts(content)
            content = self.fix_headers(content)
            content = self.clean_whitespace(content)
            content = self.wrap_long_lines(content)
            content = self.clean_image_references(content)
            
            # Split if too large
            chunks = self.split_large_file(filepath, content)
            
            # Save processed file(s)
            base_name = Path(filepath).stem
            
            if len(chunks) == 1:
                # Single file
                output_path = self.output_dir / f"{base_name}_cleaned.md"
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(chunks[0])
            else:
                # Multiple chunks
                for i, chunk in enumerate(chunks):
                    output_path = self.output_dir / f"{base_name}_part{i+1:02d}_cleaned.md"
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(chunk)
                        
            processed_length = sum(len(chunk) for chunk in chunks)
            reduction = ((original_length - processed_length) / original_length * 100)
            
            print(f"  ✅ Size reduction: {reduction:.1f}%")
            if len(chunks) > 1:
                print(f"  📄 Split into {len(chunks)} files")
                
            self.stats['files_processed'] += 1
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            
    def process_directory(self):
        """Process all markdown files in directory"""
        print(f"🔍 Processing markdown files in: {self.input_dir}")
        print(f"📁 Output directory: {self.output_dir}")
        
        self.create_directories()
        
        md_files = list(self.input_dir.glob("*.md"))
        if not md_files:
            print("❌ No .md files found!")
            return
            
        print(f"Found {len(md_files)} files to process\n")
        
        for filepath in sorted(md_files):
            self.process_file(filepath)
            
        self.print_summary()
        
    def print_summary(self):
        """Print processing summary"""
        print("\n" + "="*60)
        print("📊 PREPROCESSING SUMMARY")
        print("="*60)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files split: {self.stats['files_split']}")
        print(f"OCR artifacts fixed: {self.stats['ocr_fixes']}")
        print(f"Headers fixed: {self.stats['header_fixes']}")
        print(f"Whitespace cleaned: {self.stats['whitespace_cleaned']}")
        print(f"Long lines wrapped: {self.stats['long_lines_wrapped']}")
        
        print(f"\n✅ Processed files saved to: {self.output_dir}")
        if self.backup_dir:
            print(f"📋 Backups saved to: {self.backup_dir}")

if __name__ == "__main__":
    # Run with current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    preprocessor = MarkdownPreprocessor(input_dir=current_dir)
    preprocessor.process_directory()
