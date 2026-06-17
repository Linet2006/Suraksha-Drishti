FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
# 1. Install PaddlePaddle specifically compiled for CPU
RUN pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple

# 2. Install PaddleOCR and other requirements
RUN pip install paddleocr>=2.0.1
RUN pip install fastapi uvicorn python-multipart opencv-python-headless pillow

# Copy the rest of the application
COPY . .

# Expose the API port
EXPOSE 8000

# Command to run the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
