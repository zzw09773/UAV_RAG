#!/bin/bash
# A simple wrapper script to execute the main RAG query application.

# Exit immediately if a command fails.
set -e

# Ensure we are in the correct directory (project root)
cd "$(dirname "$0")"

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  set -a # automatically export all variables
  source .env
  set +a # stop automatically exporting
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# --- Argument Handling ---
# If the first argument exists and does not start with a '-',
# assume it is the query and prepend the '-q' flag.
# This allows for a more natural CLI usage: ./query.sh "My question"
ARGS=() # Initialize empty array for arguments
if [[ $# -gt 0 && ! "$1" =~ ^- ]]; then
  # First arg is the query, prepend -q
  ARGS+=("-q" "$1")
  # Add the rest of the arguments
  shift # Remove the first argument
  ARGS+=("$@")
else
  # Arguments already have flags, use them as is
  ARGS+=("$@")
fi
# --- End Argument Handling ---

echo "Executing RAG query application with arguments: ${ARGS[@]}"
echo "-----------------------------------------------------"

# Pass the processed arguments to the Python application (with SSL verification disabled)
python3 -m rag_system.query_rag_pg "${ARGS[@]}" --no-verify-ssl
