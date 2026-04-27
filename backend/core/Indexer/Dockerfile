# Image Base
FROM python:3.14-slim

# Define workdir
WORKDIR /app

# Copy Application in Workdir
CP . /app

# Install requirements
RUN pip install -r requirements.txt

# Expose port
EXPOSE 7003

# Command to run when container is launched
CMD ["python", "main.py"]