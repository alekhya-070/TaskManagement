# app/allocation.py
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# Load .env from the project root (one level up from 'app' directory)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

GEMINI_API_KEY_ALLOCATION = os.getenv("GEMINI_API_KEY") # Reuse the same key
if not GEMINI_API_KEY_ALLOCATION:
    raise ValueError("GEMINI_API_KEY not found for allocation agent.")
genai.configure(api_key=GEMINI_API_KEY_ALLOCATION)

# Using the model name specified by the user previously for consistency,
# though a more powerful model might be better for complex allocation.
# If this model struggles, consider 'gemini-1.0-pro' or 'gemini-1.5-pro-latest'.
allocation_model = genai.GenerativeModel('gemini-2.0-flash-001')


EFFORT_TO_SCORE = {
    "Small": 2,
    "Medium": 3,
    "Large": 5,
    "Default": 3  # Default if effort string is not recognized
}

def get_effort_score(effort_str):
    """Converts effort string to a numeric score."""
    return EFFORT_TO_SCORE.get(effort_str, EFFORT_TO_SCORE["Default"])

def generate_ai_allocation_prompt(tasks_json_str, developers_json_str):
    """
    Generates the prompt for the AI allocation agent.
    """
    prompt = f"""
    You are an expert AI Resource Allocation Manager.
    Your task is to assign a list of technical sub-tasks to a team of developers.
    For each task, you must choose the most suitable developer.

    Consider the following criteria for assignment, in approximate order of importance:
    1.  **Skill Match:** The developer MUST have the primary skill related to the task's "category".
        Review the developer's "skills" list. E.g., a "Frontend" task needs a developer with "Frontend" or a more specific frontend skill like "React" or "JavaScript" listed in their skills.
    2.  **Current Workload:** Prefer developers with a lower `current_workload_score`. This score represents their current busyness.
    3.  **Experience:** If multiple developers meet skill and workload criteria, prefer the one with more `experience` (numeric value) in the task's specific "category".
    4.  **Fair Distribution:** If all else is roughly equal, try to distribute tasks. Avoid overloading one developer if others are available and suitable.

    You will be given:
    1.  A JSON list of tasks to be assigned. Each task has a "title", "description", "category", and "effort" (Small, Medium, Large).
    2.  A JSON list of available developers. Each developer has an "id", "name", "skills" (list of strings), "experience" (an object mapping skill category to years of experience, e.g., {{"Frontend": 5, "Backend": 2}}), and "current_workload_score".

    TASKS TO ASSIGN:
    {tasks_json_str}

    AVAILABLE DEVELOPERS:
    {developers_json_str}

    Based on the tasks and developers provided, assign EACH task to ONE developer.
    Provide your output as a valid JSON list of objects. Each object in the list should represent ONE of the original tasks and MUST include:
    - "title": (string, exactly as from the input task)
    - "category": (string, exactly as from the input task)
    - "effort": (string, exactly as from the input task)
    - "description": (string, exactly as from the input task)
    - "assigned_developer_id": (string) The "id" of the developer you have assigned. If NO developer is suitable (e.g., no skill match, or all suitable developers are critically overloaded based on your judgment), use the string "unassigned".
    - "reasoning": (string) A brief explanation for your choice of developer for this task, or why it was left unassigned.

    Example of a single output task object:
    {{
        "title": "Create User Login UI",
        "category": "Frontend",
        "effort": "Medium",
        "description": "Develop the HTML, CSS, and JavaScript for the user login page.",
        "assigned_developer_id": "dev1",
        "reasoning": "Alice (dev1) has strong Frontend skills (5 years experience) and a manageable workload score of 2."
    }}

    Ensure every task from the input "TASKS TO ASSIGN" list is present in your output JSON list.
    Provide only the JSON list in your response, nothing else before or after the list.
    """
    return prompt

def assign_tasks_with_ai(tasks_from_breakdown, developers_data_original):
    """
    Uses a Gemini AI agent to allocate tasks.
    Returns a list of task objects, where each task includes AI's assignment decision
    (assigned_developer_id and reasoning) and original task details.
    Developer workloads are NOT updated by this function directly.
    """
    if not tasks_from_breakdown:
        print("Allocation AI: No tasks provided to assign.")
        return []
    if not developers_data_original:
        print("Allocation AI: No developers data provided. Tasks will be marked unassigned.")
        # Prepare tasks to be returned as unassigned
        return [
            {
                **task.copy(),
                'assigned_to': {"id": "unassigned", "name": "Unassigned - No Developers Available"},
                'ai_reasoning': 'No developers were available for assignment.',
                'effort_score': get_effort_score(task.get('effort'))
            } for task in tasks_from_breakdown
        ]

    # Prepare JSON strings for the prompt
    # Ensure tasks for AI have essential fields. The breakdown agent should provide these.
    tasks_for_ai_prompt = json.dumps([
        {"title": t.get("title"), "category": t.get("category"), "effort": t.get("effort"), "description": t.get("description")}
        for t in tasks_from_breakdown
    ])
    
    # Ensure developers for AI have essential fields.
    developers_for_ai_prompt = json.dumps([
        {"id": d.get("id"), "name": d.get("name"), "skills": d.get("skills"), "experience": d.get("experience"), "current_workload_score": d.get("current_workload_score", 0)}
        for d in developers_data_original
    ])

    prompt = generate_ai_allocation_prompt(tasks_for_ai_prompt, developers_for_ai_prompt)

    final_assigned_tasks = []

    try:
        # print("\n--- Allocation AI Prompt ---")
        # print(prompt)
        # print("---------------------------\n")
        response = allocation_model.generate_content(prompt)
        
        cleaned_response_text = response.text.strip()
        if cleaned_response_text.startswith("```json"):
            cleaned_response_text = cleaned_response_text[7:]
        if cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[:-3]
        cleaned_response_text = cleaned_response_text.strip()
        
        # print("\n--- Allocation AI Raw Response ---")
        # print(cleaned_response_text)
        # print("--------------------------------\n")

        ai_assignment_results = json.loads(cleaned_response_text)

        if not isinstance(ai_assignment_results, list):
            print("Error: AI allocation response was not a list.")
            raise ValueError("AI response format error.")

        # Create a map of AI assignments by title for easy lookup
        ai_assignments_map = {}
        for item in ai_assignment_results:
            if isinstance(item, dict) and "title" in item:
                ai_assignments_map[item["title"]] = item
            else:
                print(f"Warning: AI returned an invalid item in assignment list: {item}")


        # Merge AI assignments with original task data
        for original_task in tasks_from_breakdown:
            task_copy = original_task.copy() # Start with original task details
            task_title = original_task.get("title")

            ai_assignment_details = ai_assignments_map.get(task_title)

            if ai_assignment_details:
                assigned_dev_id = ai_assignment_details.get("assigned_developer_id")
                reasoning = ai_assignment_details.get("reasoning", "No reasoning provided by AI.")
                
                assigned_dev_info = None
                if assigned_dev_id and assigned_dev_id != "unassigned":
                    # Find developer details from the original list
                    dev_match = next((dev for dev in developers_data_original if dev['id'] == assigned_dev_id), None)
                    if dev_match:
                        assigned_dev_info = {"id": dev_match['id'], "name": dev_match['name']}
                    else:
                        # AI might have hallucinated an ID or there's a mismatch
                        assigned_dev_info = {"id": assigned_dev_id, "name": f"Unknown Dev ID: {assigned_dev_id} (AI Suggestion)"}
                        print(f"Warning: AI assigned task '{task_title}' to non-existent developer ID '{assigned_dev_id}'.")
                elif assigned_dev_id == "unassigned":
                    assigned_dev_info = {"id": "unassigned", "name": "Unassigned by AI"}
                else: # AI didn't provide an ID or a valid "unassigned"
                    assigned_dev_info = {"id": "unassigned", "name": "Unassigned (AI provided no valid ID)"}
                    print(f"Warning: AI provided no valid assigned_developer_id for task '{task_title}'. Details: {ai_assignment_details}")

                task_copy['assigned_to'] = assigned_dev_info
                task_copy['ai_reasoning'] = reasoning
            else:
                # Task was in original list but AI didn't return an assignment for it
                task_copy['assigned_to'] = {"id": "unassigned", "name": "Unassigned (Not in AI response)"}
                task_copy['ai_reasoning'] = "This task was not included in the AI allocator's assignment list."
                print(f"Warning: Task '{task_title}' was not found in AI allocation agent's response.")
            
            # Add effort score for subsequent workload calculation
            task_copy['effort_score'] = get_effort_score(task_copy.get('effort', "Medium"))
            final_assigned_tasks.append(task_copy)

        return final_assigned_tasks

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Allocation AI: {e}")
        print("Received text was:", response.text if 'response' in locals() else "N/A")
    except Exception as e:
        print(f"An unexpected error occurred with Allocation AI: {e}")
        import traceback
        traceback.print_exc()

    # Fallback: if any error, return original tasks marked as unassigned due to AI error
    print("Allocation AI: Falling back to unassigned due to error.")
    for task in tasks_from_breakdown:
        task_copy = task.copy()
        if 'assigned_to' not in task_copy: # Avoid overwriting if partially processed
            task_copy['assigned_to'] = {"id": "unassigned", "name": "Unassigned due to AI allocation error"}
            task_copy['ai_reasoning'] = 'An error occurred during the AI-driven allocation process.'
            task_copy['effort_score'] = get_effort_score(task_copy.get('effort', "Medium"))
        final_assigned_tasks.append(task_copy)
    return final_assigned_tasks


if __name__ == '__main__':
    # Mock data for testing the allocation agent
    sample_tasks_from_breakdown = [
        {"title": "Setup Frontend Project", "description": "Basic setup", "category": "Frontend", "effort": "Small"},
        {"title": "Design User Schema", "description": "For SQL DB", "category": "Database", "effort": "Medium"},
        {"title": "Implement Login API", "description": "User auth endpoint", "category": "Backend", "effort": "Large"},
        {"title": "NonExistent Category Task", "description": "Research this", "category": "NewTech", "effort": "Medium"},
    ]
    
    # Using load_developers from data_manager for a more realistic test
    from .data_manager import load_developers
    developers = load_developers()
    if not developers: # Fallback if data_manager or developers.json is missing
        print("MAIN TEST: Failed to load developers, using MOCK developers for allocation test.")
        developers = [
            {"id": "dev1", "name": "Alice", "skills": ["Frontend", "UI/UX"], "experience": {"Frontend": 5}, "current_workload_score": 2},
            {"id": "dev2", "name": "Bob", "skills": ["Backend", "Database", "API"], "experience": {"Backend": 3, "Database": 4}, "current_workload_score": 1},
            {"id": "dev3", "name": "Charlie", "skills": ["DevOps", "Backend"], "experience": {"DevOps": 4, "Backend": 2}, "current_workload_score": 5},
        ]

    print("\n--- Testing AI Task Allocation ---")
    print("Input Tasks:", json.dumps(sample_tasks_from_breakdown, indent=2))
    print("Input Developers:", json.dumps(developers, indent=2))
    
    allocated_tasks_result = assign_tasks_with_ai(sample_tasks_from_breakdown, developers)

    print("\n--- AI Allocation Results ---")
    if allocated_tasks_result:
        for task in allocated_tasks_result:
            print(f"  Task: {task['title']} (Effort: {task['effort']}, Score: {task.get('effort_score')})")
            print(f"    Category: {task['category']}")
            assignee = task.get('assigned_to', {}).get('name', 'Error fetching assignee')
            print(f"    Assigned To: {assignee} (ID: {task.get('assigned_to', {}).get('id')})")
            print(f"    AI Reasoning: {task.get('ai_reasoning')}")
            print("-" * 20)
    else:
        print("No tasks were allocated or an error occurred.")

    # Note: Workload updates would happen in main.py after this function returns.
    print("\nDeveloper workloads would be updated by the orchestrator (main.py) based on these assignments.")