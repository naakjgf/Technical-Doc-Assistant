# backend/github_loader.py

import os
import shutil
from git import Repo
from pathlib import Path
from typing import List

# Define which file extensions we want to process
ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".java", ".md", ".txt"}

def load_github_repo(repo_url: str, local_path: str = "temp_repo") -> List[dict]:
    """
    Clones a GitHub repository, extracts content, and cleans up.
    """
    print(f"--- GITHUB LOADER START for URL: {repo_url} ---", flush=True)
    
    print(f"Checking if temporary path '{local_path}' exists...", flush=True)
    if os.path.exists(local_path):
        print(f"Temporary path '{local_path}' exists. Removing it.", flush=True)
        shutil.rmtree(local_path)
    
    try:
        print(f"Attempting to clone repository from {repo_url} with depth=1...", flush=True)
        Repo.clone_from(repo_url, local_path, depth=1)
        print("--- CLONE SUCCEEDED ---", flush=True)
        
        documents = []
        repo_path = Path(local_path)
        
        print("Starting to iterate through files in the cloned repository...", flush=True)
        file_count = 0
        for file_path in repo_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ALLOWED_EXTENSIONS:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    relative_path = str(file_path.relative_to(repo_path))
                    documents.append({"source": relative_path, "content": content})
                    file_count += 1
                except Exception as e:
                    print(f"ERROR reading file {file_path}: {e}", flush=True)
        
        print(f"Finished iterating. Found and read {file_count} files.", flush=True)
        print("--- GITHUB LOADER RETURNING DOCUMENTS ---", flush=True)
        return documents

    except Exception as e:
        print(f"--- FATAL ERROR IN GITHUB LOADER (during clone or processing) ---", flush=True)
        print(f"Exception Type: {type(e).__name__}", flush=True)
        print(f"Exception Details: {e}", flush=True)
        return []
    finally:
        print("--- GITHUB LOADER FINALLY BLOCK ---", flush=True)
        if os.path.exists(local_path):
            print(f"Cleaning up temporary directory: {local_path}", flush=True)
            shutil.rmtree(local_path)
