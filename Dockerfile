FROM python:3.10
WORKDIR /app
RUN \
  apt-get update && \
  apt-get install -y wget && \
  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
  apt install -y ./google-chrome-stable_current_amd64.deb && \
  rm google-chrome-stable_current_amd64.deb && \
  apt-get clean
COPY ./requirements.txt /app
RUN pip install -r requirements.txt
COPY . /app
CMD ["python", "main.py"]

