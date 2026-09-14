#!/usr/bin/env python
import datetime
import json
import requests
import re
import pyotp
from collections import defaultdict
import login_config as login_config
from bs4 import BeautifulSoup

# Configuration
KEY = login_config.KEY  # Key used to generate the OTP
SCHOOL = login_config.SCHOOL        # WebUntis school name
USERNAME = login_config.USERNAME # WebUntis username
SERVER_URL = login_config.SERVER_URL  # WebUntis server URL

class WebUntisClient():
    def __init__(self, school, server_url, username, key):
        self.school = school
        self.server_url = server_url
        self.username = username
        self.key = key
        self.jsessionid = None
        self.token = None

        totp = pyotp.TOTP(key, interval=30)
        self.login(self.school, self.server_url, totp.now(), self.username, int(datetime.datetime.now().timestamp() * 1000))

    def login(self, scname, server, token, username, time=None):
        """Login to WebUntis using OTP and get session cookie."""
        if time is None:
            time = int(datetime.datetime.now().timestamp() * 1000)
        url = f"{server}/WebUntis/jsonrpc_intern.do"
        headers = {'Content-Type': 'application/json'}
        data = {
            'id': 'Awesome',
            'method': 'getUserData2017',
            'params': [
                {
                    'auth': {
                        'clientTime': time,
                        'user': username,
                        'otp': token,
                    },
                },
            ],
            'jsonrpc': '2.0',
        }
        params = {
            'm': 'getUserData2025',
            'school': scname,
            'v': 'i2.2',
        }
        
        response = requests.post(url, json=data, headers=headers, params=params)
        
        if 'set-cookie' in response.headers:
            cookie_parts = response.headers['set-cookie'].split('; ')
            jsessionid = None
            
            for part in cookie_parts:
                if part.startswith('JSESSIONID='):
                    jsessionid = part[len('JSESSIONID='):]
                    break
                    
            if jsessionid:
                headers = {
                    'Accept': 'application/json, text/plain, */*',
                    'Content-Type': 'application/json'
                    }
                response = requests.get(f"{self.server_url}/WebUntis/api/token/new", headers=headers, cookies={'JSESSIONID': jsessionid})
                token = response.text
                self.jsessionid = jsessionid
                self.token = token
            else:
                raise Exception("Failed to login: No session cookie found")

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

    def get_weekday_string(self, weekday):
        match weekday:
            case 0:
                weekdayStr = "Monday"
                weekdayStrShort = "mo"
            case 1:
                weekdayStr = "Tuesday"
                weekdayStrShort = "tu"
            case 2:
                weekdayStr = "Wednesday"
                weekdayStrShort = "we"
            case 3:
                weekdayStr = "Thursday"
                weekdayStrShort = "th"
            case 4:
                weekdayStr = "Friday"
                weekdayStrShort = "fr"
            case 5:
                weekdayStr = "Saturday"
                weekdayStrShort = "sa"
            case 6:
                weekdayStr = "Sunday"
                weekdayStrShort = "su"
            case _:
                raise ValueError("Invalid weekday")
            
        return weekdayStrShort, weekdayStr

    def create_empty_timetable(self):
        days = ["mo", "tu", "we", "th", "fr"]
        timetable = {}
        for day in days:
            timetable[day] = {lesson: {} for lesson in range(1, 12)}
        return timetable

    def jsonrpc_call(self, method, params=None, id=None):
        url = f"{self.server_url}/WebUntis/jsonrpc.do"
        headers = {
            'Content-Type': 'application/json',
            'Cookie': f'JSESSIONID={self.jsessionid}'
        }
        data = {
            'id': id or method,
            'method': method,
            'params': params or {},
            'jsonrpc': '2.0'
        }
        response = requests.post(url, json=data, headers=headers)
        return response.json()

    def json_get_teachers(self):
        """Get list of all teachers using JSON-RPC API 

        :return: return object containing all teachers
        :rtype: dict
        """        
        response = self.jsonrpc_call('getTeachers', id='get_teachers')
        return response

    def json_get_students(self):
        """Get list of all students using JSON-RPC API

        :return: return object containing all students
        :rtype: dict
        """
        response = self.jsonrpc_call('getStudents', id='get_students')
        return response

    def json_get_classes(self, year=None):
        """Get list of all classes using JSON-RPC API

        :return: return object containing all classes
        :rtype: dict
        :param year: schoolyear id 
        :type year: int, optional
        """
        params = {}
        if year is not None:
            params['year'] = year
        response = self.jsonrpc_call('getKlassen', params=params, id='get_classes')
        return response

    def json_get_subjects(self):
        """Get list of all subjects using JSON-RPC API

        :return: return object containing all subjects
        :rtype: dict
        """
        response = self.jsonrpc_call('getSubjects', id='get_subjects')
        return response

    def json_get_rooms(self):
        """Get list of all rooms using JSON-RPC API

        :return: return object containing all rooms
        :rtype: dict
        """
        response = self.jsonrpc_call('getRooms', id='get_rooms')
        return response

    def json_get_departments(self):
        """Get list of all departments using JSON-RPC API

        :return: return object containing all departments
        :rtype: dict
        """
        response = self.jsonrpc_call('getDepartments', id='get_departments')
        return response

    def json_get_holidays(self):
        """Get list of all holidays using JSON-RPC API

        :return: return object containing all holidays
        :rtype: dict
        """
        response = self.jsonrpc_call('getHolidays', id='get_holidays')
        return response

    def json_get_timegrid(self):
        """Get the timegrid using JSON-RPC API

        :return: return object containing the timegrid
        :rtype: dict
        """
        response = self.jsonrpc_call('getTimegrid', id='get_timegrid')
        return response

    def json_get_status_data(self):
        """Get status data using JSON-RPC API

        :return: return object containing the status data
        :rtype: dict
        """
        response = self.jsonrpc_call('getStatusData', id='get_statusData')
        return response

    def json_get_current_schoolyear(self):
        """Get the current schoolyear using JSON-RPC API

        :return: return object containing the current schoolyear
        :rtype: dict
        """
        response = self.jsonrpc_call('getCurrentSchoolyear', id='get_currentSchoolyear')
        return response

    def json_get_schoolyears(self):
        """Get a list of schoolyears using JSON-RPC API

        :return: return object containing the schoolyears
        :rtype: dict
        """
        response = self.jsonrpc_call('getSchoolyears', id='get_schoolyears')
        return response

    def json_get_timetable(self, start_date, end_date, element_type, element_id):
        """Fetch timetable data using JSON-RPC API.
        
        :param start_date: 
        :type start_date: datetime.datetime
        :param end_date: _description_
        :type end_date: datetime.datetime
        :param element_type: - 1 = klasse (class)
        - 2 = teacher
        - 3 = subject
        - 4 = room
        - 5 = student
        
        :type element_type: int
        :param element_id: _description_
        :type element_id: int
        :return: list of timetable entries for the specified element and date range
        :rtype: dict
        """
        
        # Convert datetime to WebUntis format (YYYYMMDD)
        start_formatted = start_date.strftime("%Y%m%d")
        end_formatted = end_date.strftime("%Y%m%d")
        
        params = {
                'options': {
                    'element': {
                        'id': element_id,
                        'type': element_type
                    },
                    'startDate': start_formatted,
                    'endDate': end_formatted,
                    'showStudentgroup': True,
                    'showLsText': True,
                    'showLsNumber': True,
                    'showInfo': True,
                    'showBooking': True,
                    'klasseFields': ["id", "name", "longname", "externalkey"],
                    'roomFields': ["id", "name", "longname", "externalkey"],
                    'subjectFields': ["id", "name", "longname", "externalkey"],
                    'teacherFields': ["id", "name", "longname", "externalkey"]
                }
            }
        
        response = self.jsonrpc_call('getTimetable', params=params, id='get_timetable')
        return response

    def json_get_last_update(self):
        """Get the last update timestamp using JSON-RPC API

        :return: return object containing the last update timestamp
        :rtype: dict
        """
        response = self.jsonrpc_call('getLastUpdate', id='get_last_update')
        return response

    def get_person_id(self, person_type, first_name, last_name):
        """Get the ID of a person (teacher or student) by their first and last name.

        :param person_type: Type of person (2 for teacher, 5 for student)
        :type person_type: int
        :param first_name: First name of the person
        :type first_name: str
        :param last_name: Last name of the person
        :type last_name: str
        :return: ID of the person if found, otherwise None
        :rtype: int or None
        """

        params = {
            'type': person_type,
            'fn': first_name,
            'sn': last_name,
            'dob': 0
        }
        response = self.jsonrpc_call('getPersonId', params=params, id='get_person_id')
        return response
    
    def get_raw_timetable_rest_class(self, classID, start_date, end_date):
        url = f"{self.server_url}/WebUntis/api/rest/view/v1/timetable/entries?start={start_date.isoformat()}&end={end_date.isoformat()}&format=1&resourceType=CLASS&resources={str(classID)}&periodTypes=&timetableType=STANDARD"    
        cookies = {
            'JSESSIONID': self.jsessionid
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}',
        }
        
        response = requests.get(url, headers=headers, cookies=cookies)
        return response.json()

    def get_timetable_rest_teacher(self, teacherShort, start_date, end_date):
        # Get all classes
        classes_data = self.json_get_classes()
        timetable = self.create_empty_timetable()

        # Iterate through each class and search for lessons with the specified teacher
        class_id = None
        for klasse in classes_data.get('result', []):
            
            class_id = klasse.get('id')
            class_name = klasse.get('name')
            timetableClass = self.get_raw_timetable_rest_class(class_id, start_date, end_date)

            for day in timetableClass.get('days', []):
                for entry in day.get('gridEntries', []):
                    i = 1
                    try:
                        parsed_entry = {}
                        while i <= 7:
                            self.parse_positionx(entry.get(f'position{i}'), parsed_entry)
                            i += 1
                    except Exception as e:
                        print(f"Error parsing position {i}: {e}")
                        continue
                    if not parsed_entry.get("teacherShort"):
                        continue
                    if any(teacher.lower() == teacherShort.lower() for teacher in parsed_entry.get("teacherShort")):
                        startTime = datetime.datetime.fromisoformat(entry.get('duration').get('start')).time()
                        endTime = datetime.datetime.fromisoformat(entry.get('duration').get('end')).time()
                        weekday = datetime.datetime.fromisoformat(day.get('date')).weekday()
                        weekdayStrShort, weekdayStr = self.get_weekday_string(weekday)
                        start_lesson, end_lesson = self.time_grid_number(startTime, endTime)
                        
                        ltype = entry.get('type')
                        status = entry.get('status')                                                   
                        if status != "REGULAR":
                            timetable[weekdayStrShort][start_lesson]["statusDetail"] = entry.get('statusDetail')
                        
                        timetable[weekdayStrShort][start_lesson]["type"] = ltype
                        timetable[weekdayStrShort][start_lesson]["status"] = status    
                        
                        if not parsed_entry.get("class", None):
                            parsed_entry["class"] = []
                        parsed_entry["class"].append(class_name)
                        
                        for lessonNumber in range(start_lesson, end_lesson + 1):
                            timetable[weekdayStrShort][lessonNumber] = parsed_entry
                        #print('Found ' + parsed_entry.get("subjectLong") + ' in class ' + class_name + ' in ' + parsed_entry.get("room") + ' on ' + weekdayStr)
        return timetable

    def get_timetable_rest_room(self, roomNumber, start_date, end_date):
        # Get all classes
        classes_data = self.json_get_classes()
        timetable = self.create_empty_timetable()
        
        # Iterate through each class and search for lessons with the specified teacher
        class_id = None
        for klasse in classes_data.get('result', []):
            
            class_id = klasse.get('id')
            class_name = klasse.get('name')
            timetableClass = self.get_raw_timetable_rest_class(class_id, start_date, end_date)
            
            for day in timetableClass.get('days', []):
                for entry in day.get('gridEntries', []):
                    try:
                        parsed_entry = {}
                        i = 1
                        while i <= 7:
                            self.parse_positionx(entry.get(f'position{i}'), parsed_entry)
                            i += 1
                    except Exception as e:
                        print(f"Error parsing position {i}: {e}")
                        continue
                    if not parsed_entry.get("room", None):
                        continue
                    if roomNumber == parsed_entry.get("room"):
                        startTime = datetime.datetime.fromisoformat(entry.get('duration').get('start')).time()
                        endTime = datetime.datetime.fromisoformat(entry.get('duration').get('end')).time()
                        weekday = datetime.datetime.fromisoformat(day.get('date')).weekday()
                        weekdayStrShort, weekdayStr = self.get_weekday_string(weekday)
                        start_lesson, end_lesson = self.time_grid_number(startTime, endTime)
                        
                        ltype = entry.get('type')
                        status = entry.get('status')                                                   
                        if status != "REGULAR":
                            timetable[weekdayStrShort][start_lesson]["statusDetail"] = entry.get('statusDetail')
                        
                        timetable[weekdayStrShort][start_lesson]["type"] = ltype
                        timetable[weekdayStrShort][start_lesson]["status"] = status    
                        
                        if not parsed_entry.get("class", None):
                            parsed_entry["class"] = []
                        parsed_entry["class"].append(class_name)
                        
                        for lessonNumber in range(start_lesson, end_lesson + 1):
                            timetable[weekdayStrShort][lessonNumber] = parsed_entry
                        try:
                            print(f'Found {parsed_entry.get("subjectLong")} in class {class_name} with {parsed_entry.get("teacher")} on {weekdayStr}')
                        except Exception as e:
                            print(f'Found in class {class_name} on {weekdayStr}')
        return timetable

    def parse_timetable_rest(self, timetableJSON):
        timetable = self.create_empty_timetable()
        
        for day in timetableJSON.get('days', []):
            for entry in day.get('gridEntries', []):
                dur = entry.get('duration', {})
                start = dur.get('start')
                end = dur.get('end')
                id = entry.get('ids')[0] if entry.get('ids') else None
                if not start or not end:
                    continue
                
                try:
                    start_time = datetime.datetime.fromisoformat(start).time()
                    end_time = datetime.datetime.fromisoformat(end).time()
                except ValueError:
                    continue
                
                weekday = datetime.datetime.fromisoformat(day.get('date', '')).weekday() if day.get('date') else 0
                weekday_str_short, _ = self.get_weekday_string(weekday)
                
                start_lesson, end_lesson = self.time_grid_number(start_time, end_time)
                
                parsed = {}
                for pos_num in range(1, 8):
                    pos_list = entry.get(f'position{pos_num}', [])
                    parsed = self.parse_positionx(pos_list, parsed)
                
                class_name = day.get('resource', {}).get('shortName')
                
                ltype = entry.get('type')
                status = entry.get('status')
                status_detail = entry.get('statusDetail') if status != 'REGULAR' else None
                
                for lesson in range(start_lesson, end_lesson + 1):
                    if lesson > 11:
                        continue
                    timetable[weekday_str_short][lesson] = {
                        'upstreamId': id,
                        'class': class_name,
                        'subject': parsed.get('subject'),
                        'subjectLong': parsed.get('subjectLong'),
                        'room': parsed.get('room'),
                        'roomLong': parsed.get('roomLong'),
                        'teacher': parsed.get('teacher'),
                        'teacherShort': parsed.get('teacherShort'),
                        'type': ltype,
                        'status': status,
                        'statusDetail': status_detail,
                    }
        
        return timetable

    def parse_positionx(self, raw_data, timetable_entry):
        if not raw_data:
            return timetable_entry
        
        for item in raw_data:
            current = item.get('current')
            if current:
                ptype = current.get('type')
                if ptype == 'TEACHER':
                    timetable_entry.setdefault('teacher', []).append(current.get('longName'))
                    timetable_entry.setdefault('teacherShort', []).append(current.get('shortName'))
                    timetable_entry.setdefault('teacherStatus', []).append(current.get('status'))
                elif ptype == 'CLASS':
                    timetable_entry.setdefault('class', []).append(current.get('shortName'))
                    timetable_entry.setdefault('classStatus', []).append(current.get('status'))
                elif ptype == 'SUBJECT':
                    timetable_entry['subject'] = current.get('shortName')
                    timetable_entry['subjectLong'] = current.get('longName')
                    timetable_entry['subjectStatus'] = current.get('status')
                elif ptype == 'ROOM':
                    timetable_entry['room'] = current.get('shortName')
                    timetable_entry['roomLong'] = current.get('longName')
            
            removed = item.get('removed')
            if removed:
                rtype = removed.get('type')
                if rtype == 'TEACHER':
                    timetable_entry.setdefault('oldteacher', []).append(removed.get('longName'))
                    timetable_entry.setdefault('oldteacherShort', []).append(removed.get('shortName'))
                    timetable_entry.setdefault('oldteacherStatus', []).append(removed.get('status'))
                elif rtype == 'CLASS':
                    timetable_entry.setdefault('oldclass', []).append(removed.get('shortName'))
                    timetable_entry.setdefault('oldclassStatus', []).append('REMOVED')
                elif rtype == 'SUBJECT':
                    timetable_entry['oldsubject'] = removed.get('shortName')
                    timetable_entry['oldsubjectLong'] = removed.get('longName')
                    timetable_entry['oldsubjectStatus'] = 'REMOVED'
                elif rtype == 'ROOM':
                    timetable_entry['oldroom'] = removed.get('shortName')
                    timetable_entry['oldroomLong'] = removed.get('longName')
        
        return timetable_entry

    def last_update(self):
        url = f"{self.server_url}/WebUntis/main.do"
        cookies = {
            'JSESSIONID': self.jsessionid
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}',
        }
        
        response = requests.get(url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.text, 'html.parser')
        last_update_element = soup.find(string=re.compile("Letzte Planaktualisierung aus Untis"))
        last_update_string = re.sub(r'Letzte Planaktualisierung aus Untis: .*, ', '', last_update_element)
        last_update = datetime.datetime.strptime(last_update_string, '%d.%m.%Y %H:%M:%S')
        
        return last_update

def main():
    try:
        WebUntis = WebUntisClient(SCHOOL, SERVER_URL, USERNAME, KEY)
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        friday = monday + datetime.timedelta(days=4)
        print(f"Fetching timetable from {monday} to {friday}...")
        #timetable_data = WebUntis.get_timetable_rest_room(credentinals, 'A313', monday, friday)
        timetable_data = WebUntis.get_timetable_rest_teacher('STEL', monday, friday)
        teachers = WebUntis.json_get_teachers()
        rooms = WebUntis.json_get_rooms()
        classes = WebUntis.json_get_classes()
        timegrid = WebUntis.json_get_timegrid()
        with open('teachers.json', 'w', encoding='utf-8') as f:
            json.dump(teachers, f, ensure_ascii=False, indent=4)
        with open('rooms.json', 'w', encoding='utf-8') as f:
            json.dump(rooms, f, ensure_ascii=False, indent=4)
        with open('classes.json', 'w', encoding='utf-8') as f:
            json.dump(classes, f, ensure_ascii=False, indent=4)
        with open('timegrid.json', 'w', encoding='utf-8') as f:
            json.dump(timegrid, f, ensure_ascii=False, indent=4)
        with open('timetable2.json', 'w', encoding='utf-8') as f:
            json.dump(timetable_data, f, ensure_ascii=False, indent=4)
        print("Timetable saved to timetable2.json")
        timetable_data = WebUntis.get_raw_timetable_rest_class(4434, monday, friday)
        with open('timetable.json', 'w', encoding='utf-8') as f:
            json.dump(timetable_data, f, ensure_ascii=False, indent=4)
        print("Timetable saved to timetable.json")
    except Exception as e:
        print(f"Error: {e}")
if __name__ == "__main__":
    main()