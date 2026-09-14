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
        option.value = startDate.add({days: (weekNumber - startDate.weekOfYear) * 7}).toString();
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
    if (selectedType === 'class') {
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
    } else if (selectedType === 'teacher') {
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
    } else if (selectedType === 'room') {
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
    let weekSelect = document.getElementById('week-select');
    let timetablediv = document.getElementById('timetable-entrys');
    timetablediv.innerHTML = '';
    let selectedType = typeSelect.value;
    let selectedElement = elementSelect.value;
    let selectedWeek = weekSelect.value;
    console.log("Selected Type: " + selectedType);
    console.log("Selected Element: " + selectedElement);
    console.log("Selected Week: " + selectedWeek);
    startdate = Temporal.PlainDate.from(selectedWeek);
    enddate = startdate.add({days: 6});
    data = await fetch('/' + selectedType + '/' + selectedElement + '?start_date=' + startdate.toString() + '&end_date=' + enddate.toString());
    data = await data.json();
    for (let entry of data) {
        let day = Temporal.PlainDate.from(entry.date).dayOfWeek;
        let period_start = entry.period_start.split(':');
        let period_end = entry.period_end.split(':');
        let begin = (parseInt(period_start[0]) - 8)*60 + parseInt(period_start[1]);
        let end = (parseInt(period_end[0]) - 8)*60 + parseInt(period_end[1]);
        let duration = end - begin;
        let entryDiv = document.createElement('div');
        let firstline = '';
        let lastline = '';
        if (selectedType === 'class') {
            firstline = entry.teacher;
            lastline = entry.room;
        } else if (selectedType === 'teacher') {
            firstline = entry.class;
            lastline = entry.room;
        } else if (selectedType === 'room') {
            firstline = entry.class;
            lastline = entry.teacher;
        }
        entryDiv.href = "#";
        entryDiv.className = "lesson-normal";
        entryDiv.setAttribute("onclick", "switchLayout()");
        entryDiv.style.position = "absolute";
        entryDiv.style.bottom = (590 - end)*1.8 + "px";
        entryDiv.style.left = (day)*120 + "px";
        entryDiv.style.height = duration*1.8 + "px";
        entryDiv.innerHTML = `
                <span class="teacher-name">${firstline}</span><br>
                <span class="subject">${entry.subject}</span><br>
                <span class="room">${lastline}</span>`;
        timetablediv.appendChild(entryDiv);
    }

}