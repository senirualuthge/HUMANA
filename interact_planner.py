# interact_planner.py

import os
import pty
import subprocess

def start_project_planner():
    print("🤖 Starting Claude Code as the Project Planner...")
    
    # The prompt to force Claude to adopt the project-planner agent persona
    initial_prompt = (
        "🤖 Applying knowledge of @project-planner. "
        "Review the GEMINI.md guidelines, enter plan mode, and help me scope out a new feature. "
        "Start by asking me for the feature requirements."
    )
    
    # Command to run claude with the prompt
    cmd = ["claude", "-p", initial_prompt]
    
    # Spawn the process in a pseudo-terminal so claude behaves interactively
    pty.spawn(cmd)

if __name__ == "__main__":
    start_project_planner()
