FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose the port the app runs on
EXPOSE 8001

# Command to run the application
CMD ["python", "socket_server.py"] 