from flask import Flask, Response, render_template, request
import os
from werkzeug.utils import secure_filename
from dateutil import parser
import psycopg2

ALLOWED_EXTENSIONS = ['csv']
JOURNEY_HEADER = 'Departure,Return,Departure station id,Departure station name,Return station id,Return station name,Covered distance (m),Duration (sec.)\n'
STATION_HEADER = 'FID,ID,Nimi,Namn,Name,Osoite,Adress,Kaupunki,Stad,Operaattor,Kapasiteet,x,y\n'
DATABASE_URL = os.environ['DATABASE_URL']
JOURNEY_LIMIT = 1000
METERS_IN_KILOMETER = 1000
SECONDS_IN_MINUTE = 60
COORDINATE_DECIMAL_ROUND = 5
JOURNEY_MIN_DURATION = 10
JOURNEY_MIN_DISTANCE = 10

def allowed_filename(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'secret'

def uploadfile(file, header, rowoperation):
    if file.filename == '' or not allowed_filename(file.filename):
        return False
    secure_name = secure_filename(file.filename)
    file.save(secure_name)
    with open(secure_name, 'r', encoding='utf-8-sig') as file:
        line = file.readline()
        if line != header:
            os.remove(secure_name)
            return False
        linesize = len(header.split(','))
        while True:
            rowdata = file.readline().replace('\n', '')
            if not rowdata:
                break
            rowdata = rowdata.split(',')
            if len(rowdata) != linesize:
                continue
            rowoperation(rowdata)
    os.remove(secure_name)
    return True

@app.route('/upload/', methods=['GET','POST'])
def upload():
    journeys = request.files.get('journeys')
    stations = request.files.get('stations')
    errors = []
    if request.method == 'POST' and (journeys or stations):
        con = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = con.cursor()
        def save_journey_row(rowdata):
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
                return False
            if JOURNEY_MIN_DISTANCE <= distance and JOURNEY_MIN_DURATION <= duration:
                cur.execute('''INSERT INTO journeys(departure_time,return_time,departure_station,return_station,distance,duration)
                VALUES(%s,%s,%s,%s,%s,%s)''', (departure_time,arrival_time,departure_station,arrival_station,distance,duration,))
            return True
        if journeys and not uploadfile(journeys, JOURNEY_HEADER, save_journey_row):
            errors.append('The journey file is inaccurate')
        def save_station_row(rowdata):
            try:
                id = rowdata[1]
                nimi = rowdata[2]
                namn = rowdata[3]
                name = rowdata[4]
                osoite = rowdata[5]
                adress = rowdata[6]
                city = rowdata[7]
                stad = rowdata[8]
                operator = rowdata[9]
                capacity = int(rowdata[10])
                lon = float(rowdata[11])
                lat = float(rowdata[12])
            except ValueError:
                return False
            cur.execute('''INSERT INTO stations(id,nimi,namn,name,address,adress,city,stad,operator,capacity,lat,lon)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
            (id,nimi,namn,name,osoite,adress,city,stad,operator,capacity,lat,lon),)
            return True
        if stations and not uploadfile(stations, STATION_HEADER, save_station_row):
            errors.append('The station file is inaccurate')
        con.commit()
        cur.close()
        con.close()
    return render_template('upload.html', errors=errors)

@app.route('/journeys/')
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

@app.route('/stations/')
@app.route('/stations/<id>/')
def stations(id=None):
    con = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = con.cursor()
    if not id:
        cur.execute('SELECT * FROM stations')
        rows = cur.fetchall()
        cur.close()
        con.close()
        row_list = [{'id':str(row[0]),'nimi':str(row[1]),'namn':str(row[2]),'name':str(row[3]),'address':str(row[4]),'adress':str(row[5]),
        'city':str(row[6]),'stad':str(row[7]),'operator':str(row[8]),'capacity':int(row[9]),
        'lat':round(float(row[10]),COORDINATE_DECIMAL_ROUND),'lon':round(float(row[11]),COORDINATE_DECIMAL_ROUND)}
        for row in rows]
        return render_template('stations.html', stations=row_list)
    cur.execute('''SELECT name, address,
    COUNT(CASE WHEN journeys.departure_station = %(id)s THEN 1 END), COUNT(CASE WHEN journeys.return_station = %(id)s THEN 1 END)
    FROM stations, journeys
    WHERE stations.id = %(id)s
    GROUP BY stations.id''',({'id':id}))
    rows = cur.fetchall()
    cur.close()
    con.close()
    if len(rows) == 0:
        return Response('No station found with id %s' % id)
    return render_template('station.html',name=rows[0][0], address=rows[0][1], starting=rows[0][2], ending=rows[0][3])

@app.route('/')
def index():
    return Response('hello')

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
