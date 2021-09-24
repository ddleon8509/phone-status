FROM ubuntu:20.04
ARG DEFAULT_PORT=80
RUN apt-get update \
    && apt-get install -y \
        gcc \
        g++ \
        python3 \
        python3-pip
WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
ENV PORT ${DEFAULT_PORT}
EXPOSE $PORT
CMD ["python3","app.py"]