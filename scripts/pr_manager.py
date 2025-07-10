import os
import json
from github import Github
import uuid
import logging

logging.basicConfig(level=logging.INFO, filename='cagent.log')

def create_pr():
    try:
        with open("context.json", "r") as f:
            context = json.load(f)
        with open("changes.json", "r") as f:
            changes = json.load(f)
        
        if not changes:
            logging.warning("No changes to commit")
            return
            
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
        issue_number = os.getenv("GITHUB_EVENT_ISSUE_NUMBER")
        
        # Check for previous PRs
        previous_prs = repo.get_pulls(state="all").get_page(0)
        previous_attempts = [pr for pr in previous_prs if f"Address issue #{issue_number}" in pr.title]
        attempt_number = len(previous_attempts) + 1
        
        # Create a new branch
        branch_name = f"cagent/issue-{issue_number}-attempt-{attempt_number}-{uuid.uuid4()}"
        source = repo.get_branch("main")
        repo.create_git_ref(f"refs/heads/{branch_name}", source.commit.sha)
        
        # Commit changes
        for file_path, content in changes.items():
            try:
                file = repo.get_contents(file_path, ref="main")
                repo.update_file(
                    file_path,
                    f"CAgent: Address issue #{issue_number} (Attempt {attempt_number})",
                    content,
                    file.sha,
                    branch=branch_name
                )
                logging.info(f"Updated {file_path}")
            except:
                repo.create_file(
                    file_path,
                    f"CAgent: Address issue #{issue_number} (Attempt {attempt_number})",
                    content,
                    branch=branch_name
                )
                logging.info(f"Created {file_path}")
        
        # Build PR body with previous attempt context
        pr_body = f"Automated changes for issue #{issue_number}: {context['issue_title']}\n\n{context['issue_body']}\n\n"
        if previous_attempts:
            pr_body += "**Previous Attempts:**\n"
            for pr in previous_attempts:
                feedback = [c.body for c in pr.get_comments() if 'reject' in c.body.lower()]
                pr_body += f"- PR #{pr.number} ({pr.state}): {feedback or 'No feedback'}\n"
        
        # Create PR
        pr = repo.create_pull(
            title=f"CAgent: Address issue #{issue_number} (Attempt {attempt_number})",
            body=pr_body,
            head=branch_name,
            base="main"
        )
        
        # Assign reviewers
        issue = repo.get_issue(int(issue_number))
        assignees = [assignee.login for assignee in issue.assignees]
        if assignees:
            pr.add_to_assignees(*assignees)
            logging.info(f"Assigned reviewers: {assignees}")
        
        # Post comment linking PR
        issue.create_comment(f"Created PR #{pr.number} (Attempt {attempt_number}) for this issue.")
        logging.info(f"Created PR #{pr.number}")
        
    except Exception as e:
        logging.error(f"Error creating PR: {str(e)}")

if __name__ == "__main__":
    create_pr()