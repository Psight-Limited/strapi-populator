FROM python:3.9-alpine
WORKDIR /app
COPY requirements.txt /app
RUN apk add --no-cache \
    linux-headers \
    build-base
RUN pip install -r requirements.txt
COPY . /app
CMD ["python", "./main.py"]
