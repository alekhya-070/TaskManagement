# app/data_manager.py
import json
import os

# Path to the developers.json file, assuming it's in a 'data' folder at the project root
# __file__ is app/data_manager.py
# os.path.dirname(__file__) is app/
# os.path.join(os.path.dirname(__file__), '..') is project_root/
# os.path.join(os.path.dirname(__file__), '..', 'data', 'developers.json') is project_root/data/developers.json
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'developers.json')

def load_developers():
    """Loads developer data from the JSON file."""
    try:
        abs_path = os.path.abspath(DATA_FILE_PATH)
        if not os.path.exists(abs_path):
            print(f"Error: The file {abs_path} was not found.")
            # Create an empty developers.json if it doesn't exist to prevent startup errors
            # though it's better to ensure it exists with actual data.
            # For this example, we'll return an empty list and let the app handle it.
            # os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            # with open(abs_path, 'w') as f:
            #     json.dump([], f)
            # print(f"Created an empty developers file at {abs_path}. Please populate it.")
            return []

        with open(abs_path, 'r') as f:
            developers = json.load(f)
        # Initialize workload score if not present
        for dev in developers:
            if 'current_workload_score' not in dev:
                dev['current_workload_score'] = 0
        return developers
    except FileNotFoundError: # Should be caught by os.path.exists now
        print(f"Error: The file {abs_path} was not found (FileNotFoundError).")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {abs_path}.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while loading developers: {e}")
        return []

def save_developers(developers_data):
    """Saves developer data back to the JSON file."""
    try:
        abs_path = os.path.abspath(DATA_FILE_PATH)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True) # Ensure data directory exists
        with open(abs_path, 'w') as f:
            json.dump(developers_data, f, indent=4)
        print(f"Developer data saved to {abs_path}")
    except Exception as e:
        print(f"An error occurred while saving developers: {e}")

if __name__ == '__main__':
    # Test loading
    devs = load_developers()
    if devs:
        print(f"Loaded {len(devs)} developers.")
        # print(devs[0])
        # Test saving (be careful, this will overwrite your file)
        # if devs:
        #     devs[0]['current_workload_score'] +=1 # Example modification
        #     save_developers(devs)
        #     print("Tested saving.")
    else:
        print("No developers loaded or an error occurred during loading.")