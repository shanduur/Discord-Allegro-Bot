FROM python

RUN mkdir -f /opt/bot/

COPY . /opt/bot/

RUN pip install -r requirements.txt

RUN python /opt/bot/helper.py -t create

CMD [ "python", "/opt/bot/main.py" ]