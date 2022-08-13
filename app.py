"""The backend service used in the Solita Dev Academy fall 2022 pre-assignment"""
import os
import re
from urllib.parse import urlencode
from flask import Flask, Response, render_template, request
from werkzeug.utils import secure_filename
from dateutil import parser
import psycopg2
from psycopg2 import sql

# Constraints related to the app.
ALLOWED_EXTENSIONS = ['csv']
JOURNEY_HEADER = 'Departure,Return,Departure station id,Departure station name,Return station id,Return station name,Covered distance (m),Duration (sec.)\n'
STATION_HEADER = 'FID,ID,Nimi,Namn,Name,Osoite,Adress,Kaupunki,Stad,Operaattor,Kapasiteet,x,y\n'
DATABASE_URL = os.environ['DATABASE_URL']
JOURNEY_LIMIT = 1000
METERS_IN_KILOMETER = 1000
SECONDS_IN_MINUTE = 60
DECIMAL_ROUND = 5
JOURNEY_MIN_DURATION = 10
JOURNEY_MIN_DISTANCE = 10
MONTH_PARAM = '^\\d(\\d)?-\\d{4}$' # Regular expression describing the form in which the month parameters are passed when fetching station-specific journey calculations
ROWS_INSERTED_AT_ONCE = 1000

def allowed_filename(filename):
    '''A function to validate the name of an uploaded file.'''
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)

def uploadfile(file, header, csv_row2sql_row, validate_row, insertoperation):
    '''
    A general function to be used to insert data from CSV files to a SQL database.
    The parameters are the file object, the expected header line, a function to
    convert a CSV file line to a list SQL-compatible values,
    a function to validate the SQL-compatible value list, and a function to insert
    multiple of these lines to a SQL database at once.
    Returns True if the upload was successful, otherwise False.
    '''
    if file.filename == '' or not allowed_filename(file.filename):
        return False
    secure_name = secure_filename(file.filename)
    # The file is saved on the server, but removed after reading it has been completed.
    file.save(secure_name)
    with open(secure_name, 'r', encoding='utf-8-sig') as file:
        line = file.readline()
        if line != header:
            os.remove(secure_name)
            return False
        linesize = len(header.split(','))
        sql_form_rows = [] # The rows to be inserted next are collected to this.
        while True:
            rowdata = file.readline().replace('\n', '')
            if not rowdata:
                break
            rowdata = rowdata.split(',')
            if len(rowdata) != linesize:
                continue
            sql_form = csv_row2sql_row(rowdata)
            if len(sql_form) == 0 or not validate_row(sql_form):
                continue
            sql_form_rows.append(sql_form)
            if len(sql_form_rows) == ROWS_INSERTED_AT_ONCE:
                insertoperation(sql_form_rows)
                sql_form_rows = []
        if 0 < len(sql_form_rows):
            insertoperation(sql_form_rows)
    os.remove(secure_name)
    return True

@app.route('/upload/', methods=['GET','POST'])
def upload():
    '''A page with a form to upload new data from CSV files to the SQL database.'''
    errors = []
    if (request.method == 'POST' and (request.files.get('journeys') or request.files.get('stations'))):
        con = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = con.cursor()
        def journey_csv_to_sql(rowdata):
            try:
                return [parser.parse(rowdata[0]),parser.parse(rowdata[1]),rowdata[2],rowdata[4],float(rowdata[6]),float(rowdata[7])]
            except ValueError:
                return []
        def insert_journeys(rows):
            journey_str = ','.join(cur.mogrify('(%s,%s,%s,%s,%s,%s)', journey).decode("utf-8") for journey in rows)
            # The format function is safe with psycopg2.sql objects: https://www.psycopg.org/docs/sql.html
            cur.execute(sql.SQL('''INSERT INTO journeys(departure_time,return_time,departure_station,return_station,distance,duration) VALUES {}''').format(sql.SQL(journey_str)))
        if request.files.get('journeys') and not uploadfile(request.files.get('journeys'), JOURNEY_HEADER, journey_csv_to_sql, lambda row: 10 <= row[4] and 10 <= row[5], insert_journeys):
            errors.append('The journey file is inaccurate')
        def station_csv_to_sql(rowdata):
            try:
                columns = rowdata[1:10]
                columns.extend([int(rowdata[10]),float(rowdata[12]),float(rowdata[11])])
                return columns
            except ValueError:
                return []
        def insert_stations(rows):
            station_str = ','.join(cur.mogrify('(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', station).decode("utf-8") for station in rows)
            cur.execute(sql.SQL('''
            INSERT INTO stations(id,nimi,namn,name,address,adress,city,stad,operator,capacity,lat,lon) VALUES {} ON CONFLICT DO NOTHING
            ''').format(sql.SQL(station_str)))
        if request.files.get('stations') and not uploadfile(request.files.get('stations'), STATION_HEADER, station_csv_to_sql, lambda : True, insert_stations):
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
    # This is how the journeys are ordered by default: primarily departures.name, secondarily returns.name etc.
    # The primary key can be modified with an URL parameter.
    order_params = ['departures.name', 'returns.name', 'distance', 'duration']
    primary_order = request.args.get('order')
    if primary_order in order_params:
        order_params.remove(primary_order)
        order_params.insert(0, primary_order)
    direction = request.args.get('direction')
    direction = '' if not direction else direction
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
    # The journey data is transmitted to the template as a list of dicts.
    row_list = [{'departure_station':str(row[0]),'return_station':str(row[1]),'distance':str(round(float(row[2])/METERS_IN_KILOMETER, DECIMAL_ROUND)),
    'duration':str(round(float(row[3])/SECONDS_IN_MINUTE, DECIMAL_ROUND))} for row in rows]
    # All URL parameters except page are intended to be sustained, but the page links require that the original page parameter is not repassed.
    query = dict(request.args)
    if 'page' in query:
        del query['page']
    # The query parameter is used to set the form input values to the same value as they had with the request.
    # Considered using FlaskForm to achieve the same, but this solution didn't seem too complicated for now.
    # The querystring parameter is used to determine the links used in the next page and former page links.
    return render_template('journeys.html', journeys=row_list, page=page, last=last_page, query=query, querystring=urlencode(query))

@app.route('/stations/')
# I know idd is not a perfect variable name, but id is an inbuilt function and ID would seem like a global constraint.
@app.route('/stations/<idd>/')
def stations(idd=None):
    '''
    The same function is used for both the station list and the single station view.
    If idd is None, the whole list is displayed. Otherwise, a single station view is displayed according to the idd.
    '''
    con = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = con.cursor()
    if not idd:
        cur.execute('SELECT * FROM stations')
        rows = cur.fetchall()
        cur.close()
        con.close()
        row_list = [{'id':str(row[0]),'nimi':str(row[1]),'namn':str(row[2]),'name':str(row[3]),'address':str(row[4]),'adress':str(row[5]),
        'city':str(row[6]),'stad':str(row[7]),'operator':str(row[8]),'capacity':int(row[9]),
        'lat':round(float(row[10]),DECIMAL_ROUND),'lon':round(float(row[11]),DECIMAL_ROUND)}
        for row in rows]
        return render_template('stations.html', stations=row_list)
    # The user can filter the journeys on which the station-specific calculations are based on by their departure and return months.
    # 0 means that all journeys are considered.
    departure = request.args.get('departure')
    departure_year = 0
    departure_month = 0
    if departure != None and re.match(MONTH_PARAM, departure):
        departure_split = departure.split('-')
        departure_year = int(departure_split[1])
        departure_month = int(departure_split[0])
    return_t = request.args.get('return')
    return_year = 0
    return_month = 0
    if return_t != None and re.match(MONTH_PARAM, return_t):
        return_split = return_t.split('-')
        return_year = int(return_split[1])
        return_month = int(return_split[0])
    # Fetch station information not related to journeys.
    cur.execute('''SELECT name, address, lat, lon
    FROM stations
    WHERE stations.id = %s''',(idd,))
    rows = cur.fetchall()
    if len(rows) == 0:
        return Response('No station found with id %s' % idd)
    name = rows[0][0]
    address = rows[0][1]
    lat = rows[0][2]
    lon = rows[0][3]
    # Fetch the numbers of journeys starting from and ending to the station, and their average distances.
    cur.execute('''SELECT COUNT(CASE WHEN journeys.departure_station = %(id)s THEN 1 END), COUNT(CASE WHEN journeys.return_station = %(id)s THEN 1 END),
    AVG(CASE WHEN journeys.departure_station = %(id)s THEN journeys.distance END), AVG(CASE WHEN journeys.return_station = %(id)s THEN journeys.distance END)
    FROM journeys
    WHERE (0 = %(dmonth)s OR (EXTRACT(MONTH FROM journeys.departure_time), EXTRACT(YEAR FROM journeys.departure_time)) = (%(dmonth)s,%(dyear)s)) AND
    (0 = %(rmonth)s OR (EXTRACT(MONTH FROM journeys.return_time), EXTRACT(YEAR FROM journeys.return_time)) = (%(rmonth)s,%(ryear)s))
    ''', {'id': idd, 'dmonth': departure_month, 'dyear': departure_year, 'rmonth': return_month, 'ryear': return_year})
    rows = cur.fetchall()
    starting = int(rows[0][0])
    ending = int(rows[0][1])
    starting_distance = float(rows[0][2]) if rows[0][2] != None else float('nan')
    ending_distance = float(rows[0][3]) if rows[0][3] != None else float('nan')
    # Fetch the most popular return stations for journeys starting from the station.
    cur.execute('''SELECT stations.name, COUNT(*) AS n, stations.id
    FROM journeys
    JOIN stations ON stations.id = journeys.return_station
    WHERE departure_station = %(id)s AND
    ((EXTRACT(MONTH FROM departure_time), EXTRACT(YEAR FROM departure_time)) = (%(dmonth)s,%(dyear)s) OR 0 = %(dmonth)s) AND
    ((EXTRACT(MONTH FROM return_time), EXTRACT(YEAR FROM return_time)) = (%(rmonth)s,%(ryear)s) OR 0 = %(rmonth)s)
    GROUP BY stations.id, stations.name ORDER BY n DESC LIMIT 5''',({'id': idd, 'dmonth': departure_month, 'dyear': departure_year, 'rmonth': return_month, 'ryear': return_year}))
    returns = list(map(lambda x: x[0], cur.fetchall()))
    # Fetch the most popular departure stations for journeys ending at the station.
    cur.execute('''SELECT stations.name, COUNT(*) AS n, stations.id
    FROM journeys
    JOIN stations ON stations.id = journeys.departure_station
    WHERE return_station = %(id)s AND
    ((EXTRACT(MONTH FROM departure_time), EXTRACT(YEAR FROM departure_time)) = (%(dmonth)s,%(dyear)s) OR 0 = %(dmonth)s) AND
    ((EXTRACT(MONTH FROM return_time), EXTRACT(YEAR FROM return_time)) = (%(rmonth)s,%(ryear)s) OR 0 = %(rmonth)s)
    GROUP BY stations.id, stations.name ORDER BY n DESC LIMIT 5''',({'id': idd, 'dmonth': departure_month, 'dyear': departure_year, 'rmonth': return_month, 'ryear': return_year}))
    departures = list(map(lambda x: x[0], cur.fetchall()))
    # Fetch the departure and return months and years appearing in the journeys related to this station.
    # It may seem useless to fetch these on every request, but shouldn't the database be the ultimate source of truth?
    cur.execute('''SELECT EXTRACT(MONTH FROM departure_time) AS departure_month, EXTRACT(YEAR FROM departure_time) AS departure_year
    FROM journeys
    WHERE departure_station = %s
    GROUP BY (departure_year, departure_month)''',(idd,))
    departure_months = cur.fetchall()
    cur.execute('''SELECT EXTRACT(MONTH FROM return_time) AS return_month, EXTRACT(YEAR FROM return_time) AS return_year
    FROM journeys
    WHERE return_station = %s
    GROUP BY (return_year, return_month)''',(idd,))
    return_months = cur.fetchall()
    cur.close()
    con.close()
    return render_template('station.html',name=name, address=address, starting=starting, ending=ending,
    starting_distance=round(starting_distance/METERS_IN_KILOMETER, DECIMAL_ROUND), ending_distance=round(ending_distance/METERS_IN_KILOMETER, DECIMAL_ROUND),
    returns=returns, departures=departures, lat=lat, lon=lon, departuremonths=list(map(lambda x: '{}-{}'.format(x[0],x[1]), departure_months)),
    returnmonths=list(map(lambda x: '{}-{}'.format(x[0],x[1]), return_months)), departure=departure if departure != None else 'anytime',
    return_t=return_t if return_t != None else 'anytime')

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
