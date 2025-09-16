# Use an official Python image as a parent image
FROM python:3.11-slim

# Install git, which is a dependency for the GitPython library
RUN apt-get update && apt-get install -y git

# Set the environment variable to prevent git from prompting for credentials
ENV GIT_TERMINAL_PROMPT=0

# Set the working directory in the container
WORKDIR /app

# --- THE FIX: COPY ALL CODE FIRST ---
# Copy the entire backend directory into the container's working directory
COPY ./backend .

# --- THEN, INSTALL DEPENDENCIES ---
# Now that the requirements.txt file is in place, install the packages.
# This ensures that executables like 'gunicorn' are not overwritten.
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 to the outside world
EXPOSE 8000

# --- THE FINAL, PRODUCTION-GRADE COMMAND ---
# Use Gunicorn with Uvicorn workers to run the application
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]
