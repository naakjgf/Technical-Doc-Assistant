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
    Clones a GitHub repository to a local path, extracts content from allowed
    file types, and then cleans up the cloned directory.

    Args:
        repo_url: The URL of the GitHub repository.
        local_path: The local directory to clone the repo into.

    Returns:
        A list of dictionaries, where each dictionary contains the 'source'
        (file path) and 'content' of a file.
    """
    if os.path.exists(local_path):
        shutil.rmtree(local_path)  # Clean up previous clones

    try:
        print(f"Cloning repository from {repo_url}...")
        Repo.clone_from(repo_url, local_path, depth=1)
        print("Repository cloned successfully.")
        
        documents = []
        repo_path = Path(local_path)
        
        for file_path in repo_path.rglob("*"): # rglob scans recursively
            if file_path.is_file() and file_path.suffix in ALLOWED_EXTENSIONS:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # We store the relative path to keep the context of the file's location
                    relative_path = str(file_path.relative_to(repo_path))
                    documents.append({"source": relative_path, "content": content})
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    
        return documents

    except Exception as e:
        print(f"An error occurred during repository cloning or processing: {e}")
        return []
    finally:
        # Crucially, always clean up the directory afterwards
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
        print(f"Cleaned up temporary directory: {local_path}")
