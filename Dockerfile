FROM python:3.9

RUN apt-get install ffmpeg

WORKDIR /

COPY . .

RUN pip install -r requirements.txt

CMD [ "python", "-u", "/serverless.py" ]
