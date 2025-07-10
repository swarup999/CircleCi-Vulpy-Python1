import os
import re
import json
from github import Github
import logging

logging.basicConfig(level=logging.INFO, filename='cagent.log')

def parse_comment():
    try:
        comment = os.getenv("GITHUB_EVENT_COMMENT_BODY")
        if not comment:
            logging.error("No comment body found in environment")
            print("::set-output name=triggered::false")
            return

        # Check for trigger phrases
        trigger_phrases = [r"@cagent pls fix it", r"@cagent pls create this feature"]
        triggered = any(re.search(phrase, comment, re.IGNORECASE) for phrase in trigger_phrases)
        
        if triggered:
            g = Github(os.getenv("GITHUB_TOKEN"))
            repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
            issue_number = os.getenv("GITHUB_EVENT_ISSUE_NUMBER")
            issue = repo.get_issue(int(issue_number))
            
            # Validate issue has required labels
            labels = [label.name.lower() for label in issue.labels]
            if not any(label in ['bug', 'enhancement'] for label in labels):
                logging.warning(f"Issue #{issue_number} lacks bug/enhancement label")
                print("::set-output name=triggered::false")
                return
                
            print("::set-output name=triggered::true")
            print(f"::set-output name=issue_title::{json.dumps(issue.title)}")
            print(f"::set-output name=issue_body::{json.dumps(issue.body or '')}")
            print(f"::set-output name=issue_labels::{','.join(labels)}")
            logging.info(f"Triggered for issue #{issue_number}: {issue.title}")
        else:
            print("::set-output name=triggered::false")
            logging.info("No valid trigger found in comment")
            
    except Exception as e:
        logging.error(f"Error parsing comment: {str(e)}")
        print("::set-output name=triggered::false")

if __name__ == "__main__":
    parse_comment()