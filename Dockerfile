FROM python:3.8.10
COPY ./app.py /app/app.py
COPY ./requirements.txt /app/requirements.txt
COPY templates /app/templates/
COPY static /app/static/
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT [ "python" ]
CMD [ "app.py" ]