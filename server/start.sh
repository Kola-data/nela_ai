#!/bin/bash

# 1. Define the absolute root of your project dynamically
export PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE}" )" &> /dev/null && pwd )"
cd "$PROJECT_ROOT"

# 2. Activate virtual environment
source venv/bin/activate

# 3. CRITICAL: Add the root to PYTHONPATH
export PYTHONPATH=$PROJECT_ROOT

echo "🚀 Starting server with root: $PROJECT_ROOT"

# 4. Initialize the Database Tables (Runs once and waits for completion)
echo "Initializing database tables..."
python3 Config/DB/init_db.py

# Check if the DB initialization was successful (exit code 0)
if [ $? -eq 0 ]; then
    echo "✅ Database ready. Starting server..."
else
    echo "❌ Error during database initialization. Exiting."
    exit 1
fi

# 5. Start the Uvicorn Server
# NOTE: --reload disabled due to file watch limit issues
# Use --reload only during development with a smaller venv
uvicorn main:app --host 0.0.0.0 --port 8001
