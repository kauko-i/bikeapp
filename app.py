from flask import Flask, Response, render_template, request
import os
from werkzeug.utils import secure_filename
from dateutil import parser
import psycopg2

ALLOWED_EXTENSIONS = ['csv']
JOURNEY_HEADER = 'Departure,Return,Departure station id,Departure station name,Return station id,Return station name,Covered distance (m),Duration (sec.)\n'
STATION_HEADER = 'FID,ID,Nimi,Namn,Name,Osoite,Adress,Kaupunki,Stad,Operaattor,Kapasiteet,x,y\n'
DATABASE_URL = os.environ['DATABASE_URL']
JOURNEY_LIMIT = 100
METERS_IN_KILOMETER = 1000
SECONDS_IN_MINUTE = 60

def allowed_filename(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'secret'

@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'POST' and (request.files.get('journeys') or request.files.get('stations')):
        journeys = request.files.get('journeys')
        con = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = con.cursor()
        if journeys.filename != '' and allowed_filename(journeys.filename):
            secure_name = secure_filename(journeys.filename)
            journeys.save(secure_name)
            with open(secure_name, 'r', encoding='utf-8-sig') as file:
                line = file.readline()
                if line != JOURNEY_HEADER:
                    return Response(render_template('upload.html'))
                linesize = len(JOURNEY_HEADER.split(','))
                while True:
                    rowdata = file.readline().replace('\n', '')
                    if not rowdata:
                        break
                    rowdata = rowdata.split(',')
                    if len(rowdata) != linesize:
                        continue
                    try:
                        departure_time = parser.parse(rowdata[0])
                        arrival_time = parser.parse(rowdata[1])
                        departure_station = rowdata[2]
                        arrival_station = rowdata[4]
                        distance = float(rowdata[6])
                        # This seems to differ from the difference between the departure and arrival timestamps with a few seconds usually.
                        # Concluded this should be used as the "ultimate source of truth", not the former.
                        duration = float(rowdata[7])
                    except ValueError:
                        continue
                    if distance < 10 or duration < 10:
                        continue
                    cur.execute('''INSERT INTO journeys(departure_time,return_time,departure_station,return_station,distance,duration)
                    VALUES(%s,%s,%s,%s,%s,%s)''', (departure_time,arrival_time,departure_station,arrival_station,distance,duration,))
            os.remove(secure_name)
        stations = request.files.get('stations')
        if stations.filename != '' and allowed_filename(stations.filename):
            secure_name = secure_filename(stations.filename)
            stations.save(secure_name)
            with open(secure_name, 'r', encoding='utf-8-sig') as file:
                line = file.readline()
                if line != STATION_HEADER:
                    return Response(render_template('upload.html'))
                linesize = len(STATION_HEADER.split(','))
                while True:
                    rowdata = file.readline().replace('\n', '')
                    if not rowdata:
                        break
                    rowdata = rowdata.split(',')
                    if len(rowdata) != linesize:
                        continue
                    try:
                        id = rowdata[1]
                        nimi = rowdata[2]
                        namn = rowdata[3]
                        name = rowdata[4]
                        osoite = rowdata[5]
                        adress = rowdata[6]
                        kaupunki = rowdata[7]
                        stad = rowdata[8]
                        operator = rowdata[9]
                        capacity = int(rowdata[10])
                        lon = float(rowdata[11])
                        lat = float(rowdata[12])
                    except ValueError:
                        continue
                    cur.execute('''INSERT INTO stations(id,nimi,namn,name,osoite,adress,kaupunki,stad,operaattori,kapasiteetti,lat,lon)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                    (id,nimi,namn,name,osoite,adress,kaupunki,stad,operator,capacity,lat,lon),)
            os.remove(secure_name)
        con.commit()
        cur.close()
        con.close()
    return render_template('upload.html')

@app.route('/journeys')
def journeys():
    con = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = con.cursor()
    cur.execute('''
    SELECT departures.name, returns.name, distance, duration
    FROM journeys
    JOIN stations departures ON journeys.departure_station = departures.id
    JOIN stations returns ON journeys.return_station = returns.id
    LIMIT %s
    ''',(JOURNEY_LIMIT,))
    rows = cur.fetchall()
    cur.close()
    con.close()
    row_list = [{'departure_station':str(row[0]),'return_station':str(row[1]),'distance':str(float(row[2])/METERS_IN_KILOMETER),
    'duration':str(float(row[3])/SECONDS_IN_MINUTE)} for row in rows]
    return render_template('journeys.html', journeys=row_list)

@app.route('/')
def index():
    return Response('hello')

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
