# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be required by Python packages
# For example, psycopg2 might need gcc and other build tools if not using the binary version.
# We keep this minimal for now.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory into the container
COPY . .

# By default, when the container starts, it will open a shell.
# This allows the user to run any script they want (e.g., ./build_all.sh or ./query.sh)
# For a more specific use case, you could change this to:
# CMD ["./build_all.sh"]
CMD ["bash"]
