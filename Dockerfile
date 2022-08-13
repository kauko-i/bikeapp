FROM python:3.8.10
# I know password shouldn't be this public, and "clutch" is far from a perfect password,
# but only the select and insert queries on the stations and journeys tables are granted on this role.
# The Google Cloud PostgreSQL service just requires a password for every role.
ENV DATABASE_URL=postgres://bikeapptaliso:clutch@34.136.166.67/bikeapp
COPY ./app.py /app/app.py
COPY ./requirements.txt /app/requirements.txt
COPY templates /app/templates/
COPY static /app/static/
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT [ "python" ]
CMD [ "app.py" ]