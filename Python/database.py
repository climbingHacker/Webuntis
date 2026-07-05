#!/usr/bin/env python3

import login_config as config

import asyncio
import datetime
import sys
import mysql.connector 
from webuntis_api import WebUntisClient


def init_db(corser):
    corser.execute("CREATE DATABASE IF NOT EXISTS webuntis")
    corser.execute("USE webuntis")
    corser.execute("""-- sql
        CREATE TABLE IF NOT EXISTS classes (
            id INT PRIMARY KEY,
            short_name VARCHAR(255) NOT NULL,
            long_name VARCHAR(255),
            fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) WITH SYSTEM VERSIONING
    """)
    corser.execute("""-- sql
        CREATE TABLE IF NOT EXISTS subjects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            short_name VARCHAR(255) NOT NULL,
            long_name VARCHAR(255)
        ) WITH SYSTEM VERSIONING
    """)
    corser.execute("""-- sql
        CREATE TABLE IF NOT EXISTS teachers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            short_name VARCHAR(255) NOT NULL,
            long_name VARCHAR(255)
        ) WITH SYSTEM VERSIONING
    """)
    corser.execute("""-- sql
        CREATE TABLE IF NOT EXISTS rooms (
            id INT AUTO_INCREMENT PRIMARY KEY,
            short_name VARCHAR(255) NOT NULL,
            long_name VARCHAR(255)
        ) WITH SYSTEM VERSIONING
    """)
    corser.execute("""-- sql
        CREATE TABLE IF NOT EXISTS timetable_entries (
            id INT AUTO_INCREMENT PRIMARY KEY,
            upstream_id INT NOT NULL,
            class_id INT NOT NULL,
            date DATE NOT NULL,
            period_start TIME NOT NULL,
            period_end TIME NOT NULL,
            type VARCHAR(255) NOT NULL,
            status VARCHAR(255) NOT NULL,
            status_detail VARCHAR(255),
            subject INT,
            teacher INT,
            room INT,
            fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject) REFERENCES subjects(id),
            FOREIGN KEY (teacher) REFERENCES teachers(id),
            FOREIGN KEY (room) REFERENCES rooms(id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
        ) WITH SYSTEM VERSIONING
    """)
    corser.execute("""-- sql
        CREATE TABLE IF NOT EXISTS last_update (
            id INT PRIMARY KEY CHECK (id = 1),
            last_update_timestamp TIMESTAMP NOT NULL,
            checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) WITH SYSTEM VERSIONING
    """)
    corser.execute("""-- sql
        CREATE INDEX IF NOT EXISTS idx_timetable_class_date
            ON timetable_entries(class_id, date)
    """)
    corser.execute("""-- sql
        CREATE INDEX IF NOT EXISTS idx_timetable_fetched
            ON timetable_entries(fetched_at)
    """)

def fetch_and_store_rooms(corser, conn, untis_client):
    rooms = untis_client.json_get_rooms()
    for room in rooms.get("result", []):
        corser.execute(
            "SELECT id FROM rooms WHERE short_name = %s",
            (room['name'],)
        )
        old_id = corser.fetchone()
        if old_id:
            old_id = old_id[0]
            if old_id != room['id']:
                corser.execute(
                    "INSERT INTO rooms (id, short_name, long_name) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE long_name = VALUES(long_name)",
                    (room['id'], room['name'], room.get('longName'))
                )
                corser.execute(
                    "UPDATE timetable_entries SET room = %s WHERE room = %s",
                    (room['id'], old_id)
                )
                corser.execute(
                    "DELETE FROM rooms WHERE id = %s",
                    (old_id,)
                )
        else:
            corser.execute(
                "INSERT INTO rooms (id, short_name, long_name) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
                (room['id'], room['name'], room.get('longName'))
            )
    conn.commit()

def fetch_and_store_classes(corser, conn, untis_client):
    classes = untis_client.json_get_classes()
    for class_info in classes.get("result", []):
        corser.execute(
            "SELECT id FROM classes WHERE short_name = %s",
            (class_info['name'],)
        )
        old_id = corser.fetchone()
        if old_id:
            old_id = old_id[0]
            if old_id != class_info['id']:
                corser.execute(
                    "INSERT INTO classes (id, short_name, long_name) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE long_name = VALUES(long_name)",
                    (class_info['id'], class_info['name'], class_info.get('longName'))
                )
                corser.execute(
                    "UPDATE timetable_entries SET class_id = %s WHERE class_id = %s",
                    (class_info['id'], old_id)
                )
                corser.execute(
                    "DELETE FROM classes WHERE id = %s",
                    (old_id,)
                )
        else:
            corser.execute(
                "INSERT INTO classes (id, short_name, long_name) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
                (class_info['id'], class_info['name'], class_info.get('longName'))
            )
    conn.commit()

def store_timetable_entries(corser, conn, class_id, entries):
        for e in entries:
            # TODO: insert in db
            teacher_id = None
            subject_id = None
            room_id = None
            if e.get('teacher'):
                corser.execute("SELECT id FROM teachers WHERE short_name = %s", (e.get('teacher'),))
                row = corser.fetchone()
                if row:
                    teacher_id = row[0]
                else:
                    corser.execute(
                        "INSERT INTO teachers (short_name, long_name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
                        (e.get('teacher'), e.get('teacherLong'))
                    )
                    teacher_id = corser.lastrowid
            if e.get('subject'):
                corser.execute("SELECT id FROM subjects WHERE short_name = %s", (e.get('subject'),))
                row = corser.fetchone()
                if row:
                    subject_id = row[0]
                else:
                    corser.execute(
                        "INSERT INTO subjects (short_name, long_name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
                        (e.get('subject'), e.get('subjectLong'))
                    )
                    subject_id = corser.lastrowid
            if e.get('room'):
                corser.execute("SELECT id FROM rooms WHERE short_name = %s", (e.get('room'),))
                row = corser.fetchone()
                if row:
                    room_id = row[0]
                else:
                    corser.execute(
                        "INSERT INTO rooms (short_name, long_name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
                        (e.get('room'), e.get('roomLong'))
                    )
                    room_id = corser.lastrowid
            corser.execute(
                "SELECT id FROM timetable_entries WHERE upstream_id = %s AND class_id = %s",
                (e.get('upstreamId'), class_id)
            )
            if corser.fetchone():
                sql = """-- sql\n UPDATE timetable_entries SET date = %s, period_start = %s, period_end = %s, type = %s, status = %s, status_detail = %s, subject = %s, teacher = %s, room = %s WHERE upstream_id = %s AND class_id = %s
                """
            else:
                sql = """-- sql\n INSERT INTO timetable_entries (upstream_id, class_id, date, period_start, period_end, type, status, status_detail, subject, teacher, room) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            corser.execute(sql, (
                e.get('upstreamId'),
                class_id,
                e['date'],
                e['startTime'],
                e['endTime'],
                e['type'],
                e['status'],
                e.get('statusDetail'),
                subject_id,
                teacher_id,
                room_id
            ))
            conn.commit()
            continue

def get_stored_last_update(corser, conn):
    row = corser.execute(
        "SELECT last_update_timestamp FROM last_update WHERE id = 1"
    ).fetchone()
    return datetime.datetime.fromisoformat(row[0]) if row else None

def set_stored_last_update(corser, conn, dt):
    corser.execute(
        "INSERT OR REPLACE INTO last_update (id, last_update_timestamp) VALUES (1, ?)",
        (dt.isoformat(),),
    )
    conn.commit()

def fetch_and_store_class_timetable(corser, conn, untis_client, class_id, start_date, end_date):
    # Fetch timetable from WebUntis API
    raw_data = untis_client.get_raw_timetable_rest_class(class_id, start_date, end_date)
    
    flat_entries = []
    for day in raw_data.get('days', []):
        for entry in day.get('gridEntries', []):
            parsed = {}
            for pos_num in range(1, 8):
                untis_client.parse_positionx(entry.get(f'position{pos_num}', []), parsed)
            dur = entry.get('duration', {})
            flat_entries.append({
                'upstreamId': (entry.get('ids') or [None])[0],
                'date': day['date'],
                'startTime': dur.get('start'),
                'endTime': dur.get('end'),
                'type': entry.get('type'),
                'status': entry.get('status'),
                'statusDetail': entry.get('statusDetail'),
                'teacher': (parsed.get('teacherShort') or [None])[0],
                'teacherLong': (parsed.get('teacher') or [None])[0],
                'subject': parsed.get('subject'),
                'subjectLong': parsed.get('subjectLong'),
                'room': parsed.get('room'),
                'roomLong': parsed.get('roomLong'),
            })
    
    store_timetable_entries(corser, conn, class_id, flat_entries)

def fetch_and_store_timetable(corser, conn, untis_client, start_date, end_date):
    classes = untis_client.json_get_classes()
    for class_info in classes.get("result", []):
        class_id = class_info['id']
        corser.execute(
            "INSERT INTO classes (id, short_name, long_name) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
            (class_info['id'], class_info['name'], class_info.get('longName'))
        )
        conn.commit()

        fetch_and_store_class_timetable(corser, conn, untis_client, class_id, start_date, end_date)



async def main():
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )
    untis_client = WebUntisClient(config.SCHOOL, config.SERVER_URL, config.USERNAME, config.KEY)
    corser = conn.cursor(buffered=True)
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=7)  # Get the Monday of the previous week
    friday = monday + datetime.timedelta(days=4) + datetime.timedelta(days=7)  # Get the Friday of the previous week
    init_db(corser)
    # fetch_and_store_timetable(corser, conn, untis_client, monday, friday)
    fetch_and_store_rooms(corser, conn, untis_client)
    fetch_and_store_classes(corser, conn, untis_client)
    conn.commit()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
