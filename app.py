# ==========================================
# app.py
# ==========================================

from flask import Flask, render_template, request, redirect, session, send_file
import json
import os
from openpyxl import Workbook
from openpyxl.styles import Font

app = Flask(__name__)
app.secret_key = "secret123"

DATA_FILE = "data.json"


# ==========================================
# LOAD DATA
# ==========================================
def load_data():

    if not os.path.exists(DATA_FILE):

        default_data = {
            "users": {}
        }

        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f, indent=4)

        return default_data

    with open(DATA_FILE, "r") as f:

        try:
            data = json.load(f)

            if "users" not in data:
                data["users"] = {}

            return data

        except:
            return {"users": {}}


# ==========================================
# SAVE DATA
# ==========================================
def save_data(data):

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ==========================================
# GRADE MAP
# ==========================================
grade_map = {
    "A+": 10,
    "A": 9,
    "B+": 8,
    "B": 7,
    "C+": 6,
    "C": 5,
    "D": 4,
    "F": 0,
    "FR": 0
}


# ==========================================
# FULL SYLLABUS
# ==========================================
syllabus = {

    "1": [
        ("Mathematics-I", 4),
        ("Physics", 3),
        ("Basic Electronics Engineering", 3),
        ("Physics Lab", 2),
        ("Basic Electronics Lab", 2),
        ("Engineering Graphics & Design Lab", 3),
        ("Design Thinking", 1)
    ],

    "2": [
        ("English", 3),
        ("Mathematics-II", 4),
        ("Chemistry", 3),
        ("Programming for Problem Solving", 3),
        ("Universal Human Values-II", 3),
        ("Chemistry Lab", 2),
        ("Programming Lab", 2),
        ("Workshop / Manufacturing Lab", 3)
    ],

    "3": [
        ("Microprocessor and Microcontroller", 3),
        ("Data Structures and Algorithms", 3),
        ("Digital Electronics and Systems", 3),
        ("Mathematics-III", 3),
        ("Principles of Management", 3),
        ("MPMC Lab", 2),
        ("DSA Lab", 2),
        ("Digital Electronics Lab", 2),
        ("IT Workshop", 3)
    ],

    "4": [
        ("Discrete Mathematics", 4),
        ("Computer Organization & Architecture", 3),
        ("Design & Analysis of Algorithms", 3),
        ("Advanced Programming in Java", 3),
        ("Organizational Behaviour", 3),
        ("COA Lab", 2),
        ("DAA Lab", 2),
        ("Java Programming Lab", 2)
    ],

    "5": [
        ("Computer Networks", 3),
        ("Database Systems", 3),
        ("Theory of Computation", 4),
        ("Operating System", 3),
        ("Professional Elective-I", 3),
        ("CN Lab", 2),
        ("DBMS Lab", 2),
        ("OS Lab", 2)
    ],

    "6": [
        ("Web Technology", 3),
        ("Compiler Design", 3),
        ("Distributed Computing System", 3),
        ("AI & ML", 4),
        ("Professional Elective-II", 3),
        ("Web Tech Lab", 2),
        ("Compiler Design Lab", 2),
        ("Mini Project", 3)
    ],

    "7": [
        ("Cyber Security", 3),
        ("Biology", 3),
        ("Professional Elective-III", 3),
        ("Open Elective-I", 3),
        ("Cyber Security Lab", 2),
        ("Seminar", 1),
        ("Capstone Project-I", 6)
    ],

    "8": [
        ("Professional Elective-IV", 3),
        ("Open Elective-II", 3),
        ("Open Elective-III", 3),
        ("Capstone Project-II", 6),
        ("Internship", 1)
    ]
}


# ==========================================
# LOGIN / REGISTER
# ==========================================
@app.route("/", methods=["GET", "POST"])
def login():

    data = load_data()

    users = data.get("users", {})

    if request.method == "POST":

        username = request.form["username"].strip()
        regno = request.form.get("regno", "").upper()
        password = request.form["password"]
        action = request.form["action"]

        # ADMIN LOGIN
        if username == "admin" and password == "admin123":

            session.clear()
            session["admin"] = True

            return redirect("/admin")

        # REGISTER
        if action == "register":

            if username in users:
                return "User already exists"

            users[username] = {
                "register_number": regno,
                "password": password,
                "gradesData": {},
                "cgpa": None
            }

            save_data(data)

            return redirect("/")

        # LOGIN
        if action == "login":

            if username in users and users[username]["password"] == password:

                session.clear()

                session["user"] = username

                return redirect("/dashboard")

            return "Invalid Credentials"

    return render_template("login.html")


# ==========================================
# STUDENT DASHBOARD
# ==========================================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:
        return redirect("/")

    data = load_data()

    current_user = session["user"]

    user = data["users"][current_user]

    gradesData = user.get("gradesData", {})

    selected_sem = request.args.get("semester")

    sgpa = None

    if request.method == "POST":

        sem = request.form["semester"]

        subjects = syllabus[sem]

        total_credits = 0
        total_points = 0

        subject_list = []

        for i, (subject_name, credit) in enumerate(subjects):

            grade = request.form.get(f"sub{i}")

            if grade:

                gp = grade_map[grade]

                total_credits += credit
                total_points += gp * credit

                subject_list.append({
                    "subject": subject_name,
                    "grade": grade,
                    "credit": credit
                })

        if total_credits > 0:

            sgpa = round(total_points / total_credits, 2)

            gradesData[sem] = {
                "subjects": subject_list,
                "sgpa": sgpa,
                "credits": total_credits,
                "points": total_points
            }

            user["gradesData"] = gradesData

            total_c = sum(v["credits"] for v in gradesData.values())

            total_p = sum(v["points"] for v in gradesData.values())

            if total_c > 0:
                user["cgpa"] = round(total_p / total_c, 2)

            save_data(data)

        selected_sem = sem

    return render_template(
        "dashboard.html",
        syllabus=syllabus,
        selected_sem=selected_sem,
        gradesData=gradesData,
        cgpa=user.get("cgpa"),
        sgpa=sgpa,
        username=current_user,
        register_number=user.get("register_number")
    )


# ==========================================
# ADMIN DASHBOARD
# ==========================================
@app.route("/admin")
def admin():

    if "admin" not in session:
        return redirect("/")

    data = load_data()

    users = data.get("users", {})

    return render_template(
        "admin.html",
        users=users
    )


# ==========================================
# ADMIN USER DETAILS
# ==========================================
@app.route("/admin/user/<username>")
def admin_user(username):

    if "admin" not in session:
        return redirect("/")

    data = load_data()

    users = data.get("users", {})

    if username not in users:
        return "User not found"

    user = users[username]

    return render_template(
        "student_details.html",
        username=username,
        user=user
    )


# ==========================================
# EXPORT SGPA EXCEL
# ==========================================
@app.route("/admin/export")
def export_excel():

    if "admin" not in session:
        return redirect("/")

    data = load_data()

    users = data.get("users", {})

    wb = Workbook()

    ws = wb.active

    ws.title = "Student Results"

    headers = [
        "Name",
        "Register Number",
        "Semester 1 SGPA",
        "Semester 2 SGPA",
        "Semester 3 SGPA",
        "Semester 4 SGPA",
        "Semester 5 SGPA",
        "Semester 6 SGPA",
        "Semester 7 SGPA",
        "Semester 8 SGPA",
        "CGPA"
    ]

    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for username, user_data in users.items():

        regno = user_data.get("register_number", "-")

        cgpa = user_data.get("cgpa", "-")

        gradesData = user_data.get("gradesData", {})

        row = [
            username,
            regno
        ]

        for sem in range(1, 9):

            sem_str = str(sem)

            if sem_str in gradesData:
                row.append(gradesData[sem_str].get("sgpa", "-"))
            else:
                row.append("-")

        row.append(cgpa)

        ws.append(row)

    for column in ws.columns:

        max_length = 0

        column_letter = column[0].column_letter

        for cell in column:

            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass

        ws.column_dimensions[column_letter].width = max_length + 5

    filename = "student_results.xlsx"

    wb.save(filename)

    return send_file(
        filename,
        as_attachment=True
    )


# ==========================================
# EXPORT FULL SUBJECT EXCEL
# ==========================================
@app.route("/admin/export_full")
def export_full_excel():

    if "admin" not in session:
        return redirect("/")

    data = load_data()

    users = data.get("users", {})

    wb = Workbook()

    ws = wb.active

    ws.title = "Full Student Grades"

    headers = [
        "Name",
        "Register Number"
    ]

    subject_columns = []

    for sem, subjects in syllabus.items():

        for subject_name, credit in subjects:

            column_name = f"Sem {sem} - {subject_name}"

            subject_columns.append(column_name)

    headers.extend(subject_columns)

    for sem in range(1, 9):
        headers.append(f"Semester {sem} SGPA")

    headers.append("CGPA")

    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for username, user_data in users.items():

        row = []

        row.append(username)

        row.append(user_data.get("register_number", "-"))

        gradesData = user_data.get("gradesData", {})

        # SUBJECT GRADES
        for sem, subjects in syllabus.items():

            sem_data = gradesData.get(sem, {})

            subject_list = sem_data.get("subjects", [])

            subject_grade_map = {}

            for s in subject_list:
                subject_grade_map[s["subject"]] = s["grade"]

            for subject_name, credit in subjects:

                row.append(
                    subject_grade_map.get(subject_name, "-")
                )

        # SGPA
        for sem in range(1, 9):

            sem_str = str(sem)

            if sem_str in gradesData:
                row.append(
                    gradesData[sem_str].get("sgpa", "-")
                )
            else:
                row.append("-")

        # CGPA
        row.append(
            user_data.get("cgpa", "-")
        )

        ws.append(row)

    for column in ws.columns:

        max_length = 0

        column_letter = column[0].column_letter

        for cell in column:

            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass

        ws.column_dimensions[column_letter].width = max_length + 5

    filename = "full_subject_results.xlsx"

    wb.save(filename)

    return send_file(
        filename,
        as_attachment=True
    )


# ==========================================
# LOGOUT
# ==========================================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ==========================================
# RUN
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)