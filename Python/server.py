import json

import flask
from flask import request
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

def room_timetable(room_id=None, short_name=None, start_date=None, end_date=None):
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
    if start_date and end_date:
        try:
            start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            cursor.close()
            conn.close()
            return "Invalid date format. Use YYYY-MM-DD.", 400
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
            WHERE te.room = %s AND te.date BETWEEN %s AND %s
            ORDER BY te.date, te.period_start
        """, (room_id, start_date_obj, end_date_obj))
    else:
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

def teacher_timetable(teacher_id=None, short_name=None, start_date=None, end_date=None):
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
    if start_date and end_date:
        try:
            start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            cursor.close()
            conn.close()
            return "Invalid date format. Use YYYY-MM-DD.", 400
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
        WHERE te.teacher = %s AND te.date BETWEEN %s AND %s
        ORDER BY te.date, te.period_start
    """, (teacher_id, start_date_obj, end_date_obj))
    else:
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

# get all entities of a specific type
@app.route("/classes")
def classes():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""-- sql
                    SELECT DISTINCT c.id, c.short_name, c.long_name
                    FROM classes c
                    INNER JOIN timetable_entries te ON te.class_id = c.id
                    ORDER BY c.short_name""")
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
    cursor.execute("""-- sql
                    SELECT DISTINCT r.id, r.short_name, r.long_name
                    FROM rooms r
                    INNER JOIN timetable_entries te ON te.room = r.id
                    ORDER BY r.id""")
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    json_rooms = json.dumps(rooms, default=str)
    return flask.Response(json_rooms, mimetype="application/json")

@app.route("/first_last_entry")
def first_last_entry():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""-- sql
        SELECT MIN(date) AS first_entry, MAX(date) AS last_entry
        FROM timetable_entries
    """)
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    json_result = json.dumps(result, default=str)
    return flask.Response(json_result, mimetype="application/json")

# Get timetable entries for a specific type
@app.route("/class/<int:class_id>")
def class_timetable(class_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT short_name, long_name FROM classes WHERE id = %s", (class_id,))
    class_info = cursor.fetchone()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not class_info:
        cursor.close()
        conn.close()
        return "Class not found", 404
    if start_date and end_date:
        try:
            start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            cursor.close()
            conn.close()
            return "Invalid date format. Use YYYY-MM-DD.", 400
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
            WHERE te.class_id = %s AND te.date BETWEEN %s AND %s
            ORDER BY te.date, te.period_start
        """, (class_id, start_date_obj, end_date_obj))
    else:
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
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    entries = teacher_timetable(teacher_id=teacher_id, start_date=start_date, end_date=end_date)
    json_entries = json.dumps(entries, default=str)
    return flask.Response(json_entries, mimetype="application/json")

@app.route("/teacher/name/<string:short_name>")
def teacher_timetable_by_name(short_name):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    entries = teacher_timetable(short_name=short_name, start_date=start_date, end_date=end_date)
    json_entries = json.dumps(entries, default=str)
    return flask.Response(json_entries, mimetype="application/json")

@app.route("/room/<int:room_id>")
def room_timetable_by_id(room_id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    entries = room_timetable(room_id=room_id, start_date=start_date, end_date=end_date)
    json_entries = json.dumps(entries, default=str)
    return flask.Response(json_entries, mimetype="application/json")

@app.route("/room/name/<string:short_name>")
def room_timetable_by_name(short_name):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    entries = room_timetable(short_name=short_name, start_date=start_date, end_date=end_date)
    json_entries = json.dumps(entries, default=str)
    return flask.Response(json_entries, mimetype="application/json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
