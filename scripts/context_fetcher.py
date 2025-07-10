import os
import subprocess
import json
import logging

logging.basicConfig(level=logging.INFO, filename='cagent.log')

def fetch_context():
    try:
        issue_title = os.getenv("ISSUE_TITLE")
        issue_body = os.getenv("ISSUE_BODY")
        issue_labels = os.getenv("ISSUE_LABELS").split(",")

        if not issue_title or not issue_body:
            logging.error("Missing issue title or body")
            return

        # Use Gemini CLI to fetch relevant files
        gemini_query = f"Find files related to: {issue_title}\n{issue_body}"
        result = subprocess.run(
            ["gemini-cli", "search", "--query", gemini_query, "--repo", os.getenv("GITHUB_REPOSITORY")],
            capture_output=True, text=True
        )
        
        # Validate and parse output
        try:
            files = json.loads(result.stdout).get("files", [])
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON from Gemini CLI: {result.stdout}")
            files = []
            
        if not files:
            logging.warning("No relevant files found")
            files = []  # Ensure empty list for downstream processing
            
        # Store context in a temporary file
        with open("context.json", "w") as f:
            json.dump({"files": files, "issue_title": issue_title, "issue_body": issue_body, "labels": issue_labels}, f)
        logging.info(f"Fetched {len(files)} files for issue: {issue_title}")
        
    except Exception as e:
        logging.error(f"Error fetching context: {str(e)}")
        with open("context.json", "w") as f:
            json.dump({"files": [], "issue_title": issue_title or "", "issue_body": issue_body or "", "labels": issue_labels}, f)

if __name__ == "__main__":
    fetch_context()