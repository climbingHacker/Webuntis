import json

import flask
import mysql.connector
import login_config as config
import datetime

app = flask.Flask(__name__,
    static_url_path='',
    static_folder='.',
    template_folder='.')

def get_db():
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )
    return conn

def room_timetable(room_id=None, short_name=None):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    if room_id is None and short_name is None:
        return "Room ID or short name must be provided", 400
    elif room_id is None:
        cursor.execute("SELECT id FROM rooms WHERE short_name = %s", (short_name,))
        room_info = cursor.fetchone()
        if not room_info:
            cursor.close()
            conn.close()
            return "Room not found", 404
        room_id = room_info.get('id')
    cursor.execute("SELECT short_name, long_name FROM rooms WHERE id = %s", (room_id,))
    room_info = cursor.fetchone()
    if not room_info:
        cursor.close()
        conn.close()
        return "Room not found", 404
    cursor.execute("""-- sql
        SELECT te.upstream_id, te.date, te.period_start, te.period_end,
               te.type, te.status, te.status_detail,
               s.short_name AS subject, s.long_name AS subject_long,
               c.short_name AS class, c.long_name AS class_long,
               t.short_name AS teacher, t.long_name AS teacher_long,
               r.short_name AS room, r.long_name AS room_long
        FROM timetable_entries te
        LEFT JOIN subjects s ON te.subject = s.id
        LEFT JOIN classes c ON te.class_id = c.id
        LEFT JOIN teachers t ON te.teacher = t.id
        LEFT JOIN rooms r ON te.room = r.id
        WHERE te.room = %s
        ORDER BY te.date, te.period_start
    """, (room_id,))
    entries = cursor.fetchall()
    cursor.close()
    conn.close()
    return entries

def teacher_timetable(teacher_id=None, short_name=None):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    if teacher_id is None and short_name is None:
        return "Teacher ID or short name must be provided", 400
    elif teacher_id is None:
        cursor.execute("SELECT id FROM teachers WHERE short_name = %s", (short_name,))
        teacher_info = cursor.fetchone()
        if not teacher_info:
            cursor.close()
            conn.close()
            return "Teacher not found", 404
        teacher_id = teacher_info.get('id')
    cursor.execute("SELECT short_name, long_name FROM teachers WHERE id = %s", (teacher_id,))
    teacher_info = cursor.fetchone()
    if not teacher_info:
        cursor.close()
        conn.close()
        return "Teacher not found", 404

    cursor.execute("""-- sql
        SELECT te.upstream_id, te.date, te.period_start, te.period_end,
               te.type, te.status, te.status_detail,
               s.short_name AS subject, s.long_name AS subject_long,
               c.short_name AS class, c.long_name AS class_long,
               r.short_name AS room, r.long_name AS room_long
        FROM timetable_entries te
        LEFT JOIN subjects s ON te.subject = s.id
        LEFT JOIN classes c ON te.class_id = c.id
        LEFT JOIN rooms r ON te.room = r.id
        WHERE te.teacher = %s
        ORDER BY te.date, te.period_start
    """, (teacher_id,))
    entries = cursor.fetchall()
    cursor.close()
    conn.close()
    return entries

def time_grid_number(self, start, end):
        """Calculate the time grid number for WebUntis API."""
        match start:
            case _ if start <= datetime.time(hour=8, minute=0):
                grid_number_start = 1
            case datetime.time(hour=8, minute=55):
                grid_number_start = 2
            case datetime.time(hour=9, minute=50):
                grid_number_start = 3
            case datetime.time(hour=10, minute=55):
                grid_number_start = 4
            case datetime.time(hour=11, minute=50):
                grid_number_start = 5
            case datetime.time(hour=12, minute=45):
                grid_number_start = 6
            case datetime.time(hour=13, minute=40):
                grid_number_start = 7
            case datetime.time(hour=14, minute=30):
                grid_number_start = 8
            case datetime.time(hour=15, minute=20):
                grid_number_start = 9
            case datetime.time(hour=16, minute=10):
                grid_number_start = 10
            case _ if start >= datetime.time(hour=17, minute=0):
                grid_number_start = 11
            case _:
                raise ValueError("Invalid start time")
        match end:
            case end if end <= datetime.time(hour=8, minute=50):
                grid_number_end = 1
            case datetime.time(hour=9, minute=45):
                grid_number_end = 2
            case datetime.time(hour=10, minute=40):
                grid_number_end = 3
            case datetime.time(hour=11, minute=45):
                grid_number_end = 4
            case datetime.time(hour=12, minute=40):
                grid_number_end = 5
            case datetime.time(hour=13, minute=35):
                grid_number_end = 6
            case datetime.time(hour=14, minute=30):
                grid_number_end = 7
            case datetime.time(hour=15, minute=20):
                grid_number_end = 8
            case datetime.time(hour=16, minute=10):
                grid_number_end = 9
            case datetime.time(hour=17, minute=0):
                grid_number_end = 10
            case _ if end >= datetime.time(hour=17, minute=50):
                grid_number_end = 11
            case _:
                raise ValueError("Invalid end time")
        return grid_number_start, grid_number_end

def parse_timegrid(tt):
    for i in range(len(tt)):
        entry = tt[i]
        start_time = entry.get('period_start')
        end_time = entry.get('period_end')
        print(type(start_time), type(end_time))
        if start_time and end_time:
            start_time_obj = (datetime.datetime.min + start_time).time()
            end_time_obj = (datetime.datetime.min + end_time).time()
            grid_start, grid_end = time_grid_number(None, start_time_obj, end_time_obj)
            tt[i]['period_start'] = grid_start
            tt[i]['period_end'] = grid_end
            tt[i]['start_time'] = start_time_obj.time()
            tt[i]['end_time'] = end_time_obj.time()
    return tt

# get all entities of a specific type
@app.route("/classes")
def classes():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, short_name, long_name FROM classes ORDER BY short_name")
    classes = cursor.fetchall()
    cursor.close()
    conn.close()
    json_classes = json.dumps(classes, default=str)
    return flask.Response(json_classes, mimetype="application/json")

@app.route("/teachers")
def teachers():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, short_name, long_name FROM teachers ORDER BY short_name")
    teachers = cursor.fetchall()
    cursor.close()
    conn.close()
    json_teachers = json.dumps(teachers, default=str)
    return flask.Response(json_teachers, mimetype="application/json")

@app.route("/rooms")
def rooms():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, short_name, long_name FROM rooms ORDER BY short_name")
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    json_rooms = json.dumps(rooms, default=str)
    return flask.Response(json_rooms, mimetype="application/json")

# Get timetable entries for a specific type
@app.route("/class/<int:class_id>")
def class_timetable(class_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT short_name, long_name FROM classes WHERE id = %s", (class_id,))
    class_info = cursor.fetchone()
    if not class_info:
        cursor.close()
        conn.close()
        return "Class not found", 404

    cursor.execute("""-- sql
        SELECT te.upstream_id, te.date, te.period_start, te.period_end,
               te.type, te.status, te.status_detail,
               s.short_name AS subject, s.long_name AS subject_long,
               t.short_name AS teacher, t.long_name AS teacher_long,
               r.short_name AS room, r.long_name AS room_long
        FROM timetable_entries te
        LEFT JOIN subjects s ON te.subject = s.id
        LEFT JOIN teachers t ON te.teacher = t.id
        LEFT JOIN rooms r ON te.room = r.id
        WHERE te.class_id = %s
        ORDER BY te.date, te.period_start
    """, (class_id,))
    entries = cursor.fetchall()
    cursor.close()
    conn.close()
    json_entries = json.dumps(entries, default=str)
    return flask.Response(json_entries, mimetype="application/json")

@app.route("/teacher/<int:teacher_id>")
def teacher_timetable_by_id(teacher_id):
    entries = parse_timegrid(teacher_timetable(teacher_id=teacher_id))
    json_entries = json.dumps(entries, default=str)
    return flask.Response(json_entries, mimetype="application/json")

@app.route("/teacher/name/<string:short_name>")
def teacher_timetable_by_name(short_name):
    entries = parse_timegrid(teacher_timetable(short_name=short_name))
    json_entries = json.dumps(entries, default=str)
    return flask.Response(json_entries, mimetype="application/json")

@app.route("/room/<int:room_id>")
def room_timetable_by_id(room_id):
    entries = parse_timegrid(room_timetable(room_id=room_id))
    json_entries = json.dumps(entries, default=str)
    return flask.Response(json_entries, mimetype="application/json")

@app.route("/room/name/<string:short_name>")
def room_timetable_by_name(short_name):
    entries = parse_timegrid(room_timetable(short_name=short_name))
    json_entries = json.dumps(entries, default=str)
    return flask.Response(json_entries, mimetype="application/json")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
