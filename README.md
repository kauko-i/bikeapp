# bikeapp

This is the pre-assignment for the Solita Dev Academy in fall 2022, following these instructions: https://github.com/solita/dev-academy-2022-fall-exercise/blob/main/README.md
Every recommended and additional feature except pagination and searching on the station list view is completed. No extra features included.

The app is running at bikeapp-taliso.herokuapp.com, so you only need an Internet connection and a browser for basic testing and usage.

## Run locally on Linux

These commands are tested on Ubuntu 20.04.
After cloning the repo, the following commands on the root directory of this app should start up the server.
Python 3 is installed on Ubuntu 20.04 by default, but the app is intended to be run in a virtual environment created by the `python3-venv` package.
To install that, run `sudo apt-get install python3-venv`. You need the sudo credentials to run that.
```
python3 -m venv venv # Create a virtual environment for the backend service
. venv/bin/activate # Activate that virtual environment
pip install -r requirements.txt # Install the requirements listed in requirements.txt
# The following command tells the server to connect to the Google Cloud PostgreSQL database.
# You can specify another database as well, such as a locally hosted database.
# Modify the URL if you wish.
# These credentials only allow the operations used by the app, so I see no security threat in publishing these.
export DATABASE_URL=postgres://bikeapptaliso:clutch@34.136.166.67/bikeapp
flask run # Run the server
```
Now, the app should be running on localhost:5000.
To deactivate the virtual environment, run `deactivate`.

## Run locally in Docker

You can modify the DATABASE_URL on the line 5 in Dockerfile if you wish to use some other database with this app.

These commands are tested on Ubuntu 20.04. Given that Docker is installed, in the root directory of this app, run:
```
docker build .
docker run -p 5000:5000 [THE IMAGE ID APPEARING ON THE LAST LINE OF THE FORMER COMMAND OUTPUT, PRECEDED BY "Successfully built"]
```
Now, the app should be running on localhost:5000.

## About the personal choices with this assignment

I considered using Node and TypeScript as well to crate the backend services as the language has become familiar at BirdLife.
However, Flask is the backend service framework I’m most familiar with. I've created another app, saastaruoassa (published on GitHub and Heroku cloud service as well) with that.

I thought proper database usage is the most important aspect of the assignment as there are millions of journeys.
The stucture of the CSV files seems so regular that SQL seems the self-evident choice for hosting the data. Google Cloud seemed the most
trustworthy, but (limitedly) free SQL hosting service online. I didn’t allocate very much resources for the SQL instance running in Google Cloud to save my free trial quota. That may make the app a bit slow when using the Coogle Cloud database.

It seems like every journey is listed twice in the CSV files linked in the instructions. However, the journeys don't contain any ID keys (unlike stations), and nothing proves two journeys can't have the exactly same attributes.