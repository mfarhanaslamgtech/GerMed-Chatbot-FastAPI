#!/bin/bash
set -e

# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
else
    echo "Virtual environment not found. Please create one with 'python3 -m venv .venv'."
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH=$PYTHONPATH:.

echo "Running tests..."

# Run tests in order
for f in tests/test_layer*.py; do
    echo "Running $f"
    python3 "$f"
done

echo "Running Database tests..."
python3 tests/test_db.py

echo "All tests passed successfully!"
