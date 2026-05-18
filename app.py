# ==========================================
# app.py
# ==========================================

from flask import Flask, render_template, request, redirect, session, send_file, flash
import sqlite3
import os
import io
from werkzeug.security import generate_password_hash, check_password_hash
from openpyxl import Workbook
from openpyxl.styles import Font
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
csrf = CSRFProtect(app)

DB_FILE = "database.db"

# ==========================================
# DATABASE SETUP
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            register_number TEXT,
            department TEXT DEFAULT 'CSE',
            cgpa REAL,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')
    
    # Check for missing columns (for migrations)
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'department' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN department TEXT DEFAULT 'CSE'")
        
    if 'is_admin' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    
    # Grades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            semester TEXT,
            subject TEXT,
            grade TEXT,
            credit INTEGER,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# ==========================================
# GRADE MAP
# ==========================================
grade_map = {
    "A+": 10, "A": 9, "B+": 8, "B": 7, "C+": 6, "C": 5, "D": 4, "F": 0, "FR": 0
}

# ==========================================
# FULL SYLLABUS
# ==========================================
syllabus = {
    "CSE": {
        "1": [("Mathematics-I", 4), ("Physics", 3), ("Basic Electronics Engineering", 3), ("Physics Lab", 2), ("Basic Electronics Lab", 2), ("Engineering Graphics & Design Lab", 3), ("Design Thinking", 1)],
        "2": [("English", 3), ("Mathematics-II", 4), ("Chemistry", 3), ("Programming for Problem Solving", 3), ("Universal Human Values-II", 3), ("Chemistry Lab", 2), ("Programming Lab", 2), ("Workshop / Manufacturing Lab", 3)],
        "3": [("Microprocessor and Microcontroller", 3), ("Data Structures and Algorithms", 3), ("Digital Electronics and Systems", 3), ("Mathematics-III", 3), ("Principles of Management", 3), ("MPMC Lab", 2), ("DSA Lab", 2), ("Digital Electronics Lab", 2), ("IT Workshop", 3)],
        "4": [("Discrete Mathematics", 4), ("Computer Organization & Architecture", 3), ("Design & Analysis of Algorithms", 3), ("Advanced Programming in Java", 3), ("Organizational Behaviour", 3), ("COA Lab", 2), ("DAA Lab", 2), ("Java Programming Lab", 2)],
        "5": [("Computer Networks", 3), ("Database Systems", 3), ("Theory of Computation", 4), ("Operating System", 3), ("Professional Elective-I", 3), ("CN Lab", 2), ("DBMS Lab", 2), ("OS Lab", 2)],
        "6": [("Web Technology", 3), ("Compiler Design", 3), ("Distributed Computing System", 3), ("AI & ML", 4), ("Professional Elective-II", 3), ("Web Tech Lab", 2), ("Compiler Design Lab", 2), ("Mini Project", 3)],
        "7": [("Cyber Security", 3), ("Biology", 3), ("Professional Elective-III", 3), ("Open Elective-I", 3), ("Cyber Security Lab", 2), ("Seminar", 1), ("Capstone Project-I", 6)],
        "8": [("Professional Elective-IV", 3), ("Open Elective-II", 3), ("Open Elective-III", 3), ("Capstone Project-II", 6), ("Internship", 1)]
    },
    "IT": {
        "1": [("Mathematics-I", 4), ("Physics", 3), ("Basic Electronics Engineering", 3), ("Physics Lab", 2), ("Basic Electronics Lab", 2), ("Engineering Graphics and Design Lab", 3), ("Design Thinking", 1)],
        "2": [("English", 3), ("Mathematics-II", 4), ("Chemistry", 3), ("Programming for Problem Solving", 3), ("Universal Human Values II", 3), ("Chemistry Lab", 2), ("Programming for Problem Solving Lab", 2), ("Workshop /Manufacturing Lab", 3)],
        "3": [("Mathematics-III", 3), ("Digital Electronics and System", 3), ("Data Structures and Algorithms", 3), ("Object Oriented Programming", 3), ("Communication Engineering", 3), ("Computer Organization and Architecture", 3), ("Data Structures and Algorithms Lab", 2), ("Object Oriented Programming Lab", 2), ("Communication Engineering Lab", 2)],
        "4": [("Discrete Mathematics", 4), ("Theory of Computation", 3), ("Information Coding Techniques", 3), ("Database Management Systems", 3), ("Web Technology", 3), ("Operating Systems", 3), ("Database Management Systems Lab", 2), ("Web Technology Lab", 2), ("Operating Systems Lab", 2)],
        "5": [("Computer Networks", 3), ("Cloud Computing", 3), ("Distributed Computing", 3), ("Embedded Systems and IoT", 3), ("Principles of Management", 3), ("Computer Networks Lab", 2), ("Cloud Computing Lab", 2), ("Embedded Systems and IoT Lab", 2)],
        "6": [("Artificial Intelligence", 3), ("Software Engineering", 3), ("Compiler Design", 3), ("Professional Elective-I", 3), ("Professional Elective-II", 3), ("Human Resource Management", 3), ("Artificial Intelligence Lab", 2), ("Mini Project", 3)],
        "7": [("Organizational Behavior", 3), ("Cyber Security", 3), ("Professional Elective-III", 3), ("Professional Elective-IV", 3), ("Seminar", 1), ("Project I", 6)],
        "8": [("Open Elective-I", 3), ("Open Elective-II", 3), ("Open Elective-III", 3), ("Internship", 1), ("Project II", 6)]
    }
}

# ==========================================
# LOGIN / REGISTER
# ==========================================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        action = request.form.get("action")
        regno = request.form.get("regno", "").strip().upper()
        password = request.form.get("password")

        conn = get_db_connection()

        if action == "register":
            username = request.form.get("username", "").strip()
            dept = request.form.get("department", "CSE")
            
            if not username or not regno or not password:
                flash("All fields are required", "danger")
                return redirect("/")
            
            if len(password) < 6:
                flash("Password must be at least 6 characters long", "danger")
                return redirect("/")

            # Check for existing user by username or register number
            user_by_uname = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            user_by_regno = conn.execute("SELECT * FROM users WHERE register_number = ?", (regno,)).fetchone()
            
            if user_by_uname or user_by_regno:
                conn.close()
                flash("User with this username or registration number already exists", "danger")
                return redirect("/")
            
            hashed_pw = generate_password_hash(password)
            conn.execute("INSERT INTO users (username, password, register_number, department) VALUES (?, ?, ?, ?)",
                         (username, hashed_pw, regno, dept))
            conn.commit()
            conn.close()
            flash("Registration successful! Please login.", "success")
            return redirect("/")

        if action == "login":
            user = conn.execute("SELECT * FROM users WHERE register_number = ?", (regno,)).fetchone()
            if user and check_password_hash(user["password"], password):
                session.clear()
                
                # Check role
                if user["is_admin"]:
                    session["admin"] = True
                    session["admin_user"] = user["username"]
                    conn.close()
                    return redirect("/admin")
                else:
                    session["user"] = user["username"]
                    session["department"] = user["department"]
                    conn.close()
                    return redirect("/dashboard")
            
            conn.close()
            flash("Invalid Credentials", "danger")

    return render_template("login.html")

# ==========================================
# STUDENT DASHBOARD
# ==========================================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    username = session["user"]
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    dept = user_row["department"]
    dept_syllabus = syllabus.get(dept, syllabus["CSE"])
    
    if request.method == "POST":
        sem = request.form["semester"]
        subjects_config = dept_syllabus[sem]
        
        try:
            with conn:
                # Delete old grades for this semester to overwrite
                conn.execute("DELETE FROM grades WHERE username = ? AND semester = ?", (username, sem))
                
                total_credits = 0
                total_points = 0
                
                for i, (sub_name, credit) in enumerate(subjects_config):
                    grade = request.form.get(f"sub{i}")
                    if grade:
                        gp = grade_map[grade]
                        total_credits += credit
                        total_points += gp * credit
                        conn.execute("INSERT INTO grades (username, semester, subject, grade, credit) VALUES (?, ?, ?, ?, ?)",
                                     (username, sem, sub_name, grade, credit))
                
                # Re-calculate CGPA
                all_grades = conn.execute("SELECT grade, credit FROM grades WHERE username = ?", (username,)).fetchall()
                total_c = 0
                total_p = 0
                for row in all_grades:
                    total_c += row["credit"]
                    total_p += grade_map[row["grade"]] * row["credit"]
                
                cgpa = round(total_p / total_c, 2) if total_c > 0 else 0
                conn.execute("UPDATE users SET cgpa = ? WHERE username = ?", (cgpa, username))
            
            flash(f"Semester {sem} grades saved!", "success")
        except sqlite3.Error as e:
            flash(f"Error saving grades: {e}", "danger")
        
        return redirect(f"/dashboard?semester={sem}")

    # GET REQUEST
    selected_sem = request.args.get("semester")
    
    # Fetch all grades to display in tables
    db_grades = conn.execute("SELECT * FROM grades WHERE username = ?", (username,)).fetchall()
    
    # Organize grades for the template
    gradesData = {}
    for row in db_grades:
        s = row["semester"]
        if s not in gradesData:
            gradesData[s] = {"subjects": [], "credits": 0, "points": 0}
        
        gradesData[s]["subjects"].append({
            "subject": row["subject"],
            "grade": row["grade"],
            "credit": row["credit"]
        })
        gradesData[s]["credits"] += row["credit"]
        gradesData[s]["points"] += grade_map[row["grade"]] * row["credit"]

    for s in gradesData:
        gradesData[s]["sgpa"] = round(gradesData[s]["points"] / gradesData[s]["credits"], 2)

    # Pre-fill data for selected semester
    current_sem_grades = {}
    if selected_sem:
        rows = conn.execute("SELECT subject, grade FROM grades WHERE username = ? AND semester = ?", 
                            (username, selected_sem)).fetchall()
        current_sem_grades = {r["subject"]: r["grade"] for r in rows}

    conn.close()
    return render_template(
        "dashboard.html",
        syllabus=dept_syllabus,
        selected_sem=selected_sem,
        gradesData=gradesData,
        cgpa=user_row["cgpa"],
        username=username,
        register_number=user_row["register_number"],
        department=dept,
        current_sem_grades=current_sem_grades
    )

# ==========================================
# ADMIN DASHBOARD
# ==========================================
@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/")

    admin_username = session.get("admin_user", "Admin")
    conn = get_db_connection()
    
    # Filtering logic
    filter_dept = request.args.get("department", "")
    filter_cgpa = request.args.get("min_cgpa", "")
    
    query = "SELECT username, register_number, department, cgpa FROM users WHERE is_admin = 0"
    params = []
    
    if filter_dept:
        query += " AND department = ?"
        params.append(filter_dept)
        
    if filter_cgpa:
        try:
            min_cgpa_val = float(filter_cgpa)
            query += " AND cgpa >= ?"
            params.append(min_cgpa_val)
        except ValueError:
            filter_cgpa = "" # Reset if invalid
            
    users = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template("admin.html", 
                           users=users, 
                           admin_username=admin_username, 
                           filter_dept=filter_dept, 
                           filter_cgpa=filter_cgpa)

# ==========================================
# ADMIN USER DETAILS
# ==========================================
@app.route("/admin/user/<username>")
def admin_user(username):
    if "admin" not in session:
        return redirect("/")

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        conn.close()
        return "User not found"

    db_grades = conn.execute("SELECT * FROM grades WHERE username = ?", (username,)).fetchall()
    gradesData = {}
    for row in db_grades:
        s = row["semester"]
        if s not in gradesData:
            gradesData[s] = {"subjects": [], "credits": 0, "points": 0}
        gradesData[s]["subjects"].append({"subject": row["subject"], "grade": row["grade"], "credit": row["credit"]})
        gradesData[s]["credits"] += row["credit"]
        gradesData[s]["points"] += grade_map[row["grade"]] * row["credit"]
    
    for s in gradesData:
        gradesData[s]["sgpa"] = round(gradesData[s]["points"] / gradesData[s]["credits"], 2)

    conn.close()
    # Mocking user object for template compatibility
    user_dict = dict(user)
    user_dict["gradesData"] = gradesData
    
    return render_template("student_details.html", username=username, user=user_dict)

# ==========================================
# ADMIN EDIT USER
# ==========================================
@app.route("/admin/edit/<username>", methods=["POST"])
def admin_edit(username):
    if "admin" not in session:
        return redirect("/")

    conn = get_db_connection()
    new_username = request.form.get("username").strip()
    new_dept = request.form.get("department")
    new_password = request.form.get("password")

    if not new_username:
        flash("Student name cannot be empty.", "danger")
        return redirect(f"/admin/user/{username}")

    try:
        with conn:
            # Handle username change
            if new_username != username:
                existing = conn.execute("SELECT * FROM users WHERE username = ?", (new_username,)).fetchone()
                if existing:
                    flash("This name is already taken by another user.", "danger")
                    return redirect(f"/admin/user/{username}")
                
                # Update users and grades
                conn.execute("UPDATE users SET username = ? WHERE username = ?", (new_username, username))
                conn.execute("UPDATE grades SET username = ? WHERE username = ?", (new_username, username))
                username = new_username

            # Update department
            conn.execute("UPDATE users SET department = ? WHERE username = ?", (new_dept, username))

            # Update password if provided
            if new_password:
                if len(new_password) < 6:
                    flash("Password must be at least 6 characters.", "danger")
                    return redirect(f"/admin/user/{username}")
                hashed_pw = generate_password_hash(new_password)
                conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_pw, username))

        flash("Student profile updated successfully!", "success")
    except sqlite3.Error as e:
        flash(f"Database Error: {e}", "danger")
    finally:
        conn.close()

    return redirect(f"/admin/user/{username}")

# ==========================================
# ADMIN DELETE USER
# ==========================================
@app.route("/admin/delete/<username>", methods=["POST"])
def admin_delete(username):
    if "admin" not in session:
        return redirect("/")

    conn = get_db_connection()
    try:
        with conn:
            # Delete grades first to maintain data integrity
            conn.execute("DELETE FROM grades WHERE username = ?", (username,))
            # Delete the user
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
        flash(f"Student {username} and their data have been deleted.", "success")
    except sqlite3.Error as e:
        flash(f"Error deleting user: {e}", "danger")
    finally:
        conn.close()

    return redirect("/admin")

# ==========================================
# EXPORT EXCEL (IN-MEMORY)
# ==========================================
@app.route("/admin/export")
def export_excel():
    if "admin" not in session:
        return redirect("/")

    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Student Results"
    
    headers = ["Name", "Register Number", "Department"] + [f"Sem {i} SGPA" for i in range(1, 9)] + ["CGPA"]
    ws.append(headers)
    for cell in ws[1]: cell.font = Font(bold=True)

    for user in users:
        row = [user["username"], user["register_number"], user["department"]]
        user_grades = conn.execute("SELECT semester, grade, credit FROM grades WHERE username = ?", (user["username"],)).fetchall()
        
        sem_stats = {}
        for g in user_grades:
            s = g["semester"]
            if s not in sem_stats: sem_stats[s] = {"p": 0, "c": 0}
            sem_stats[s]["p"] += grade_map[g["grade"]] * g["credit"]
            sem_stats[s]["c"] += g["credit"]
        
        for i in range(1, 9):
            s_str = str(i)
            if s_str in sem_stats and sem_stats[s_str]["c"] > 0:
                row.append(round(sem_stats[s_str]["p"] / sem_stats[s_str]["c"], 2))
            else:
                row.append("-")
        
        row.append(user["cgpa"] or "-")
        ws.append(row)

    conn.close()
    
    # Save to memory
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name="student_results.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================================
# STUDENT PROFILE
# ==========================================
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect("/")
        
    current_username = session["user"]
    conn = get_db_connection()
    
    if request.method == "POST":
        new_username = request.form.get("username").strip()
        new_dept = request.form.get("department")
        new_password = request.form.get("password")
        
        if not new_username:
            flash("Name cannot be empty.", "danger")
            return redirect("/profile")
            
        try:
            with conn:
                # Handle username change
                if new_username != current_username:
                    existing = conn.execute("SELECT * FROM users WHERE username = ?", (new_username,)).fetchone()
                    if existing:
                        flash("This name is already taken.", "danger")
                        return redirect("/profile")
                        
                    # Update users and grades tables (username acts as PK)
                    conn.execute("UPDATE users SET username = ? WHERE username = ?", (new_username, current_username))
                    conn.execute("UPDATE grades SET username = ? WHERE username = ?", (new_username, current_username))
                    session["user"] = new_username
                    current_username = new_username
                
                # Update department
                conn.execute("UPDATE users SET department = ? WHERE username = ?", (new_dept, current_username))
                session["department"] = new_dept
                
                # Update password if provided
                if new_password:
                    if len(new_password) < 6:
                        flash("Password must be at least 6 characters.", "danger")
                        return redirect("/profile")
                    hashed_pw = generate_password_hash(new_password)
                    conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_pw, current_username))
                    
            flash("Profile updated successfully!", "success")
        except sqlite3.Error as e:
            flash(f"Database Error: {e}", "danger")
            
        return redirect("/profile")
        
    user = conn.execute("SELECT * FROM users WHERE username = ?", (current_username,)).fetchone()
    conn.close()
    return render_template("profile.html", user=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    app.run(debug=debug_mode)