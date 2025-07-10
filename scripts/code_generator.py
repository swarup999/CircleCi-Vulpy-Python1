import os
import json
import subprocess
import logging

logging.basicConfig(level=logging.INFO, filename='cagent.log')

def generate_code():
    try:
        with open("context.json", "r") as f:
            context = json.load(f)
        
        files = context["files"]
        issue_title = context["issue_title"]
        issue_body = context["issue_body"]
        
        if not files:
            logging.warning("No files to process for code generation")
            with open("changes.json", "w") as f:
                json.dump({}, f)
            return
            
        # Generate code changes using Gemini CLI
        changes = {}
        for file in files:
            prompt = f"Generate code changes for {file} to address: {issue_title}\n{issue_body}"
            result = subprocess.run(
                ["gemini-cli", "generate", "--file", file, "--prompt", prompt],
                capture_output=True, text=True
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                logging.error(f"Failed to generate changes for {file}: {result.stderr}")
                continue
                
            # Validate semantic correctness
            validation_prompt = f"Is this code correct for {issue_title}?\nCode:\n{result.stdout}"
            validation_result = subprocess.run(
                ["gemini-cli", "analyze", "--prompt", validation_prompt],
                capture_output=True, text=True
            )
            validation_data = json.loads(validation_result.stdout)
            confidence = validation_data.get("confidence", 0.0)
            
            if confidence < 0.8:
                logging.warning(f"Low confidence ({confidence}) for {file}, flagging for review")
                continue
                
            changes[file] = result.stdout
            logging.info(f"Generated changes for {file} with confidence {confidence}")
            
            # Run unit tests if available
            if file.endswith('.py'):
                with open('temp.py', 'w') as f:
                    f.write(result.stdout)
                test_result = subprocess.run(['pytest', 'temp.py'], capture_output=True, text=True)
                if test_result.returncode != 0:
                    logging.warning(f"Unit tests failed for {file}: {test_result.stderr}")
                    continue
                
                # Linting check
                lint_result = subprocess.run(['flake8', 'temp.py'], capture_output=True, text=True)
                if lint_result.returncode != 0:
                    logging.warning(f"Linting issues in {file}: {lint_result.stdout}")
        
        # Save changes to a temporary file
        with open("changes.json", "w") as f:
            json.dump(changes, f)
            
    except Exception as e:
        logging.error(f"Error generating code: {str(e)}")
        with open("changes.json", "w") as f:
            json.dump({}, f)

if __name__ == "__main__":
    generate_code()