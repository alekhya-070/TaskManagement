# AI Task Management Agent

This project is a proof-of-concept AI agent that takes a high-level use case description,
splits it into smaller technical tasks using the Gemini API, and allocates these tasks
to developers based on their skills, experience, and current workload.

## Setup

1.  **Clone the repository (or create files as described).**
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up your Gemini API Key:**
    Create a `.env` file in the project root (`task-management-ai/`) and add your API key:
    ```
    GEMINI_API_KEY=YOUR_ACTUAL_GEMINI_API_KEY
    ```
5.  **Populate `data/developers.json`** with your team's data.

## Running the Application

```bash
python -m app.main