# Use an official Python image as a parent image
FROM python:3.11-slim

# Install git, which is a dependency for the GitPython library
# apt-get update refreshes the package lists
# -y automatically confirms the installation
RUN apt-get update && apt-get install -y git

# --- THE FIX ---
# This environment variable tells Git to never prompt for credentials.
# If credentials are required, it will fail immediately instead of hanging.
# This is essential for running in non-interactive environments like Docker.
ENV GIT_TERMINAL_PROMPT=0

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY backend/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container at /app
COPY backend/ .

# Expose port 8000 to the outside world
EXPOSE 8000

# Command to run the application using uvicorn
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]
