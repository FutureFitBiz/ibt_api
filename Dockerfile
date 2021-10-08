FROM python:3.9
COPY . /
WORKDIR /app
EXPOSE 5000
ENV PYTHONPATH=/
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt
