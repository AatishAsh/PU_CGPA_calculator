from flask import Blueprint, render_template, request, redirect, session, flash
import sqlite3
from utils.db import get_db_connection
from utils.constants import syllabus, grade_map

student_bp = Blueprint('student', __name__)

@student_bp.route("/dashboard", methods=["GET", "POST"])
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

@student_bp.route("/dashboard/clear/<sem>", methods=["POST"])
def clear_semester(sem):
    if "user" not in session:
        return redirect("/")
    
    username = session["user"]
    conn = get_db_connection()
    
    try:
        with conn:
            # Delete grades for this semester
            conn.execute("DELETE FROM grades WHERE username = ? AND semester = ?", (username, sem))
            
            # Recalculate CGPA
            all_grades = conn.execute("SELECT grade, credit FROM grades WHERE username = ?", (username,)).fetchall()
            total_c = 0
            total_p = 0
            for row in all_grades:
                total_c += row["credit"]
                total_p += grade_map[row["grade"]] * row["credit"]
            
            cgpa = round(total_p / total_c, 2) if total_c > 0 else 0
            conn.execute("UPDATE users SET cgpa = ? WHERE username = ?", (cgpa, username))
            
        flash(f"Semester {sem} grades cleared!", "success")
    except sqlite3.Error as e:
        flash(f"Error clearing grades: {e}", "danger")
    finally:
        conn.close()
        
    return redirect("/dashboard")
