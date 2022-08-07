from flask import Flask, Response, render_template, request
import os
from werkzeug.utils import secure_filename
from dateutil import parser
import psycopg2
from psycopg2 import sql
from urllib.parse import urlencode

# Constraints related to the app.
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

# A function to validate the name of an uploaded file.
def allowed_filename(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'secret'

# A general function to be used to insert data from CSV files to a database.
# The parameters are the file object, the expected header row, and the function to be applied to each of the other rows.
# Returns True if upload was successful, otherwise False.
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
        # Determines how to do the SQL insert query based on a journey row on a CSV file.
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
        # Determines how to do the SQL insert query based on a station row on a CSV file.
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
    # Read the URL parameters and set the default values if not passed.
    page = request.args.get('page')
    page = 0 if not page else int(page)
    departure = request.args.get('departure')
    departure = '' if not departure else departure
    arrival = request.args.get('return')
    arrival = '' if not arrival else arrival
    mindistance = request.args.get('mindistance')
    mindistance = -1 if not mindistance else float(mindistance)*METERS_IN_KILOMETER
    maxdistance = request.args.get('maxdistance')
    maxdistance = -1 if not maxdistance else float(maxdistance)*METERS_IN_KILOMETER
    minduration = request.args.get('minduration')
    minduration = -1 if not minduration else float(minduration)*SECONDS_IN_MINUTE
    maxduration = request.args.get('maxduration')
    maxduration = -1 if not maxduration else float(maxduration)*SECONDS_IN_MINUTE
    order_params = ['departures.name', 'returns.name', 'distance', 'duration']
    primary_order = request.args.get('order')
    if primary_order in order_params:
        order_params.remove(primary_order)
        order_params.insert(0, primary_order)
    direction = request.args.get('direction')
    if not direction:
        direction = ''
    con = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = con.cursor()
    # Query journeys from the database according to the URL parameters.
    cur.execute(sql.SQL('''SELECT departures.name, returns.name, distance, duration
    FROM journeys
    JOIN stations departures ON journeys.departure_station = departures.id
    JOIN stations returns ON journeys.return_station = returns.id
    WHERE (departures.name = %(departure)s OR %(departure)s = '') AND (returns.name = %(arrival)s OR %(arrival)s = '') AND
    (%(mindistance)s <= distance OR %(mindistance)s = -1) AND (distance <= %(maxdistance)s OR %(maxdistance)s = -1) AND
    (%(minduration)s <= duration OR %(minduration)s = -1) AND (duration <= %(maxduration)s OR %(maxduration)s = -1)
    ORDER BY {order1} {direction}, {order2}, {order3}, {order4} LIMIT %(limit)s OFFSET %(offset)s''')
    # The format function is safe with psycopg2.sql objects: https://www.psycopg.org/docs/sql.html
    .format(order1=sql.SQL(order_params[0]),order2=sql.SQL(order_params[1]),
    order3=sql.SQL(order_params[2]),order4=sql.SQL(order_params[3]),direction=sql.SQL(direction)),
    {'departure':departure,'arrival':arrival,'mindistance':mindistance,'maxdistance':maxdistance,
    'minduration':minduration,'maxduration':maxduration,'limit':JOURNEY_LIMIT + 1,'offset':JOURNEY_LIMIT*page})
    rows = cur.fetchall()
    cur.close()
    con.close()
    # The query searches for one row more than what's going to be displayed on a single page.
    # A link to the next page is displayed if and only if such a row is found.
    last_page = False
    if len(rows) < JOURNEY_LIMIT + 1:
        last_page = True
    else:
        rows = rows[:-1]
    # The journey data is transmitted to the tempalte as a list of dicts.
    row_list = [{'departure_station':str(row[0]),'return_station':str(row[1]),'distance':str(float(row[2])/METERS_IN_KILOMETER),
    'duration':str(float(row[3])/SECONDS_IN_MINUTE)} for row in rows]
    # All URL parameters except page are intended to be sustained, but the page links require that the original page parameter is not repassed.
    query = dict(request.args)
    if 'page' in query:
        del query['page']
    return render_template('journeys.html', journeys=row_list, page=page, last=last_page, query=query, querystring=urlencode(query))

# The same function is used for both the station list and the single station view.
# If id is None, the whole list is displayed. Otherwise, a single station view is displayed according to the id.
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
