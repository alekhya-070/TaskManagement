# app/main.py
from flask import Flask, request, jsonify, render_template
import os
import sys # Import sys

# ---- Add project root to sys.path if not already there ----
# This helps when running app/main.py directly from the project root as CWD.
# Or when VS Code's "Run Python File" is used on app/main.py and CWD is project root.
# __file__ is /path/to/your_project_directory/app/main.py
# project_root should be /path/to/your_project_directory/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------------------------------------------------

# Now, relative imports from the `app` package should work more reliably
# because 'project_root' is in sys.path, making 'app' discoverable as a top-level package.
# However, if main.py is the entry point, `from .agent` implies `app.agent` is already known.
# The above sys.path manipulation is more for ensuring modules within 'app' can find each other
# if VSCode runs main.py with a CWD *inside* the app directory.
# Let's stick to the `from .module` style for consistency within the app package.

from .agent import split_use_case_into_tasks
from .allocation import assign_tasks_with_ai, get_effort_score
from .data_manager import load_developers, save_developers

app = Flask(__name__) # Flask will find templates/static relative to `app` directory if main.py is in `app`

# ... (rest of your Flask routes and logic from the previous version)
# Make sure the @app.route('/') and @app.route('/process_use_case') are here.
# For brevity, I'm not pasting them again. Assume they are unchanged.

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_use_case', methods=['POST'])
def process_use_case():
    data = request.get_json()
    use_case_description = data.get('use_case')

    if not use_case_description:
        return jsonify({"error": "No use case description provided"}), 400

    # --- Agent 1: Task Breakdown ---
    print("Agent 1 (Breakdown): Processing use case...")
    ai_tasks_breakdown = split_use_case_into_tasks(use_case_description)
    
    if ai_tasks_breakdown is None:
        error_msg = "Agent 1 (Breakdown): Failed to process use case with AI. Check Gemini configuration or prompt."
        print(error_msg)
        return jsonify({"error": error_msg}), 500
    
    if not ai_tasks_breakdown:
        print("Agent 1 (Breakdown): Gemini returned an empty list of tasks.")
        devs_for_empty_tasks = load_developers()
        if not devs_for_empty_tasks:
             devs_for_empty_tasks = []

        return jsonify({
            "message": "AI (Breakdown) processed the use case but did not generate any specific sub-tasks.",
            "original_tasks_from_ai": [],
            "allocated_tasks": [],
            "updated_developer_workloads_preview": devs_for_empty_tasks
        }), 200

    # --- Load Developer Data ---
    developers_initial_state = load_developers()
    if not developers_initial_state:
        print("Error: Failed to load developer data. AI allocation will be impacted.")
        developers_initial_state = [] 
    
    developers_for_this_run = [d.copy() for d in developers_initial_state]
    for dev in developers_for_this_run:
        dev['experience'] = dev.get('experience', {}).copy()
        dev['current_workload_score'] = dev.get('current_workload_score', 0)
        dev['skills'] = dev.get('skills', [])

    # --- Agent 2: AI Task Allocation ---
    print(f"Agent 2 (Allocation): Allocating {len(ai_tasks_breakdown)} tasks using AI...")
    tasks_with_ai_assignment = assign_tasks_with_ai(ai_tasks_breakdown, developers_for_this_run)
    
    # --- Update Developer Workloads based on AI Assignment ---
    if developers_for_this_run:
        temp_dev_map_for_workload_update = {dev['id']: dev for dev in developers_for_this_run}
        
        for task in tasks_with_ai_assignment:
            assigned_to_info = task.get('assigned_to')
            if assigned_to_info:
                assignee_id = assigned_to_info.get('id')
                if assignee_id and assignee_id != "unassigned" and assignee_id in temp_dev_map_for_workload_update:
                    task_effort_score = task.get('effort_score') 
                    if task_effort_score is None:
                        task_effort_score = get_effort_score(task.get('effort'))
                        print(f"Warning: effort_score missing for task '{task.get('title')}', recalculating.")

                    developer_to_update = temp_dev_map_for_workload_update[assignee_id]
                    developer_to_update['current_workload_score'] = \
                        developer_to_update.get('current_workload_score', 0) + task_effort_score
                elif assignee_id and assignee_id != "unassigned":
                    print(f"Workload Update SKIPPED: Assigned developer ID '{assignee_id}' for task '{task.get('title')}' not found.")
            else:
                 print(f"Workload Update SKIPPED: Task '{task.get('title')}' has no 'assigned_to' info.")

    # print("Persisting updated developer workloads...")
    # save_developers(developers_for_this_run)

    print("Processing complete. Returning results.")
    return jsonify({
        "original_tasks_from_ai": ai_tasks_breakdown,
        "allocated_tasks": tasks_with_ai_assignment,
        "updated_developer_workloads_preview": developers_for_this_run
    })
# This is the crucial part for direct execution
if __name__ == '__main__':
    # When app/main.py is run directly, __name__ becomes "__main__".
    # Ensure Flask's development server is started.
    
    # You might need to adjust host and port if needed, or load from env vars.
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting Flask server on host 0.0.0.0, port {port}...")
    print(f"Project root identified as: {project_root}")
    print(f"Python sys.path includes: {sys.path[0]}, {sys.path[1]}...")
    print(f"To access the app, open http://127.0.0.1:{port}/ in your browser.")
    app.run(debug=True, host='0.0.0.0', port=port)