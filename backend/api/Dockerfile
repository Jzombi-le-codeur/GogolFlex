# Image Base
FROM python:3.14-slim

# Define workdir
WORKDIR /app

# Copy Application in Workdir
COPY . /app

# Install requirements
RUN pip install -r requirements.txt

# Expose port
EXPOSE 7000

# Command to run when container is launched
CMD ["python", "main.py"]