from flask import Blueprint, render_template, request, redirect, session, flash, send_file
import sqlite3
import io
from openpyxl import Workbook
from openpyxl.styles import Font
from werkzeug.security import generate_password_hash
from utils.db import get_db_connection
from utils.constants import grade_map

admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/")

    admin_username = session.get("admin_user", "Admin")
    conn = get_db_connection()
    
    # Fetch admin profile pic
    admin_row = conn.execute("SELECT profile_pic FROM users WHERE username = ?", (admin_username,)).fetchone()
    admin_pic = admin_row["profile_pic"] if admin_row else "default.png"
    
    # Filtering logic
    filter_dept = request.args.get("department", "")
    filter_cgpa = request.args.get("min_cgpa", "")
    search_query = request.args.get("search", "").strip()
    
    # Sorting logic
    sort_by = request.args.get("sort", "username")
    order = request.args.get("order", "asc")
    
    # Pagination logic
    try:
        page = int(request.args.get("page", 1))
        if page < 1: page = 1
    except ValueError:
        page = 1
    per_page = 10
    offset = (page - 1) * per_page
    
    # Validate sorting parameters to prevent SQL injection
    valid_columns = ["username", "register_number", "department", "cgpa"]
    if sort_by not in valid_columns:
        sort_by = "username"
    if order not in ["asc", "desc"]:
        order = "asc"
    
    base_query = "FROM users WHERE is_admin = 0"
    params = []
    
    if filter_dept:
        base_query += " AND department = ?"
        params.append(filter_dept)
        
    if filter_cgpa:
        try:
            min_cgpa_val = float(filter_cgpa)
            base_query += " AND cgpa >= ?"
            params.append(min_cgpa_val)
        except ValueError:
            filter_cgpa = "" 

    if search_query:
        base_query += " AND (username LIKE ? OR register_number LIKE ?)"
        params.append(f"%{search_query}%")
        params.append(f"%{search_query}%")
            
    # Count total results for pagination
    count_query = f"SELECT COUNT(*) {base_query}"
    total_results = conn.execute(count_query, params).fetchone()[0]
    total_pages = (total_results + per_page - 1) // per_page
    
    # Fetch paginated results
    query = f"SELECT username, register_number, department, cgpa {base_query} ORDER BY {sort_by} {order.upper()} LIMIT ? OFFSET ?"
    paginated_params = params + [per_page, offset]
    
    users = conn.execute(query, paginated_params).fetchall()
    conn.close()
    
    return render_template("admin.html", 
                           users=users, 
                           admin_username=admin_username, 
                           admin_pic=admin_pic,
                           filter_dept=filter_dept, 
                           filter_cgpa=filter_cgpa,
                           search_query=search_query,
                           sort_by=sort_by,
                           order=order,
                           page=page,
                           total_pages=total_pages,
                           total_results=total_results)

@admin_bp.route("/admin/user/<username>")
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

@admin_bp.route("/admin/edit/<username>", methods=["POST"])
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

@admin_bp.route("/admin/delete/<username>", methods=["POST"])
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

@admin_bp.route("/admin/export")
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
