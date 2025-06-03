# app/agent.py
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# Load .env from the project root (one level up from 'app' directory)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file or environment variables.")
genai.configure(api_key=GEMINI_API_KEY)

# Using the model name specified by the user
model = genai.GenerativeModel('gemini-2.0-flash-001')

TASK_CATEGORIES = ["Frontend", "Backend", "Database", "API", "QA", "DevOps", "Documentation", "Design", "Research"]
EFFORT_SCALE = ["Small", "Medium", "Large"] # MODIFIED

def generate_task_breakdown_prompt(use_case_description):
    prompt = f"""
    You are an expert AI project manager and software architect.
    Your task is to break down the following use case or feature request into smaller, actionable technical sub-tasks.

    For each sub-task, provide:
    1. A concise "title" for the task.
    2. A "description" of what needs to be done.
    3. A "category" from the following list: {', '.join(TASK_CATEGORIES)}. If unsure, choose the closest or 'Research'.
    4. An estimated "effort" level from the following scale: {', '.join(EFFORT_SCALE)}. 
    
    User Case / Feature Request:
    "{use_case_description}"

    Please format your output as a valid JSON list of objects. Each object should represent a sub-task and have the keys "title", "description", "category", and "effort".
    Example of a single task object:
    {{
        "title": "Create User Login UI",
        "description": "Develop the HTML, CSS, and JavaScript for the user login page.",
        "category": "Frontend",
        "effort": "Medium"
    }}

    Provide only the JSON list in your response, nothing else.
    """
    return prompt

def split_use_case_into_tasks(use_case_description):
    """
    Uses Gemini API to split a use case into sub-tasks.
    Returns a list of task dictionaries or None if an error occurs.
    """
    if not use_case_description:
        print("Error: No use case description provided to split_use_case_into_tasks.")
        return None

    prompt = generate_task_breakdown_prompt(use_case_description)
    try:
        response = model.generate_content(prompt)
        # print("--- Gemini Raw Response ---")
        # print(response.text)
        # print("---------------------------")

        cleaned_response_text = response.text.strip()
        if cleaned_response_text.startswith("```json"):
            cleaned_response_text = cleaned_response_text[7:]
        if cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[:-3]
        
        cleaned_response_text = cleaned_response_text.strip()

        tasks = json.loads(cleaned_response_text)
        
        if isinstance(tasks, list) and all(
            isinstance(task, dict) and
            all(key in task for key in ["title", "description", "category", "effort"]) and
            task.get("effort") in EFFORT_SCALE # Validate effort against the defined scale
            for task in tasks
        ):
            return tasks
        else:
            print("Error: Gemini response was not in the expected JSON list format or effort value is invalid.")
            print("Received (cleaned):", cleaned_response_text)
            # Attempt to identify specific issues for better debugging
            if not isinstance(tasks, list):
                print("Validation Error: Parsed JSON is not a list.")
            else:
                for i, task in enumerate(tasks):
                    if not isinstance(task, dict):
                        print(f"Validation Error: Task at index {i} is not a dictionary.")
                        continue
                    if not all(key in task for key in ["title", "description", "category", "effort"]):
                        print(f"Validation Error: Task at index {i} is missing one or more required keys (title, description, category, effort). Task: {task}")
                    if task.get("effort") not in EFFORT_SCALE:
                         print(f"Validation Error: Task at index {i} has an invalid effort value '{task.get('effort')}'. Expected one of {EFFORT_SCALE}. Task: {task}")
            return None

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Gemini: {e}")
        print("Received text (raw) was:", response.text)
        return None
    except Exception as e:
        # This can catch errors from genai.GenerativeModel if the model name is invalid
        print(f"An unexpected error occurred with Gemini API or response processing: {e}")
        return None

if __name__ == '__main__':
    sample_use_case = "As a user, I want to be able to register for a new account using my email and password, so I can access the platform's features. This should include email verification."
    print(f"Processing use case: {sample_use_case}")
    generated_tasks = split_use_case_into_tasks(sample_use_case)

    if generated_tasks:
        print("\nGenerated Tasks:")
        for task in generated_tasks:
            print(f"  - Title: {task['title']}")
            print(f"    Description: {task['description']}")
            print(f"    Category: {task['category']}")
            print(f"    Effort: {task['effort']}")
            print("-" * 20)
    else:
        print("\nFailed to generate tasks.")