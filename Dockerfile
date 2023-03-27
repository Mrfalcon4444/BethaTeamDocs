# Use the official Python image as the base image
FROM python:3.8-slim

# Install Poppler utilities
RUN apt-get update && apt-get install -y poppler-utils

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install poppler-utils
RUN apt-get update && \
    apt-get install -y poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY . .

# Expose the port the app will run on
EXPOSE 8000

# Start the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
