# Backend Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /code

# Install Python dependencies
COPY requirements.txt /code/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project code
COPY . /code/

# Create directories for media and static files
RUN mkdir -p /code/mediafiles /code/staticfiles

# Add wait-for-db command
COPY ./manage.py /code/
RUN chmod +x /code/manage.py

EXPOSE 8000