#!/usr/bin/env python3
"""Unified course content upload script with CLI."""

import sys
import os
import argparse

# Add the responses-api-server directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'responses-api-server'))

from llmproxy import pdf_upload, text_upload


CONTENT_DIRECTORIES = {
    'admin': 'admin_docs',
    'hw': 'hw_proj_specs',
    'projects': 'hw_proj_specs',
    'labs': 'lab_specs',
}


def upload_pdf(pdf_path: str, session_id: str = 'GenericSession', strategy: str = 'smart'):
    """Upload a single PDF file"""
    if not os.path.exists(pdf_path):
        print(f" File not found: {pdf_path}")
        return False
    
    print(f" Uploading {os.path.basename(pdf_path)}...")
    try:
        response = pdf_upload(
            path=pdf_path,
            session_id=session_id,
            strategy=strategy
        )
        print(f" Upload successful: {response}")
        return True
    except Exception as e:
        print(f" Upload failed: {e}")
        return False


def upload_text(text_path: str, description: str = None, session_id: str = 'GenericSession', strategy: str = 'smart'):
    """Upload a single text file"""
    if not os.path.exists(text_path):
        print(f" File not found: {text_path}")
        return False
    
    try:
        with open(text_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
    except Exception as e:
        print(f" Error reading file: {e}")
        return False
    
    if not description:
        description = f"CS 15 course content from {os.path.basename(text_path)}"
    
    print(f" Uploading {os.path.basename(text_path)}...")
    try:
        response = text_upload(
            text=text_content,
            strategy=strategy,
            description=description,
            session_id=session_id
        )
        print(f" Upload successful: {response}")
        return True
    except Exception as e:
        print(f" Upload failed: {e}")
        return False


def upload_directory(directory: str, file_pattern: str = None, session_id: str = 'GenericSession', strategy: str = 'smart'):
    """Upload all files from a directory"""
    if not os.path.exists(directory):
        print(f" Directory not found: {directory}")
        return
    
    files = os.listdir(directory)
    
    # Filter by pattern if provided
    if file_pattern:
        files = [f for f in files if file_pattern.lower() in f.lower()]
    
    # Separate PDFs and text files
    pdf_files = [f for f in files if f.lower().endswith('.pdf')]
    txt_files = [f for f in files if f.lower().endswith('.txt')]
    
    total = len(pdf_files) + len(txt_files)
    if total == 0:
        print(f"  No files found in {directory}")
        return
    
    print(f" Found {len(pdf_files)} PDFs and {len(txt_files)} text files in {directory}")
    
    success_count = 0
    
    # Upload PDFs
    for filename in pdf_files:
        pdf_path = os.path.join(directory, filename)
        if upload_pdf(pdf_path, session_id, strategy):
            success_count += 1
    
    # Upload text files
    for filename in txt_files:
        text_path = os.path.join(directory, filename)
        if upload_text(text_path, session_id=session_id, strategy=strategy):
            success_count += 1
    
    print(f"\n Uploaded {success_count}/{total} files successfully")


def upload_all_content(session_id: str = 'GenericSession', strategy: str = 'smart'):
    """Upload all course content from all directories"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    print(" Uploading all CS 15 course content...")
    print("=" * 60)
    
    total_success = 0
    total_files = 0
    
    for content_type, dirname in CONTENT_DIRECTORIES.items():
        dir_path = os.path.join(base_path, dirname)
        
        if not os.path.exists(dir_path):
            print(f"  Skipping {dirname} (not found)")
            continue
        
        print(f"\n Processing {content_type} ({dirname})...")
        print("-" * 60)
        
        files = [f for f in os.listdir(dir_path) if f.lower().endswith(('.pdf', '.txt'))]
        total_files += len(files)
        
        for filename in files:
            file_path = os.path.join(dir_path, filename)
            
            if filename.lower().endswith('.pdf'):
                if upload_pdf(file_path, session_id, strategy):
                    total_success += 1
            elif filename.lower().endswith('.txt'):
                if upload_text(file_path, session_id=session_id, strategy=strategy):
                    total_success += 1
    
    print("\n" + "=" * 60)
    print(f" Upload complete: {total_success}/{total_files} files uploaded successfully")


def upload_specific_category(category: str, session_id: str = 'GenericSession', strategy: str = 'smart'):
    """Upload all files from a specific category"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    if category not in CONTENT_DIRECTORIES:
        print(f" Unknown category: {category}")
        print(f"Available categories: {', '.join(CONTENT_DIRECTORIES.keys())}")
        return
    
    dirname = CONTENT_DIRECTORIES[category]
    dir_path = os.path.join(base_path, dirname)
    
    print(f" Uploading {category} content from {dirname}...")
    upload_directory(dir_path, session_id=session_id, strategy=strategy)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Unified CS 15 Course Content Upload Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload a single PDF
  python upload_content.py file hw_proj_specs/proj_gerp.pdf
  
  # Upload all files from a directory
  python upload_content.py dir lab_specs
  
  # Upload all files from a specific category
  python upload_content.py category labs
  
  # Upload all content
  python upload_content.py all
  
  # Upload with custom strategy
  python upload_content.py file myfile.pdf --strategy fixed
  
Available categories: admin, hw, projects, labs
        """
    )
    
    parser.add_argument('command', choices=['file', 'dir', 'category', 'all'],
                       help='Upload command: file (single file), dir (directory), category (predefined), all (everything)')
    parser.add_argument('path', nargs='?', default=None,
                       help='File path, directory path, or category name')
    parser.add_argument('--session-id', default='GenericSession',
                       help='Session ID for upload (default: GenericSession)')
    parser.add_argument('--strategy', default='smart', choices=['smart', 'fixed'],
                       help='Upload strategy (default: smart)')
    parser.add_argument('--pattern', default=None,
                       help='Filter files by pattern (e.g., "metrosim")')
    parser.add_argument('--description', default=None,
                       help='Description for text file uploads')
    
    args = parser.parse_args()
    
    # Resolve relative paths to absolute paths
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    try:
        if args.command == 'file':
            if not args.path:
                print(" Error: file path required")
                parser.print_help()
                return
            
            # Resolve file path
            if not os.path.isabs(args.path):
                file_path = os.path.join(base_path, args.path)
            else:
                file_path = args.path
            
            # Determine file type and upload
            if file_path.lower().endswith('.pdf'):
                upload_pdf(file_path, args.session_id, args.strategy)
            elif file_path.lower().endswith('.txt'):
                upload_text(file_path, args.description, args.session_id, args.strategy)
            else:
                print(" Unsupported file type. Only .pdf and .txt files are supported.")
        
        elif args.command == 'dir':
            if not args.path:
                print(" Error: directory path required")
                parser.print_help()
                return
            
            # Resolve directory path
            if not os.path.isabs(args.path):
                dir_path = os.path.join(base_path, args.path)
            else:
                dir_path = args.path
            
            upload_directory(dir_path, args.pattern, args.session_id, args.strategy)
        
        elif args.command == 'category':
            if not args.path:
                print(" Error: category name required")
                print(f"Available categories: {', '.join(CONTENT_DIRECTORIES.keys())}")
                return
            
            upload_specific_category(args.path, args.session_id, args.strategy)
        
        elif args.command == 'all':
            upload_all_content(args.session_id, args.strategy)
        
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # No arguments provided, show help
        main()
    else:
        main()

