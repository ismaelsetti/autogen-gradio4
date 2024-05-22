FROM python:3.10.13-slim-bookworm

# Setup working directory
WORKDIR /home
COPY . /home/

# Install app requirements
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://ollama.com/install.sh | sh
RUN ollama --version
# RUN systemctl enable ollama
# RUN systemctl start ollama
RUN pip3 install -r requirements.txt
# RUN ollama serve
# RUN ollama pull llama3

RUN chmod +x docker-entrypoint.sh

EXPOSE 7860
# ENTRYPOINT ["python3", "app.py"]
ENTRYPOINT ./docker-entrypoint.sh
