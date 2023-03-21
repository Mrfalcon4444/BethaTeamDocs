# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Install any needed packages specified in requirements.txt
COPY requirements.txt /app/requirements.txt

# Install poppler-utils
RUN apt-get update && \
    apt-get install -y poppler-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
WORKDIR /app
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the application
COPY . /app

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV FLASK_APP=app.py

# Run app.py when the container launches
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "80"]
