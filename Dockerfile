FROM python:alpine

RUN mkdir /opt/bot/

RUN apk add gcc musl-dev

COPY . /opt/bot/

RUN pip install -r /opt/bot/requirements.txt

RUN cd /opt/bot/ && python helper.py -t create

WORKDIR /opt/bot/

CMD [ "python", "main.py" ]