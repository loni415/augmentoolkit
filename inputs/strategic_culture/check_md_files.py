#!/usr/bin/env python3
"""
Script to check all .md files for potential RAG processing issues
"""

import os
import glob
import re
from collections import defaultdict

def check_file_for_rag_issues(filepath):
    """Check a single file for common RAG processing issues"""
    issues = []
    filename = os.path.basename(filepath)
    
    try:
        # Read file with error handling
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        lines = content.split('\n')
        
        # 1. File size issues
        if len(content) < 100:
            issues.append("CRITICAL: Very short content (< 100 characters)")
        elif len(content) > 1000000:  # 1MB
            issues.append("WARNING: Very large file (> 1MB) - may cause processing issues")
            
        # 2. Encoding issues
        if '�' in content:
            issues.append("CRITICAL: Contains replacement characters (encoding issues)")
            
        # 3. Mixed language content (Chinese + English)
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'\b[A-Za-z]+\b', content))
        
        if chinese_chars > 100 and english_words > 100:
            issues.append(f"WARNING: Mixed Chinese/English content (Chinese: {chinese_chars}, English words: {english_words})")
        elif chinese_chars > len(content) * 0.3:
            issues.append(f"WARNING: Primarily Chinese content ({chinese_chars} Chinese characters)")
            
        # 4. Excessive special characters
        special_chars = len(re.findall(r'[^\w\s\-\.\,\;\:\!\?\(\)\[\]\{\}\'\"\/\\\n\r\t]', content))
        special_ratio = special_chars / len(content) if content else 0
        if special_ratio > 0.15:
            issues.append(f"WARNING: High special character ratio ({special_ratio:.2%}) - may indicate OCR issues")
            
        # 5. Malformed markdown headers
        malformed_headers = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#') and not re.match(r'^#+\s+.+', stripped):
                malformed_headers.append(i+1)
        if malformed_headers:
            issues.append(f"WARNING: Malformed headers at lines: {malformed_headers[:10]}")
            
        # 6. Excessive empty lines
        empty_lines = sum(1 for line in lines if not line.strip())
        if empty_lines > len(lines) * 0.4:
            issues.append(f"WARNING: Excessive empty lines ({empty_lines}/{len(lines)})")
            
        # 7. OCR artifacts detection
        ocr_patterns = [
            (r'[A-Z]{3,}\s+[A-Z]{3,}', 'Multiple consecutive uppercase words'),
            (r'[0-9]+[A-Za-z]+[0-9]+', 'Mixed numbers and letters'),
            (r'[^\w\s]{4,}', 'Long sequences of special characters'),
            (r'\b[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\b', 'Spaced single letters'),
        ]
        
        total_ocr_issues = 0
        for pattern, description in ocr_patterns:
            matches = len(re.findall(pattern, content))
            if matches > 5:
                issues.append(f"WARNING: Potential OCR artifacts - {description} ({matches} instances)")
                total_ocr_issues += matches
                
        # 8. Table formatting issues
        table_lines = [line for line in lines if '|' in line and line.count('|') >= 2]
        if table_lines:
            malformed_tables = 0
            for line in table_lines:
                # Check for consistent pipe count in table rows
                if line.strip().startswith('|') != line.strip().endswith('|'):
                    malformed_tables += 1
            if malformed_tables > len(table_lines) * 0.2:
                issues.append(f"WARNING: Inconsistent table formatting ({malformed_tables}/{len(table_lines)} rows)")
                
        # 9. Incomplete sentences
        sentences = re.split(r'[.!?]+', content)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
        very_short = sum(1 for s in valid_sentences if len(s) < 15)
        if very_short > len(valid_sentences) * 0.3 and len(valid_sentences) > 10:
            issues.append(f"WARNING: Many short sentence fragments ({very_short}/{len(valid_sentences)})")
            
        # 10. Mathematical expressions that might break processing
        math_issues = 0
        math_patterns = [r'\$[^$]*\$', r'\\[a-zA-Z]+\{', r'\\\(.*?\\\)', r'\\\[.*?\\\]']
        for pattern in math_patterns:
            math_issues += len(re.findall(pattern, content))
        if math_issues > 20:
            issues.append(f"INFO: Contains mathematical expressions ({math_issues}) - ensure LaTeX compatibility")
            
    except UnicodeDecodeError:
        issues.append("CRITICAL: File encoding issues - cannot read as UTF-8")
    except Exception as e:
        issues.append(f"CRITICAL: Error reading file - {str(e)}")
        
    return issues

def main():
    """Main analysis function"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_files = glob.glob(os.path.join(script_dir, "*.md"))
    
    print(f"🔍 Analyzing {len(md_files)} .md files for RAG compatibility issues...\n")
    
    all_issues = {}
    critical_count = 0
    warning_count = 0
    
    for filepath in sorted(md_files):
        filename = os.path.basename(filepath)
        issues = check_file_for_rag_issues(filepath)
        
        if issues:
            all_issues[filename] = issues
            critical_issues = [i for i in issues if i.startswith('CRITICAL')]
            warning_issues = [i for i in issues if i.startswith('WARNING')]
            critical_count += len(critical_issues)
            warning_count += len(warning_issues)
            
            print(f"📄 {filename}")
            for issue in issues:
                if issue.startswith('CRITICAL'):
                    print(f"  🔴 {issue}")
                elif issue.startswith('WARNING'):
                    print(f"  🟡 {issue}")
                else:
                    print(f"  ℹ️  {issue}")
            print()
    
    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    if all_issues:
        print(f"Files with issues: {len(all_issues)}/{len(md_files)}")
        print(f"Critical issues: {critical_count}")
        print(f"Warning issues: {warning_count}")
        
        print("\n🔴 CRITICAL ISSUES (must fix):")
        critical_files = []
        for filename, issues in all_issues.items():
            critical_issues = [i for i in issues if i.startswith('CRITICAL')]
            if critical_issues:
                critical_files.append(filename)
                print(f"  • {filename}: {len(critical_issues)} critical issue(s)")
                
        print("\n🟡 WARNING ISSUES (should review):")
        warning_files = []
        for filename, issues in all_issues.items():
            warning_issues = [i for i in issues if i.startswith('WARNING')]
            if warning_issues:
                warning_files.append(filename)
                print(f"  • {filename}: {len(warning_issues)} warning(s)")
                
        print("\n📋 RECOMMENDATIONS:")
        if critical_count > 0:
            print("1. Fix all CRITICAL issues before using files with RAG")
            print("2. Consider re-processing files with encoding issues")
        if warning_count > 0:
            print("3. Review WARNING issues for potential quality improvements")
            print("4. Test RAG performance with mixed-language files")
            print("5. Consider splitting very large files")
            
    else:
        print("✅ No issues found! All files appear RAG-compatible.")
        
    print(f"\nAnalysis complete. Checked {len(md_files)} files.")

if __name__ == "__main__":
    main()