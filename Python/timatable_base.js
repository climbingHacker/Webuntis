function getInfo(element) {

}
async function init() {
    let weekSelect = document.getElementById('week-select');
    startEnd = await fetch('first_last_entry');
    startEnd = await startEnd.text();
    startEnd = JSON.parse(startEnd);
    let startDate = Temporal.PlainDate.from(startEnd.first_entry);
    let endDate = Temporal.PlainDate.from(startEnd.last_entry);
    if (startDate.dayOfWeek !== 1) {
        startDate = startDate.subtract({days:startDate.dayOfWeek});
    }
    if (endDate.dayOfWeek !== 1) {
        endDate = endDate.subtract({days:endDate.dayOfWeek});
    }
    for (let weekNumber = startDate.weekOfYear; weekNumber <= endDate.weekOfYear; weekNumber++) {
        let option = document.createElement('option');
        option.value = weekNumber
        option.text = 'Week ' + weekNumber;
        weekSelect.appendChild(option);
    }
    await typeChanged(document.getElementById('type-select'));
    await updateTimetable();
}

async function typeChanged(selectElement) {
    let selectedType = selectElement.value;
    let elementSelect = document.getElementById('element-select');
    elementSelect.innerHTML = '';
    if (selectedType === '0') {
        // Class
        let classes = await fetch('classes');
        classes = await classes.text();
        classes = JSON.parse(classes);
        for (let cls of classes) {
            let option = document.createElement('option');
            option.value = cls.id;
            option.text = cls.short_name + ' (' + cls.long_name + ')';
            elementSelect.appendChild(option);
        }
    } else if (selectedType === '1') {
        // Teacher
        let teachers = await fetch('teachers');
        teachers = await teachers.text();
        teachers = JSON.parse(teachers);
        for (let teacher of teachers) {
            let option = document.createElement('option');
            option.value = teacher.id;
            option.text = '(' + teacher.short_name + ') ' + teacher.long_name;
            elementSelect.appendChild(option);
        }
    } else if (selectedType === '2') {
        // Room
        let rooms = await fetch('rooms');
        rooms = await rooms.text();
        rooms = JSON.parse(rooms);
        for (let room of rooms) {
            let option = document.createElement('option');
            option.value = room.id;
            option.text = room.short_name + ' (' + room.long_name + ')';
            elementSelect.appendChild(option);
        }
    }
    updateTimetable();
}

async function elementChanged(selectElement) {
    updateTimetable();
}

async function weekChanged(selectElement) {
    updateTimetable();
}

async function updateTimetable() {
    let typeSelect = document.getElementById('type-select');
    let elementSelect = document.getElementById('element-select');
    let selectedType = typeSelect.value;
    let selectedElement = elementSelect.value;
    console.log("Selected Type: " + selectedType);
    console.log("Selected Element: " + selectedElement);
}
async function parseTimeTable() {
    let weekdays = ['mo', 'tu', 'we', 'th', 'fr'];
    let data = await fetch('timetable2.json')
    data = await data.text();
    let json = JSON.parse(data);
    document.getElementById('info').innerText = json["tu"][4]["room"];
    for (let day of weekdays) {
        for (let lessonNumber = 1; lessonNumber <= 11; lessonNumber++) {
            let lessonKey = json[day][lessonNumber];
            let buttonId = day + '-' + lessonNumber;
            let buttonElement = document.getElementById(buttonId);
            if ((lessonKey["teacherShort"] !== undefined) || (lessonKey["class"] !== undefined) || (lessonKey["subject"] !== undefined) || (lessonKey["room"] !== undefined)) {
                buttonElement.innerHTML = `
                <div>
                    <span class="teacher-name">${lessonKey["class"]}</span><br>
                    <span class="subject">${lessonKey["subject"]}</span><br>
                    <span class="room">${lessonKey["room"]}</span>
                </div>`;
            } else {
                buttonElement.innerHTML = '';
                buttonElement.disabled = true;
                buttonElement.style.visibility = 'hidden';
            }
        }
    }
}