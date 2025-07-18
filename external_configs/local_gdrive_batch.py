import os
import subprocess
import json

# --- START OF USER CONFIGURATION ---

# Add your directory pairs to sync in the list below.
# Each entry should be a dictionary with two keys:
# 'local_dir': The full path to your local folder containing markdown files.
# 'gdrive_url': The full URL of the destination Google Drive folder.

SYNC_DIRECTORIES = [
    {
        "local_dir": "/Users/lukasfiller/Library/CloudStorage/OneDrive-DKIAsia-PacificCenterforSecurityStudies/APCSS_Docs/Contract Work/UVa/data_acq_plan/not_gdocd",
        "gdrive_url": "https://drive.google.com/drive/folders/1Hu9qVAeNIOgqoz2ufTM25Ip7my44Pjg3" #data_acq_plan
    },
    #{
    #    "local_dir": "/Users/lukas/documents/contract_work/UVa",
    #    "gdrive_url": "https://drive.google.com/drive/folders/1gEt0O-OLkJgBQcrmB1MWu0Ajt5aCAMxj"
    #},
    # Add more pairs here if needed, for example:
    # {
    #     "local_dir": "~/Documents/my-notes",
    #     "gdrive_url": "https://drive.google.com/drive/folders/your_folder_id_here"
    # },
]

# --- END OF USER CONFIGURATION ---


def parse_gdrive_url(url):
    """
    Parses a Google Drive folder URL to extract the unique Folder ID.
    Example URL: https://drive.google.com/drive/folders/16qDnKU71mbQ269V-jmyEpYHDqajloVJX
    Returns the ID string or None if parsing fails.
    """
    try:
        # The ID is the last part of the URL path
        folder_id = url.split('/')[-1]
        # A simple check to see if it looks like a valid ID (avoids empty strings)
        if len(folder_id) > 20:
            return folder_id
        else:
            return None
    except Exception:
        return None

def sync_single_directory(local_markdown_dir, gdrive_folder_id):
    """
    Checks for local .md files in a given directory, compares them against
    existing files in the corresponding Google Drive folder, and only uploads
    new files, converting them to Google Docs.
    """
    # Use the root of the remote and specify the folder ID with a flag
    gdrive_remote_root = "gdrive1:"

    print("\nStarting sync and conversion process...")
    
    # NOTE: Your rclone executable path is preserved here.
    rclone_executable_path = "/opt/homebrew/bin/rclone"
    
    print(f"Checking for existing files in Google Drive folder ID: {gdrive_folder_id}...")
    try:
        # Use --drive-root-folder-id to target the specific folder
        list_command = [rclone_executable_path, "lsjson", "--drive-root-folder-id", gdrive_folder_id, gdrive_remote_root]
        result = subprocess.run(list_command, check=True, capture_output=True, text=True, timeout=300)
        remote_files_json = json.loads(result.stdout)
        existing_remote_names = {os.path.splitext(item['Name'])[0] for item in remote_files_json}
        print(f"Found {len(existing_remote_names)} existing files in remote.")
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        print("  Could not list remote files. Assuming folder is empty or new.")
        existing_remote_names = set()

    markdown_files_to_process = [f for f in os.listdir(local_markdown_dir) if f.endswith('.md') and os.path.splitext(f)[0] not in existing_remote_names]
    if not markdown_files_to_process:
        print("No new markdown files found to process in this directory.")
        return

    print(f"Found {len(markdown_files_to_process)} new files to process.")
    new_files_processed = 0
    for i, md_filename in enumerate(markdown_files_to_process):
        base_filename = os.path.splitext(md_filename)[0]

        print(f"\n[{i+1}/{len(markdown_files_to_process)}] Processing: '{md_filename}'")

        new_files_processed += 1
        md_filepath = os.path.join(local_markdown_dir, md_filename)
        html_filename = f"{base_filename}.html"
        html_filepath = os.path.join(local_markdown_dir, html_filename)

        try:
            print("  Converting to HTML with pandoc...")
            subprocess.run(["pandoc", "-s", md_filepath, "-o", html_filepath], check=True, capture_output=True, text=True, timeout=300)
            print("  Conversion successful.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"  Pandoc conversion failed: {e}")
            continue

        try:
            print("  Uploading to Google Drive with rclone...")
            # Use --drive-root-folder-id to specify the upload destination
            rclone_command = [
                rclone_executable_path, "copy",
                "--drive-root-folder-id", gdrive_folder_id,
                "--drive-import-formats", "html",
                "--no-check-dest",
                "--drive-allow-import-name-change",
                html_filepath,
                gdrive_remote_root
            ]
            subprocess.run(rclone_command, check=True, capture_output=True, text=True, timeout=600)
            print(f"  Successfully uploaded '{base_filename}' as a Google Doc.")
        except subprocess.TimeoutExpired:
            print(f"  Rclone upload timed out for '{md_filename}'. Skipping.")
        except subprocess.CalledProcessError as e:
            print(f"  Rclone upload failed: {e.stderr}")
        finally:
            if os.path.exists(html_filepath):
                os.remove(html_filepath)
    
    if new_files_processed == 0:
        print("All local files are already synced for this directory.")

def main():
    """
    Iterates through the predefined directory pairs and syncs each one.
    """
    print("Starting batch sync process...")
    if not SYNC_DIRECTORIES:
        print("Configuration list is empty. Please add directories to sync.")
        return

    for i, pair in enumerate(SYNC_DIRECTORIES):
        local_dir = pair.get("local_dir")
        gdrive_url = pair.get("gdrive_url")

        print(f"\n--- Processing Pair {i+1} of {len(SYNC_DIRECTORIES)} ---")
        print(f"Local: {local_dir}")
        print(f"Remote URL: {gdrive_url}")

        if not local_dir or not gdrive_url:
            print("Error: Incomplete pair information. Both 'local_dir' and 'gdrive_url' are required. Skipping.")
            continue

        # Validate and expand local directory path (e.g., handles '~')
        expanded_local_dir = os.path.expanduser(local_dir.strip().strip("'"))
        if not os.path.isdir(expanded_local_dir):
            print(f"Error: Local directory not found at '{expanded_local_dir}'. Skipping.")
            continue

        # Validate Google Drive URL and extract ID
        gdrive_folder_id = parse_gdrive_url(gdrive_url)
        if not gdrive_folder_id:
            print("Error: Invalid Google Drive URL. Could not extract Folder ID. Skipping.")
            continue
            
        print(f"Validated Local Path: {expanded_local_dir}")
        print(f"Extracted GDrive ID: {gdrive_folder_id}")

        # Call the sync logic for the current pair
        sync_single_directory(expanded_local_dir, gdrive_folder_id)

    print("\n--- Batch sync process complete. ---")


if __name__ == "__main__":
    main()