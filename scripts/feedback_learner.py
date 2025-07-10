import os
import json
import subprocess
from github import Github
from pinecone import Pinecone
import logging

logging.basicConfig(level=logging.INFO, filename='cagent.log')

def generate_embedding(text):
    """Generate embedding using Gemini CLI."""
    try:
        result = subprocess.run(
            ["gemini-cli", "embed", "--text", text],
            capture_output=True, text=True
        )
        return json.loads(result.stdout).get("embedding", [0.0] * 128)
    except Exception as e:
        logging.error(f"Error generating embedding: {str(e)}")
        return [0.0] * 128

def update_styleguide(feedback_category, feedback_text):
    """Update styleguide based on style-related feedback."""
    if feedback_category == "style":
        try:
            with open(".gemini/styleguide.md", "a") as f:
                f.write(f"\n- {feedback_text}")
            logging.info("Updated styleguide with new rule")
        except Exception as e:
            logging.error(f"Error updating styleguide: {str(e)}")

def process_feedback():
    try:
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
        issue_number = os.getenv("GITHUB_EVENT_ISSUE_NUMBER")
        issue = repo.get_issue(int(issue_number))
        
        # Check for previous PRs
        prs = repo.get_pulls(state="all").get_page(0)
        previous_attempts = [pr for pr in prs if f"Address issue #{issue_number}" in pr.title]
        if len(previous_attempts) >= 3:
            logging.warning(f"Retry limit reached for issue #{issue_number}")
            issue.create_comment("Retry limit reached for @cagent. Please review manually.")
            return
            
        # Find the most recent unmerged PR
        relevant_pr = None
        for pr in previous_attempts:
            if not pr.merged and pr.state == "closed":
                relevant_pr = pr
                break
        
        if not relevant_pr:
            logging.info(f"No relevant closed PR found for issue #{issue_number}")
            return
            
        # Extract and categorize feedback
        comments = relevant_pr.get_comments()
        feedback = []
        for comment in comments:
            prompt = f"Categorize this feedback: {comment.body}\nOptions: functional, style, logic, other"
            result = subprocess.run(
                ["gemini-cli", "analyze", "--prompt", prompt],
                capture_output=True, text=True
            )
            category = json.loads(result.stdout).get("category", "other")
            feedback.append({"text": comment.body, "category": category})
            if category == "style":
                update_styleguide(category, comment.body)
        
        if not feedback:
            logging.info(f"No feedback found for PR #{relevant_pr.number}")
            return
            
        # Store feedback in Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("cagent-feedback")
        feedback_text = "\n".join([f["text"] for f in feedback])
        embedding = generate_embedding(feedback_text)
        index.upsert([
            {
                "id": str(relevant_pr.number),
                "values": embedding,
                "metadata": {
                    "feedback": feedback_text,
                    "issue_number": issue_number,
                    "categories": [f["category"] for f in feedback]
                }
            }
        ])
        logging.info(f"Stored feedback for PR #{relevant_pr.number}")
        
        # Query Pinecone for similar feedback
        similar_feedback = index.query(vector=embedding, top_k=5, include_metadata=True)
        similar_context = "\n".join([m["metadata"]["feedback"] for m in similar_feedback["matches"]])
        
        # Generate new changes based on feedback
        with open("context.json", "r") as f:
            context = json.load(f)
        prompt = (
            f"Address feedback for issue #{issue_number}: {feedback_text}\n"
            f"Similar past feedback: {similar_context}\n"
            f"Original context: {context['issue_title']}\n{context['issue_body']}"
        )
        result = subprocess.run(
            ["gemini-cli", "generate", "--prompt", prompt],
            capture_output=True, text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            with open("changes.json", "w") as f:
                json.dump(json.loads(result.stdout), f)
            from pr_manager import create_pr
            create_pr()
            logging.info(f"Generated new PR based on feedback for issue #{issue_number}")
        else:
            logging.error(f"Failed to generate new changes: {result.stderr}")
            issue.create_comment("Failed to generate new changes. Please review manually.")
            
    except Exception as e:
        logging.error(f"Error processing feedback: {str(e)}")
        issue.create_comment(f"Error processing @cagent feedback: {str(e)}. Please review manually.")

if __name__ == "__main__":
    process_feedback()