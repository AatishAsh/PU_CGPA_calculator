from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        action = request.form.get("action")
        regno_input = request.form.get("regno", "").strip()
        password = request.form.get("password")

        conn = get_db_connection()

        if action == "register":
            username = request.form.get("username", "").strip()
            dept = request.form.get("department", "CSE")
            confirm_password = request.form.get("confirm_password")
            regno = regno_input.upper()
            
            if not username or not regno or not password or not confirm_password:
                flash("All fields are required", "danger")
                return redirect("/")
            
            if password != confirm_password:
                flash("Password and confirm password must match", "danger")
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
            # Search by Upper(Reg Number) OR Raw(Full Name)
            user = conn.execute("SELECT * FROM users WHERE register_number = ? OR username = ?", (regno_input.upper(), regno_input)).fetchone()
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

@auth_bp.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect("/")
        
    current_username = session["user"]
    conn = get_db_connection()
    
    if request.method == "POST":
        new_username = request.form.get("username").strip()
        new_dept = request.form.get("department")
        new_password = request.form.get("password")
        new_profile_pic = request.form.get("profile_pic", "default.png")
        
        if not new_username:
            flash("Name cannot be empty.", "danger")
            return redirect("/profile")
            
        try:
            with conn:
                # Update profile picture
                conn.execute("UPDATE users SET profile_pic = ? WHERE username = ?", (new_profile_pic, current_username))

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

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@auth_bp.route("/forgot-password")
def forgot_password():
    return render_template("forgot_password.html")
