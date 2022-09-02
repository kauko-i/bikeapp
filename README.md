# bikeapp

This has originally been created as a pre-assignment for the Solita Dev Academy in fall 2022, following these instructions: https://github.com/solita/dev-academy-2022-fall-exercise/blob/main/README.md
Every recommended and additional feature except pagination and searching on the station list view has been completed. No extra features included.

## Initialize database

Creating a PostgreSQL database is up to the OS, but after creating it, you can initialize the proper tables to run the app with the following commands in the PostgreSQL command line.

```
CREATE TABLE journeys(
    departure_time TIMESTAMP,
    return_time TIMESTAMP,
    departure_station VARCHAR(3),
    return_station VARCHAR(3),
    distance NUMERIC,
    duration NUMERIC
);
CREATE TABLE stations(
    id VARCHAR(3),
    nimi VARCHAR(256),
    namn VARCHAR(256),
    name VARCHAR(256),
    address VARCHAR(256),
    adress VARCHAR(256),
    city VARCHAR(256),
    stad VARCHAR(256),
    operator VARCHAR(256),
    capacity INTEGER,
    lat NUMERIC,
    lon NUMERIC
);
```

## Run locally on Linux

These commands have been tested on Ubuntu 20.04 and Ubuntu 22.04.
After cloning the repo, the following commands in the root directory of this app should start up the server.
Python 3 is installed on Ubuntu 20.04 by default, but the app is intended to be run in a virtual environment created by the `python3-venv` package.
To install that, run `sudo apt-get install python3-venv`. You need the sudo credentials to run that.
```
python3 -m venv venv # Create a virtual environment for the backend service
. venv/bin/activate # Activate that virtual environment
pip install -r requirements.txt # Install the requirements listed in requirements.txt
# The following command tells the server to connect to the specified database.
# The URL used by the app running on Heroku has been emailed to Pauliina Hovila.
export DATABASE_URL=[INSERT YOUR DATABASE URL]
flask run # Run the server
```
Now, the app should be running on localhost:5000.
To deactivate the virtual environment, run `deactivate`.

## Run locally in Docker

These commands have been tested on Ubuntu 20.04 and Ubuntu 22.04. Given that Docker has been installed, in the root directory of this app, run:
```
docker build -t bikeapp .
docker run -p 5000:5000 --env DATABASE_URL=[INSERT YOUR DATABASE URL] --net="host" bikeapp
```
The `--net="host"` argument is unnecessary if you connect to a remote database. Now, the app should be running on localhost:5000.

## About the personal choices with this assignment

### Used technologies
* PostgreSQL
* Flask
* Jinja templates for generating the HTML
* Leaflet to display a map on the single station view

I considered using Node and TypeScript as well to create the backend services as the language has become familiar at BirdLife.
However, Flask is the backend service framework I’m most familiar with. I've created another app, saastaruoassa (published on GitHub and Heroku cloud service as well) with that.

I thought proper database usage is the most important aspect of the assignment as there are millions of journeys.
The structure of the CSV files seems so regular that SQL seems the self-evident choice for hosting the data.

It seems like every journey is listed twice in the CSV files linked in the instructions. However, the journeys don't contain any ID keys (unlike stations), and nothing proves two journeys can't have the exactly same attributes.
