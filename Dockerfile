# Use a lightweight official Python 3.9 image
FROM python:3.9-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to utilize Docker build layer caching
COPY requirements.txt .

# Upgrade pip and install modular local RAG python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose the default Streamlit port
EXPOSE 8501

# Command to boot Streamlit and bind to all interface addresses
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
