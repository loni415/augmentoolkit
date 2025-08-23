#!/usr/bin/env python3
"""
Detailed check for specific RAG processing issues
"""

import os
import glob
import re

def check_specific_issues(filepath):
    """Check for specific issues that commonly break RAG systems"""
    filename = os.path.basename(filepath)
    issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # 1. Check for broken image references
        broken_images = re.findall(r'!\[.*?\]\(.*?\)', content)
        if broken_images:
            issues.append(f"Contains {len(broken_images)} image references - may break if images missing")
            
        # 2. Check for URLs that might be broken
        urls = re.findall(r'https?://[^\s\)]+', content)
        if len(urls) > 20:
            issues.append(f"Contains {len(urls)} URLs - verify accessibility")
            
        # 3. Check for footnote references
        footnotes = re.findall(r'\[\d+\]', content)
        if len(footnotes) > 50:
            issues.append(f"Contains {len(footnotes)} footnote references - may need cleanup")
            
        # 4. Check for citation formats
        citations = re.findall(r'\([A-Za-z]+\s+\d{4}[a-z]?\)', content)
        if len(citations) > 30:
            issues.append(f"Contains {len(citations)} academic citations - may need formatting")
            
        # 5. Check for tables
        table_markers = content.count('|')
        if table_markers > 50:
            issues.append(f"Contains complex tables ({table_markers} pipe characters) - verify formatting")
            
        # 6. Check for code blocks
        code_blocks = len(re.findall(r'```.*?```', content, re.DOTALL))
        if code_blocks > 5:
            issues.append(f"Contains {code_blocks} code blocks - ensure proper formatting")
            
        # 7. Check for mathematical notation
        latex_math = len(re.findall(r'\$.*?\$', content))
        if latex_math > 10:
            issues.append(f"Contains {latex_math} LaTeX math expressions - verify compatibility")
            
        # 8. Check for special formatting
        bold_italic = len(re.findall(r'\*\*\*.*?\*\*\*', content))
        if bold_italic > 20:
            issues.append(f"Heavy use of formatting ({bold_italic} bold-italic) - may affect parsing")
            
        # 9. Check line length issues
        lines = content.split('\n')
        very_long_lines = [i for i, line in enumerate(lines) if len(line) > 500]
        if very_long_lines:
            issues.append(f"Contains very long lines: {len(very_long_lines)} lines > 500 chars")
            
        # 10. Check for metadata blocks
        yaml_blocks = len(re.findall(r'^---\n.*?\n---', content, re.MULTILINE | re.DOTALL))
        if yaml_blocks > 0:
            issues.append(f"Contains {yaml_blocks} YAML metadata blocks - may need extraction")
            
    except Exception as e:
        issues.append(f"Error analyzing file: {str(e)}")
        
    return issues

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_files = glob.glob(os.path.join(script_dir, "*.md"))
    
    print("🔍 Detailed RAG Processing Check\n")
    print("Checking for specific issues that commonly affect RAG systems:\n")
    
    total_issues = 0
    files_with_issues = 0
    
    for filepath in sorted(md_files):
        filename = os.path.basename(filepath)
        issues = check_specific_issues(filepath)
        
        if issues:
            files_with_issues += 1
            total_issues += len(issues)
            print(f"📄 {filename}")
            for issue in issues:
                print(f"  ⚠️  {issue}")
            print()
    
    print("=" * 60)
    print(f"Summary: {files_with_issues}/{len(md_files)} files have specific RAG issues")
    print(f"Total issues found: {total_issues}")
    
    if total_issues > 0:
        print("\n💡 Recommendations:")
        print("• Test RAG processing with a small subset first")
        print("• Consider preprocessing to clean up formatting")
        print("• Verify that image references and URLs are accessible")
        print("• Check if mathematical expressions render correctly")
        print("• Consider splitting files with complex tables or many citations")

if __name__ == "__main__":
    main()