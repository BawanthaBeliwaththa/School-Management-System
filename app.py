from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import date, datetime, timedelta
import re
import os
import sys
from werkzeug.utils import secure_filename
import json
import pandas as pd
import random
import string
from functools import wraps
from io import BytesIO
import openpyxl

app = Flask(__name__)

app.secret_key = 'abcd21234455'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'bawwa'
app.config['MYSQL_DB'] = 'python_sms'

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

mysql = MySQL(app)

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def is_recent(date_string, days=7):
    """Check if a date is within the last N days"""
    if not date_string:
        return False
    try:
        # Parse the date string (adjust format based on your database)
        if isinstance(date_string, str):
            date_obj = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        elif isinstance(date_string, datetime):
            date_obj = date_string
        else:
            return False
            
        cutoff_date = datetime.now() - timedelta(days=days)
        return date_obj > cutoff_date
    except Exception as e:
        print(f"Error parsing date: {e}")
        return False

def time_ago_filter(dt):
    """Convert a datetime object to a human-readable time ago string"""
    if not dt:
        return "just now"
    
    now = datetime.now()
    diff = now - dt
    
    # Convert to seconds
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 2592000:  # 30 days
        days = int(seconds // 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 31536000:  # 365 days
        months = int(seconds // 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds // 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"

# ==================== DECORATORS FOR ROLE-BASED ACCESS ====================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and session.get('type') == 'administrator':
            return f(*args, **kwargs)
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    return decorated_function

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and session.get('type') in ['teacher', 'administrator']:
            return f(*args, **kwargs)
        flash('Access denied. Teacher privileges required.', 'error')
        return redirect(url_for('dashboard'))
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and session.get('type') in ['student', 'administrator']:
            return f(*args, **kwargs)
        flash('Access denied. Student privileges required.', 'error')
        return redirect(url_for('dashboard'))
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session:
            return f(*args, **kwargs)
        return redirect(url_for('login'))
    return decorated_function

# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_password(length=8):
    """Generate a random password"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_user_db_id():
    """Get the correct database ID based on user type"""
    if 'loggedin' not in session:
        return None
    
    user_type = session.get('type')
    
    if user_type == 'student':
        # For students, use student_id from sms_students table
        return session.get('student_id')
    elif user_type == 'teacher':
        # For teachers, use teacher_id from sms_teacher table
        return session.get('teacher_id')
    else:
        # For admins, use userid from sms_user table
        return session.get('userid')


# ==================== LOGIN/LOGOUT ====================

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    mesage = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Check in sms_user table
        cursor.execute('SELECT * FROM sms_user WHERE status="active" AND email = %s AND password = %s', (email, password))
        user = cursor.fetchone()
        
        if user:
            # Map database 'type' to session 'role'
            user_type = user['type']
            
            # Set session variables
            session['loggedin'] = True
            session['userid'] = user['id']
            session['name'] = user['first_name'] + ' ' + user['last_name']
            session['email'] = user['email']
            session['type'] = user_type
            
            # For administrators
            if user_type == 'administrator':
                session['role'] = 'admin'
                # Update last login
                cursor.execute('UPDATE sms_user SET last_login = NOW() WHERE id = %s', (user['id'],))
                mysql.connection.commit()
                mesage = 'Admin logged in successfully!'
                return redirect(url_for('dashboard'))
            
            # For teachers
            elif user_type == 'teacher':
                session['role'] = 'teacher'
                # Get teacher_id from sms_teacher table
                cursor.execute('SELECT teacher_id FROM sms_teacher WHERE user_id = %s', (user['id'],))
                teacher = cursor.fetchone()
                
                if teacher:
                    session['teacher_id'] = teacher['teacher_id']
                    # Update last login
                    cursor.execute('UPDATE sms_user SET last_login = NOW() WHERE id = %s', (user['id'],))
                    mysql.connection.commit()
                    mesage = 'Teacher logged in successfully!'
                    return redirect(url_for('dashboard'))
                else:
                    mesage = 'Teacher record not found!'
            
            # For students
            elif user_type == 'student':
                session['role'] = 'student'
                # Get student_id from sms_students table
                cursor.execute('SELECT id, admission_no FROM sms_students WHERE user_id = %s', (user['id'],))
                student = cursor.fetchone()
                
                if student:
                    session['student_id'] = student['id']
                    session['admission_no'] = student.get('admission_no', '')
                    # Update last login
                    cursor.execute('UPDATE sms_user SET last_login = NOW() WHERE id = %s', (user['id'],))
                    mysql.connection.commit()
                    mesage = 'Student logged in successfully!'
                    return redirect(url_for('dashboard'))
                else:
                    mesage = 'Student record not found!'
            
            else:
                mesage = 'Unknown user type!'
        else:
            mesage = 'Please enter correct email / password!'
    
    return render_template('login.html', mesage=mesage)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== DASHBOARD (ROLE-BASED) ====================

def student_dashboard():
    """Student-specific dashboard"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get student table ID from session - it should already be set from login
    student_table_id = session.get('student_id')
    
    if not student_table_id:
        # Try to get it from user_id as fallback
        cursor.execute('SELECT id FROM sms_students WHERE user_id = %s', (session['userid'],))
        student = cursor.fetchone()
        if student:
            student_table_id = student['id']
            session['student_id'] = student_table_id  # Store it for future
        else:
            flash('Student information not found!', 'error')
            return redirect(url_for('logout'))
    
    # Get student info
    cursor.execute('SELECT * FROM sms_students WHERE id = %s', (student_table_id,))
    student = cursor.fetchone()
    
    if not student:
        flash('Student record not found!', 'error')
        return redirect(url_for('logout'))
    
    # Get enrolled courses count
    cursor.execute('''
        SELECT COUNT(*) as count FROM sms_course_enrollments 
        WHERE student_id = %s
    ''', (student_table_id,))
    enrolled_courses_result = cursor.fetchone()
    enrolled_courses = enrolled_courses_result['count'] if enrolled_courses_result else 0
    
    # Get pending assignments count
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM sms_assignments a
        JOIN sms_course_enrollments ce ON a.course_id = ce.course_id
        WHERE ce.student_id = %s 
            AND a.due_date >= CURDATE()
            AND a.assignment_id NOT IN (
                SELECT assignment_id FROM sms_assignment_submissions 
                WHERE student_id = %s
            )
    ''', (student_table_id, student_table_id))
    pending_assignments_result = cursor.fetchone()
    pending_assignments = pending_assignments_result['count'] if pending_assignments_result else 0
    
    # Get attendance rate - note: attendance_status is string in your DB
    cursor.execute('''
        SELECT ROUND(AVG(CASE WHEN attendance_status = "present" THEN 1 ELSE 0 END) * 100, 1) as rate
        FROM sms_attendance 
        WHERE student_id = %s 
        AND attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    ''', (student_table_id,))
    attendance_result = cursor.fetchone()
    attendance_rate = attendance_result['rate'] if attendance_result else 0
    
    # Get recent activities
    cursor.execute('''
        (SELECT 'assignment' as type, a.title, sub.submission_date as time
         FROM sms_assignment_submissions sub
         JOIN sms_assignments a ON sub.assignment_id = a.assignment_id
         WHERE sub.student_id = %s
         ORDER BY sub.submission_date DESC LIMIT 3)
        UNION
        (SELECT 'grade' as type, CONCAT('Grade received for ', a.title) as title, sub.submission_date as time
         FROM sms_assignment_submissions sub
         JOIN sms_assignments a ON sub.assignment_id = a.assignment_id
         WHERE sub.student_id = %s AND sub.marks_obtained IS NOT NULL
         ORDER BY sub.submission_date DESC LIMIT 2)
        ORDER BY time DESC LIMIT 5
    ''', (student_table_id, student_table_id))
    recent_activities = cursor.fetchall()
    
    # Get upcoming events
    cursor.execute('''
        SELECT title, event_date, location 
        FROM sms_events 
        WHERE event_date >= CURDATE() 
        ORDER BY event_date ASC 
        LIMIT 5
    ''')
    events = cursor.fetchall()
    
    upcoming_events = []
    for event in events:
        event_date = event['event_date']
        if isinstance(event_date, (date, datetime)):
            upcoming_events.append({
                'title': event['title'],
                'day': event_date.day,
                'month': event_date.strftime('%b'),
                'location': event['location'] or 'School'
            })
        else:
            # Handle case where event_date is string
            try:
                event_date_obj = datetime.strptime(str(event_date), '%Y-%m-%d')
                upcoming_events.append({
                    'title': event['title'],
                    'day': event_date_obj.day,
                    'month': event_date_obj.strftime('%b'),
                    'location': event['location'] or 'School'
                })
            except:
                upcoming_events.append({
                    'title': event['title'],
                    'day': '',
                    'month': '',
                    'location': event['location'] or 'School'
                })
    
    # Get student courses
    cursor.execute('''
        SELECT c.course_id, c.course_name, c.course_code
        FROM sms_courses c
        JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
        WHERE ce.student_id = %s
        LIMIT 5
    ''', (student_table_id,))
    user_courses = cursor.fetchall()
    
    # Get attendance stats
    cursor.execute('''
        SELECT c.name as class, 
               ROUND(AVG(CASE WHEN a.attendance_status = "present" THEN 1 ELSE 0 END) * 100, 1) as percentage
        FROM sms_students s
        JOIN sms_classes c ON s.class = c.id
        LEFT JOIN sms_attendance a ON s.id = a.student_id 
            AND a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        WHERE s.id = %s
        GROUP BY c.id, c.name
    ''', (student_table_id,))
    stats = cursor.fetchall()
    
    attendance_stats = []
    for stat in stats:
        attendance_stats.append({
            'class': stat['class'],
            'percentage': stat['percentage'] or 0
        })
    
    # Get pending assignments details
    cursor.execute('''
        SELECT a.*, c.course_name, DATEDIFF(a.due_date, CURDATE()) as days_left
        FROM sms_assignments a
        JOIN sms_courses c ON a.course_id = c.course_id
        JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
        WHERE ce.student_id = %s 
            AND a.due_date >= CURDATE()
            AND a.assignment_id NOT IN (
                SELECT assignment_id FROM sms_assignment_submissions 
                WHERE student_id = %s
            )
        ORDER BY a.due_date ASC 
        LIMIT 5
    ''', (student_table_id, student_table_id))
    pending_assignments_details = cursor.fetchall()
    
    return render_template("dashboard.html",
                         total_students=1,
                         total_teachers=0,
                         total_classes=1 if student and student.get('class') else 0,
                         recent_activities=recent_activities,
                         upcoming_events=upcoming_events,
                         attendance_stats=attendance_stats,
                         user_courses=user_courses,
                         pending_assignments=pending_assignments_details,
                         today=date.today(),
                         attendance_rate=attendance_rate,
                         enrolled_courses=enrolled_courses,
                         pending_assignments_count=pending_assignments)
    
@app.route("/teacher_dashboard")
@teacher_required
def teacher_dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get teacher info
    cursor.execute('SELECT * FROM sms_teacher WHERE teacher_id = %s', (session['userid'],))
    teacher_info = cursor.fetchone()
    
    # Get teacher's classes
    cursor.execute('''
        SELECT c.id, c.name, c.section, 
               COUNT(DISTINCT s.id) as student_count
        FROM sms_classes c
        LEFT JOIN sms_students s ON c.id = s.class
        WHERE c.teacher_id = %s
        GROUP BY c.id
    ''', (session['userid'],))
    teacher_classes = cursor.fetchall()
    
    # Get assignments to grade
    cursor.execute('''
        SELECT COUNT(DISTINCT sub.assignment_id) as count
        FROM sms_assignment_submissions sub
        JOIN sms_assignments a ON sub.assignment_id = a.assignment_id
        WHERE a.created_by = %s AND sub.marks_obtained IS NULL
    ''', (session['userid'],))
    assignments_to_grade_result = cursor.fetchone()
    assignments_to_grade = assignments_to_grade_result['count'] if assignments_to_grade_result else 0
    
    # Get average attendance
    cursor.execute('''
        SELECT ROUND(AVG(CASE WHEN a.attendance_status = 1 THEN 1 ELSE 0 END) * 100, 1) as avg_attendance
        FROM sms_attendance a
        JOIN sms_students s ON a.student_id = s.id
        JOIN sms_classes c ON s.class = c.id
        WHERE c.teacher_id = %s
        AND a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    ''', (session['userid'],))
    avg_attendance_result = cursor.fetchone()
    avg_attendance = avg_attendance_result['avg_attendance'] if avg_attendance_result else 0
    
    # Get live classes
    cursor.execute('''
        SELECT COUNT(*) as count FROM sms_online_classes 
        WHERE created_by = %s 
        AND schedule_time <= NOW() 
        AND schedule_time + INTERVAL duration MINUTE >= NOW()
    ''', (session['userid'],))
    live_classes_result = cursor.fetchone()
    live_classes = live_classes_result['count'] if live_classes_result else 0
    
    # Get recent submissions - FIXED: using submission_id instead of id
    cursor.execute('''
        SELECT sub.*, s.name as student_name, a.title as assignment_title,
            CASE WHEN sub.marks_obtained IS NOT NULL THEN 1 ELSE 0 END as graded
        FROM sms_assignment_submissions sub
        JOIN sms_students s ON sub.student_id = s.id
        JOIN sms_assignments a ON sub.assignment_id = a.assignment_id
        WHERE a.created_by = %s
        ORDER BY sub.submission_date DESC
        LIMIT 5
    ''', (session['userid'],))
    recent_submissions = cursor.fetchall()
    
    # Get upcoming deadlines
    cursor.execute('''
        SELECT a.title, c.course_name, a.due_date
        FROM sms_assignments a
        JOIN sms_courses c ON a.course_id = c.course_id
        WHERE a.created_by = %s AND a.due_date >= CURDATE()
        ORDER BY a.due_date ASC
        LIMIT 5
    ''', (session['userid'],))
    upcoming_deadlines = cursor.fetchall()
    
    # Get teacher subjects
    cursor.execute('''
        SELECT DISTINCT s.subject 
        FROM sms_subjects s
        JOIN sms_teacher t ON s.subject_id = t.subject_id
        WHERE t.teacher_id = %s
    ''', (session['userid'],))
    subjects = cursor.fetchall()
    teacher_subjects = [s['subject'] for s in subjects] if subjects else []
    
    return render_template("teacher_dashboard.html",
                         teacher_info=teacher_info,
                         teacher_classes=teacher_classes,
                         total_students=sum(c.get('student_count', 0) for c in teacher_classes),
                         total_classes=len(teacher_classes),
                         pending_assignments=assignments_to_grade,
                         avg_attendance=avg_attendance,
                         recent_submissions=recent_submissions,  # This is a list of dictionaries
                         upcoming_deadlines=upcoming_deadlines,
                         teacher_subjects=teacher_subjects,
                         live_classes=live_classes,
                         assignments_to_grade=assignments_to_grade)
    
@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    # Get user type from session
    user_type = session.get('type')
    
    # Redirect based on user type
    if user_type == 'teacher':
        return teacher_dashboard()
    elif user_type == 'student':
        return student_dashboard()
    else:
        # Default to admin dashboard
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # ========== ADMIN DASHBOARD (for 'administrator' type) ==========
    # Get basic statistics
    cursor.execute('SELECT COUNT(*) as count FROM sms_students')
    total_students_result = cursor.fetchone()
    total_students = total_students_result['count'] if total_students_result else 0
    
    cursor.execute('SELECT COUNT(*) as count FROM sms_teacher')
    total_teachers_result = cursor.fetchone()
    total_teachers = total_teachers_result['count'] if total_teachers_result else 0
    
    cursor.execute('SELECT COUNT(*) as count FROM sms_classes')
    total_classes_result = cursor.fetchone()
    total_classes = total_classes_result['count'] if total_classes_result else 0
    
    # Get today's date
    today = date.today()
    
    # Get recent activities
    cursor.execute('''
        (SELECT 'student' as type, 'New student registered' as title, created_at as time 
         FROM sms_students ORDER BY created_at DESC LIMIT 3)
        UNION
        (SELECT 'attendance' as type, 'Daily attendance taken' as title, attendance_date as time 
         FROM sms_attendance ORDER BY attendance_date DESC LIMIT 3)
        UNION
        (SELECT 'assignment' as type, 'New assignment posted' as title, created_at as time 
         FROM sms_assignments ORDER BY created_at DESC LIMIT 3)
        ORDER BY time DESC LIMIT 5
    ''')
    activities = cursor.fetchall()
    
    recent_activities = []
    for activity in activities:
        recent_activities.append({
            'type': activity['type'],
            'title': activity['title'],
            'time': activity['time']
        })
    
    # Get upcoming events
    cursor.execute('''
        SELECT title, event_date, location 
        FROM sms_events 
        WHERE event_date >= CURDATE() 
        ORDER BY event_date ASC 
        LIMIT 5
    ''')
    events = cursor.fetchall()
    
    upcoming_events = []
    for event in events:
        event_date = event['event_date']
        if isinstance(event_date, (date, datetime)):
            upcoming_events.append({
                'title': event['title'],
                'day': event_date.day,
                'month': event_date.strftime('%b'),
                'location': event['location'] or 'School'
            })
        else:
            # Handle case where event_date is string
            try:
                event_date_obj = datetime.strptime(str(event_date), '%Y-%m-%d')
                upcoming_events.append({
                    'title': event['title'],
                    'day': event_date_obj.day,
                    'month': event_date_obj.strftime('%b'),
                    'location': event['location'] or 'School'
                })
            except:
                upcoming_events.append({
                    'title': event['title'],
                    'day': '',
                    'month': '',
                    'location': event['location'] or 'School'
                })
    
    # Get attendance statistics (admin view)
    cursor.execute('''
        SELECT c.name as class, 
               ROUND(AVG(CASE WHEN a.attendance_status = "present" THEN 1 ELSE 0 END) * 100, 1) as percentage
        FROM sms_classes c
        LEFT JOIN sms_students s ON c.id = s.class
        LEFT JOIN sms_attendance a ON s.id = a.student_id 
            AND a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY c.id, c.name
        LIMIT 5
    ''')
    stats = cursor.fetchall()
    
    attendance_stats = []
    for stat in stats:
        attendance_stats.append({
            'class': stat['class'],
            'percentage': stat['percentage'] or 0
        })
    
    # Get popular courses
    cursor.execute('''
        SELECT c.course_name, COUNT(ce.student_id) as enrolled
        FROM sms_courses c
        LEFT JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
        GROUP BY c.course_id
        ORDER BY enrolled DESC
        LIMIT 5
    ''')
    user_courses = cursor.fetchall()
    
    # Get system status
    cursor.execute('SELECT 1 FROM sms_user LIMIT 1')
    system_online = cursor.fetchone() is not None
    
    return render_template("dashboard.html", 
                         total_students=total_students,
                         total_teachers=total_teachers,
                         total_classes=total_classes,
                         recent_activities=recent_activities,
                         upcoming_events=upcoming_events,
                         attendance_stats=attendance_stats,
                         user_courses=user_courses,
                         today=today,
                         system_online=system_online)
    
# ==================== TEMPLATE FILTERS ====================

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if isinstance(value, (datetime, date)):
        return value.strftime(format)
    elif isinstance(value, str):
        try:
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            return dt.strftime(format)
        except:
            try:
                dt = datetime.strptime(value, '%Y-%m-%d')
                return dt.strftime(format)
            except:
                return value
    return value

@app.template_filter('timeago')
def timeago(value):
    if not value:
        return ''
    
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                value = datetime.strptime(value, '%Y-%m-%d')
            except:
                return value
    
    now = datetime.now()
    diff = now - value
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes}m ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours}h ago'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days}d ago'
    else:
        return value.strftime('%b %d, %Y')

@app.template_filter('count_by_status')
def count_by_status_filter(assignments, status):
    """Count assignments by status"""
    if not assignments:
        return 0
    
    count = 0
    for assignment in assignments:
        if assignment.get('status') == status:
            count += 1
    return count

@app.template_filter('days_until')
def days_until_filter(value):
    """Calculate days until a given date (negative for overdue, positive for upcoming)"""
    if not value:
        return 0
    
    try:
        from datetime import datetime, date
        
        # Convert to date object
        if isinstance(value, str):
            for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                try:
                    value = datetime.strptime(value, fmt).date()
                    break
                except:
                    continue
        
        if isinstance(value, datetime):
            value = value.date()
        
        today = date.today()
        
        # Calculate difference
        delta = (value - today).days
        
        return delta
    except Exception as e:
        print(f"Error in days_until filter: {e}")
        return 0

@app.template_filter('timeuntil')
def timeuntil_filter(value):
    """Calculate time until a datetime"""
    if not value:
        return ""
    
    try:
        from datetime import datetime
        
        # Convert to datetime object
        if isinstance(value, str):
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except:
                    continue
        
        now = datetime.now()
        
        if value < now:
            return "Started"
        
        # Calculate time difference
        diff = value - now
        
        if diff.days > 0:
            return f"In {diff.days} days"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"In {hours} hours"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"In {minutes} minutes"
        else:
            return "Now"
            
    except Exception as e:
        print(f"Error in timeuntil filter: {e}")
        return ""


# ==================== CONTEXT PROCESSOR ====================

@app.context_processor
def inject_user_data():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Get last login time
        cursor.execute('SELECT last_login FROM sms_user WHERE id = %s', (session['userid'],))
        user = cursor.fetchone()
        last_login = user['last_login'] if user else None
        
        data = {
            'last_login': last_login.strftime('%Y-%m-%d %H:%M') if last_login else 'Today 09:45 AM'
        }
        
        if session['role'] == 'admin':
            cursor.execute('SELECT COUNT(*) as count FROM sms_students')
            result = cursor.fetchone()
            data['total_students'] = result['count'] if result else 0
            
            cursor.execute('SELECT COUNT(*) as count FROM sms_teacher')
            result = cursor.fetchone()
            data['total_teachers'] = result['count'] if result else 0
            
            cursor.execute('SELECT COUNT(*) as count FROM sms_classes')
            result = cursor.fetchone()
            data['total_classes'] = result['count'] if result else 0
            
        elif session['role'] == 'teacher':
            # Get teacher-specific stats
            cursor.execute('''
                SELECT COUNT(*) as count FROM sms_classes WHERE teacher_id = %s
            ''', (session['userid'],))
            result = cursor.fetchone()
            data['my_classes_count'] = result['count'] if result else 0
            
            cursor.execute('''
                SELECT COUNT(DISTINCT s.id) as count 
                FROM sms_students s
                JOIN sms_classes c ON s.class = c.id
                WHERE c.teacher_id = %s
            ''', (session['userid'],))
            result = cursor.fetchone()
            data['my_students_count'] = result['count'] if result else 0
            
            cursor.execute('''
                SELECT COUNT(DISTINCT sub.assignment_id) as count
                FROM sms_assignment_submissions sub
                JOIN sms_assignments a ON sub.assignment_id = a.assignment_id
                WHERE a.created_by = %s AND sub.marks_obtained IS NULL
            ''', (session['userid'],))
            result = cursor.fetchone()
            data['assignments_to_grade'] = result['count'] if result else 0
            
            cursor.execute('''
                SELECT ROUND(AVG(CASE WHEN a.attendance_status = 1 THEN 1 ELSE 0 END) * 100, 1) as avg
                FROM sms_attendance a
                JOIN sms_students s ON a.student_id = s.id
                JOIN sms_classes c ON s.class = c.id
                WHERE c.teacher_id = %s
                AND a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            ''', (session['userid'],))
            result = cursor.fetchone()
            data['avg_attendance'] = result['avg'] if result else 0
            
        elif session['role'] == 'student':
            # Get student-specific stats
            cursor.execute('''
                SELECT COUNT(*) as count FROM sms_course_enrollments 
                WHERE student_id = %s
            ''', (session['userid'],))
            result = cursor.fetchone()
            data['enrolled_courses'] = result['count'] if result else 0
            
            cursor.execute('''
                SELECT COUNT(DISTINCT s.class) as count 
                FROM sms_students s
                WHERE s.id = %s
            ''', (session['userid'],))
            result = cursor.fetchone()
            data['enrolled_classes'] = result['count'] if result else 0
            
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM sms_assignments a
                JOIN sms_course_enrollments ce ON a.course_id = ce.course_id
                WHERE ce.student_id = %s 
                    AND a.due_date >= CURDATE()
                    AND a.assignment_id NOT IN (
                        SELECT assignment_id FROM sms_assignment_submissions 
                        WHERE student_id = %s
                    )
            ''', (session['userid'], session['userid']))
            result = cursor.fetchone()
            data['pending_assignments'] = result['count'] if result else 0
            
            cursor.execute('''
                SELECT ROUND(AVG(CASE WHEN attendance_status = 1 THEN 1 ELSE 0 END) * 100, 1) as rate
                FROM sms_attendance 
                WHERE student_id = %s 
                AND attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            ''', (session['userid'],))
            result = cursor.fetchone()
            data['attendance_rate'] = result['rate'] if result else 0
            # ADD THIS: Get live classes count for student
            cursor.execute('''
                SELECT COUNT(*) as count 
                FROM sms_online_classes oc
                JOIN sms_courses c ON oc.course_id = c.course_id
                JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
                WHERE ce.student_id = %s 
                    AND oc.schedule_time <= NOW() 
                    AND oc.schedule_time + INTERVAL oc.duration MINUTE >= NOW()
            ''', (session['userid'],))
            result = cursor.fetchone()
            data['live_classes'] = result['count'] if result else 0
        return data
    
    return {}

# ==================== ADMIN MANAGEMENT PAGES ====================

@app.route("/teacher", methods=['GET', 'POST'])
@admin_required
def teacher():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT t.teacher_id, t.teacher, s.subject FROM sms_teacher t LEFT JOIN sms_subjects s ON s.subject_id = t.subject_id')
    teachers = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_subjects')
    subjects = cursor.fetchall()
    
    return render_template("teacher.html", teachers=teachers, subjects=subjects)

@app.route("/edit_teacher", methods=['GET'])
@admin_required
def edit_teacher():
    teacher_id = request.args.get('teacher_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT t.teacher_id, t.teacher, s.subject FROM sms_teacher t LEFT JOIN sms_subjects s ON s.subject_id = t.subject_id WHERE t.teacher_id = %s', (teacher_id,))
    teachers = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_subjects')
    subjects = cursor.fetchall()
    
    return render_template("edit_teacher.html", teachers=teachers, subjects=subjects)

@app.route("/save_teacher", methods=['GET', 'POST'])
@admin_required
def save_teacher():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST' and 'teacher_name' in request.form and 'specialization' in request.form:
        teacher_name = request.form['teacher_name']
        specialization = request.form['specialization']
        action = request.form['action']
        
        if action == 'updateTeacher':
            teacherid = request.form['teacherid']
            cursor.execute('UPDATE sms_teacher SET teacher = %s, subject_id = %s WHERE teacher_id = %s', (teacher_name, specialization, teacherid))
            mysql.connection.commit()
            flash('Teacher updated successfully!', 'success')
        else:
            cursor.execute('INSERT INTO sms_teacher (teacher, subject_id) VALUES (%s, %s)', (teacher_name, specialization))
            mysql.connection.commit()
            flash('Teacher added successfully!', 'success')
        return redirect(url_for('teacher'))
    
    flash('Please fill out the form correctly!', 'error')
    return redirect(url_for('teacher'))

@app.route("/delete_teacher", methods=['GET'])
@admin_required
def delete_teacher():
    teacher_id = request.args.get('teacher_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM sms_teacher WHERE teacher_id = %s', (teacher_id,))
    mysql.connection.commit()
    flash('Teacher deleted successfully!', 'success')
    return redirect(url_for('teacher'))

@app.route("/subject", methods=['GET', 'POST'])
@admin_required
def subject():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM sms_subjects')
    subjects = cursor.fetchall()
    
    return render_template("subject.html", subjects=subjects)

@app.route("/save_subject", methods=['GET', 'POST'])
@admin_required
def save_subject():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST' and 'subject' in request.form and 's_type' in request.form and 'code' in request.form:
        subject = request.form['subject']
        s_type = request.form['s_type']
        code = request.form['code']
        action = request.form['action']
        
        if action == 'updateSubject':
            subjectid = request.form['subjectid']
            cursor.execute('UPDATE sms_subjects SET subject = %s, type = %s, code = %s WHERE subject_id = %s', (subject, s_type, code, subjectid))
            mysql.connection.commit()
            flash('Subject updated successfully!', 'success')
        else:
            cursor.execute('INSERT INTO sms_subjects (subject, type, code) VALUES (%s, %s, %s)', (subject, s_type, code))
            mysql.connection.commit()
            flash('Subject added successfully!', 'success')
        return redirect(url_for('subject'))
    
    flash('Please fill out the form correctly!', 'error')
    return redirect(url_for('subject'))

@app.route("/edit_subject", methods=['GET'])
@admin_required
def edit_subject():
    subject_id = request.args.get('subject_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT subject_id, subject, type, code FROM sms_subjects WHERE subject_id = %s', (subject_id,))
    subjects = cursor.fetchall()
    
    return render_template("edit_subject.html", subjects=subjects)

@app.route("/delete_subject", methods=['GET'])
@admin_required
def delete_subject():
    subject_id = request.args.get('subject_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM sms_subjects WHERE subject_id = %s', (subject_id,))
    mysql.connection.commit()
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('subject'))

@app.route("/classes", methods=['GET', 'POST'])
@admin_required
def classes():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT c.id, c.name, s.section, t.teacher FROM sms_classes c LEFT JOIN sms_section s ON s.section_id = c.section LEFT JOIN sms_teacher t ON t.teacher_id = c.teacher_id')
    classes = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_section')
    sections = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_teacher')
    teachers = cursor.fetchall()
    
    return render_template("class.html", classes=classes, sections=sections, teachers=teachers)

@app.route("/edit_class", methods=['GET'])
@admin_required
def edit_class():
    class_id = request.args.get('class_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT c.id, c.name, s.section, t.teacher FROM sms_classes c LEFT JOIN sms_section s ON s.section_id = c.section LEFT JOIN sms_teacher t ON t.teacher_id = c.teacher_id WHERE c.id = %s', (class_id,))
    classes = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_section')
    sections = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_teacher')
    teachers = cursor.fetchall()
    
    return render_template("edit_class.html", classes=classes, sections=sections, teachers=teachers)

@app.route("/save_class", methods=['GET', 'POST'])
@admin_required
def save_class():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST' and 'cname' in request.form:
        cname = request.form['cname']
        sectionid = request.form['sectionid']
        teacherid = request.form['teacherid']
        action = request.form['action']
        
        if action == 'updateClass':
            class_id = request.form['classid']
            cursor.execute('UPDATE sms_classes SET name = %s, section = %s, teacher_id = %s WHERE id = %s', (cname, sectionid, teacherid, class_id))
            mysql.connection.commit()
            flash('Class updated successfully!', 'success')
        else:
            cursor.execute('INSERT INTO sms_classes (name, section, teacher_id) VALUES (%s, %s, %s)', (cname, sectionid, teacherid))
            mysql.connection.commit()
            flash('Class added successfully!', 'success')
        return redirect(url_for('classes'))
    
    flash('Please fill out the form correctly!', 'error')
    return redirect(url_for('classes'))

@app.route("/delete_class", methods=['GET'])
@admin_required
def delete_class():
    class_id = request.args.get('class_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM sms_classes WHERE id = %s', (class_id,))
    mysql.connection.commit()
    flash('Class deleted successfully!', 'success')
    return redirect(url_for('classes'))

@app.route("/sections", methods=['GET', 'POST'])
@admin_required
def sections():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM sms_section')
    sections = cursor.fetchall()
    
    return render_template("sections.html", sections=sections)

@app.route("/edit_sections", methods=['GET'])
@admin_required
def edit_sections():
    section_id = request.args.get('section_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM sms_section WHERE section_id = %s', (section_id,))
    sections = cursor.fetchall()
    
    return render_template("edit_section.html", sections=sections)

@app.route("/save_sections", methods=['GET', 'POST'])
@admin_required
def save_sections():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST' and 'section_name' in request.form:
        section_name = request.form['section_name']
        action = request.form['action']
        
        if action == 'updateSection':
            section_id = request.form['sectionid']
            cursor.execute('UPDATE sms_section SET section = %s WHERE section_id = %s', (section_name, section_id))
            mysql.connection.commit()
            flash('Section updated successfully!', 'success')
        else:
            cursor.execute('INSERT INTO sms_section (section) VALUES (%s)', (section_name,))
            mysql.connection.commit()
            flash('Section added successfully!', 'success')
        return redirect(url_for('sections'))
    
    flash('Please fill out the form correctly!', 'error')
    return redirect(url_for('sections'))

@app.route("/delete_sections", methods=['GET'])
@admin_required
def delete_sections():
    section_id = request.args.get('section_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM sms_section WHERE section_id = %s', (section_id,))
    mysql.connection.commit()
    flash('Section deleted successfully!', 'success')
    return redirect(url_for('sections'))

@app.route("/student", methods=['GET', 'POST'])
@admin_required
def student():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT s.id, s.admission_no, s.roll_no, s.name, s.photo, c.name AS class, sec.section FROM sms_students s LEFT JOIN sms_section sec ON sec.section_id = s.section LEFT JOIN sms_classes c ON c.id = s.class')
    students = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_classes')
    classes = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_section')
    sections = cursor.fetchall()
    
    return render_template("student.html", students=students, classes=classes, sections=sections)

@app.route("/edit_student", methods=['GET'])
@admin_required
def edit_student():
    student_id = request.args.get('student_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT s.id, s.admission_no, s.roll_no, s.name, s.photo, c.name AS class, sec.section FROM sms_students s LEFT JOIN sms_section sec ON sec.section_id = s.section LEFT JOIN sms_classes c ON c.id = s.class WHERE s.id = %s', (student_id,))
    students = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_classes')
    classes = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_section')
    sections = cursor.fetchall()
    
    return render_template("edit_student.html", students=students, classes=classes, sections=sections)

@app.route("/save_student", methods=['GET', 'POST'])
@admin_required
def save_student():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST' and 'sname' in request.form:
        admission_no = request.form.get('registerNo')
        roll_no = request.form.get('rollNo')
        name = request.form['sname']
        class_id = request.form.get('classid')
        section_id = request.form.get('sectionid')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        gender = request.form.get('gender')
        dob = request.form.get('dob')
        address = request.form.get('address')
        father_name = request.form.get('fname')
        mother_name = request.form.get('mname')
        academic_year = request.form.get('year')
        admission_date = request.form.get('admission_date')
        
        action = request.form.get('action')
        
        if action == 'updateStudent':
            student_id = request.form.get('studentid')
            cursor.execute('''
                UPDATE sms_students SET 
                admission_no = %s, roll_no = %s, name = %s, class = %s, section = %s,
                email = %s, mobile = %s, gender = %s, dob = %s, current_address = %s,
                father_name = %s, mother_name = %s, academic_year = %s, admission_date = %s
                WHERE id = %s
            ''', (admission_no, roll_no, name, class_id, section_id, email, mobile, gender, dob, address, father_name, mother_name, academic_year, admission_date, student_id))
            mysql.connection.commit()
            flash('Student updated successfully!', 'success')
        else:
            cursor.execute('''
                INSERT INTO sms_students 
                (admission_no, roll_no, name, class, section, email, mobile, gender, dob, 
                current_address, father_name, mother_name, academic_year, admission_date, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ''', (admission_no, roll_no, name, class_id, section_id, email, mobile, gender, dob, address, father_name, mother_name, academic_year, admission_date))
            mysql.connection.commit()
            flash('Student added successfully!', 'success')
        return redirect(url_for('student'))
    
    flash('Please fill out the form correctly!', 'error')
    return redirect(url_for('student'))

@app.route("/delete_student", methods=['GET'])
@admin_required
def delete_student():
    student_id = request.args.get('student_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM sms_students WHERE id = %s', (student_id,))
    mysql.connection.commit()
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('student'))

# ==================== ATTENDANCE ====================

@app.route("/attendance", methods=['GET', 'POST'])
@login_required
def attendance():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if session['role'] == 'admin':
        cursor.execute('SELECT * FROM sms_classes')
        classes = cursor.fetchall()
        
        cursor.execute('SELECT * FROM sms_section')
        sections = cursor.fetchall()
        
        return render_template("attendance.html", classes=classes, sections=sections)
    
    elif session['role'] == 'teacher':
        # Teacher sees only their classes
        cursor.execute('SELECT c.* FROM sms_classes c WHERE c.teacher_id = %s', (session['userid'],))
        classes = cursor.fetchall()
        
        cursor.execute('SELECT DISTINCT s.section_id, s.section FROM sms_section s JOIN sms_classes c ON s.section_id = c.section WHERE c.teacher_id = %s', (session['userid'],))
        sections = cursor.fetchall()
        
        return render_template("attendance.html", classes=classes, sections=sections)
    
    else:  # Student
        # First, get the student_id
        student_id = session.get('student_id')
        if not student_id:
            cursor.execute('SELECT id FROM sms_students WHERE user_id = %s', (session['userid'],))
            student = cursor.fetchone()
            if student:
                student_id = student['id']
            else:
                flash('Student information not found!', 'error')
                return redirect(url_for('dashboard'))
        
        cursor.execute('''
            SELECT a.*, c.name as class_name
            FROM sms_attendance a
            JOIN sms_students s ON a.student_id = s.id
            JOIN sms_classes c ON s.class = c.id
            WHERE s.id = %s
            ORDER BY a.attendance_date DESC
            LIMIT 30
        ''', (student_id,))
        attendance_records = cursor.fetchall()
        
        # For now, use a simple template - create student_attendance.html or use existing template
        # Let's create a simple template on the fly if needed
        return render_template("student_attendance.html", attendance_records=attendance_records)
    
@app.route("/getClassAttendance", methods=['GET', 'POST'])
@login_required
def getClassAttendance():
    if request.method == 'POST' and 'classid' in request.form and 'sectionid' in request.form:
        classid = request.form['classid']
        sectionid = request.form['sectionid']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('SELECT * FROM sms_classes')
        classes = cursor.fetchall()
        
        cursor.execute('SELECT * FROM sms_section')
        sections = cursor.fetchall()
        
        currentDate = date.today().strftime('%Y/%m/%d')
        
        cursor.execute('SELECT s.id, s.name, s.photo, s.gender, s.dob, s.mobile, s.email, s.current_address, s.father_name, s.mother_name,s.admission_no, s.roll_no, s.admission_date, s.academic_year, a.attendance_status, a.attendance_date FROM sms_students as s LEFT JOIN sms_attendance as a ON s.id = a.student_id WHERE s.class = %s AND s.section = %s', (classid, sectionid))
        students = cursor.fetchall()
        
        return render_template("attendance.html", classes=classes, sections=sections, students=students, classId=classid, sectionId=sectionid)
    
    flash('Please select class and section!', 'error')
    return redirect(url_for('attendance'))

# ==================== REPORTS ====================

@app.route("/report", methods=['GET', 'POST'])
@login_required
def report():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('SELECT * FROM sms_classes')
    classes = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_section')
    sections = cursor.fetchall()
    
    return render_template("report.html", classes=classes, sections=sections)

# ==================== LMS FEATURES ====================

@app.route("/courses", methods=['GET', 'POST'])
@login_required
def courses():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if session['role'] == 'admin':
        # Admin sees all courses
        cursor.execute('''
            SELECT c.*, t.teacher, 
                   (SELECT COUNT(*) FROM sms_course_enrollments WHERE course_id = c.course_id) as enrolled_students
            FROM sms_courses c
            LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
            ORDER BY c.created_at DESC
        ''')
        courses_list = cursor.fetchall()
        
        cursor.execute('SELECT teacher_id, teacher FROM sms_teacher')
        teachers = cursor.fetchall()
        
    elif session['role'] == 'teacher':
        # Teacher sees only their courses
        cursor.execute('''
            SELECT c.*, 
                   (SELECT COUNT(*) FROM sms_course_enrollments WHERE course_id = c.course_id) as enrolled_students
            FROM sms_courses c
            WHERE c.teacher_id = %s
            ORDER BY c.created_at DESC
        ''', (session['userid'],))
        courses_list = cursor.fetchall()
        
        teachers = [{'teacher_id': session['userid'], 'teacher': session['name']}]
        
    else:  # Student
        # Student sees only enrolled courses
        cursor.execute('''
            SELECT c.*, t.teacher,
                   (SELECT COUNT(*) FROM sms_course_enrollments WHERE course_id = c.course_id) as enrolled_students
            FROM sms_courses c
            JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
            LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
            WHERE ce.student_id = %s
            ORDER BY c.created_at DESC
        ''', (session['userid'],))
        courses_list = cursor.fetchall()
        
        teachers = []
    
    if request.method == 'POST' and session['role'] in ['admin', 'teacher']:
        course_name = request.form.get('course_name')
        course_code = request.form.get('course_code')
        description = request.form.get('description')
        teacher_id = request.form.get('teacher_id') or session['userid']
        
        cursor.execute('''
            INSERT INTO sms_courses (course_name, course_code, description, teacher_id, created_by)
            VALUES (%s, %s, %s, %s, %s)
        ''', (course_name, course_code, description, teacher_id, session['userid']))
        mysql.connection.commit()
        flash('Course added successfully!', 'success')
        return redirect(url_for('courses'))
    
    return render_template("courses.html", courses=courses_list, teachers=teachers)

@app.route("/course/<int:course_id>")
@login_required
def course_details(course_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Check if student is enrolled or user has access
    if session['role'] == 'student':
        cursor.execute('''
            SELECT * FROM sms_course_enrollments 
            WHERE course_id = %s AND student_id = %s
        ''', (course_id, session['userid']))
        enrollment = cursor.fetchone()
        if not enrollment:
            flash('You are not enrolled in this course!', 'error')
            return redirect(url_for('courses'))
    
    # Get course details
    cursor.execute('''
        SELECT c.*, t.teacher 
        FROM sms_courses c
        LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
        WHERE c.course_id = %s
    ''', (course_id,))
    course = cursor.fetchone()
    
    # Get course materials
    cursor.execute('''
        SELECT * FROM sms_course_materials 
        WHERE course_id = %s 
        ORDER BY created_at DESC
    ''', (course_id,))
    materials = cursor.fetchall()
    
    # Get assignments
    cursor.execute('''
        SELECT a.*, 
               (SELECT COUNT(*) FROM sms_assignment_submissions 
                WHERE assignment_id = a.assignment_id) as submissions
        FROM sms_assignments a
        WHERE a.course_id = %s
        ORDER BY a.due_date ASC
    ''', (course_id,))
    assignments = cursor.fetchall()
    
    # Get announcements
    cursor.execute('''
        SELECT * FROM sms_announcements 
        WHERE course_id = %s 
        ORDER BY created_at DESC 
        LIMIT 5
    ''', (course_id,))
    announcements = cursor.fetchall()
    
    # Check if student is enrolled
    enrollment = None
    if session['role'] == 'student':
        cursor.execute('''
            SELECT * FROM sms_course_enrollments 
            WHERE course_id = %s AND student_id = %s
        ''', (course_id, session['userid']))
        enrollment = cursor.fetchone()
    
    return render_template("course_details.html", 
                          course=course, 
                          materials=materials, 
                          assignments=assignments,
                          announcements=announcements,
                          enrollment=enrollment)

@app.route("/assignments", methods=['GET', 'POST'])
@login_required
def assignments():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST' and session['role'] in ['admin', 'teacher']:
        title = request.form.get('title')
        description = request.form.get('description')
        course_id = request.form.get('course_id')
        due_date = request.form.get('due_date')
        max_marks = request.form.get('max_marks')
        
        cursor.execute('''
            INSERT INTO sms_assignments (title, description, course_id, due_date, max_marks, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (title, description, course_id, due_date, max_marks, session['userid']))
        mysql.connection.commit()
        flash('Assignment created successfully!', 'success')
        return redirect(url_for('assignments'))
    
    # Get assignments based on user role
    if session['role'] == 'teacher':
        cursor.execute('''
            SELECT a.*, c.course_name,
                   (SELECT COUNT(*) FROM sms_assignment_submissions 
                    WHERE assignment_id = a.assignment_id) as submissions,
                   (SELECT COUNT(*) FROM sms_course_enrollments 
                    WHERE course_id = a.course_id) as total_students
            FROM sms_assignments a
            JOIN sms_courses c ON a.course_id = c.course_id
            WHERE a.created_by = %s
            ORDER BY a.due_date ASC
        ''', (session['userid'],))
        assignments_list = cursor.fetchall()
        
        # Get courses for dropdown
        cursor.execute('SELECT course_id, course_name FROM sms_courses WHERE teacher_id = %s', (session['userid'],))
        courses = cursor.fetchall()
        
    elif session['role'] == 'student':
        cursor.execute('''
            SELECT a.*, c.course_name, s.submission_date, s.marks_obtained,
                   CASE WHEN s.submission_id IS NOT NULL THEN 'Submitted'
                        WHEN a.due_date < CURDATE() THEN 'Overdue'
                        ELSE 'Pending' END as status
            FROM sms_assignments a
            JOIN sms_courses c ON a.course_id = c.course_id
            JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
            LEFT JOIN sms_assignment_submissions s ON a.assignment_id = s.assignment_id 
                AND s.student_id = %s
            WHERE ce.student_id = %s
            ORDER BY a.due_date ASC
        ''', (session['userid'], session['userid']))
        assignments_list = cursor.fetchall()
        courses = []
        
    else:  # Admin
        cursor.execute('''
            SELECT a.*, c.course_name, t.teacher,
                   (SELECT COUNT(*) FROM sms_assignment_submissions 
                    WHERE assignment_id = a.assignment_id) as submissions
            FROM sms_assignments a
            JOIN sms_courses c ON a.course_id = c.course_id
            LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
            ORDER BY a.due_date ASC
        ''')
        assignments_list = cursor.fetchall()
        
        cursor.execute('SELECT course_id, course_name FROM sms_courses')
        courses = cursor.fetchall()
    
    return render_template("assignments.html", assignments=assignments_list, courses=courses)

@app.route("/assignment/<int:assignment_id>", methods=['GET', 'POST'])
@login_required
def assignment_details(assignment_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get assignment details
    cursor.execute('''
        SELECT a.*, c.course_name, t.teacher
        FROM sms_assignments a
        JOIN sms_courses c ON a.course_id = c.course_id
        JOIN sms_teacher t ON c.teacher_id = t.teacher_id
        WHERE a.assignment_id = %s
    ''', (assignment_id,))
    assignment = cursor.fetchone()
    
    if not assignment:
        flash('Assignment not found!', 'error')
        return redirect(url_for('assignments'))
    
    # Check if student is enrolled in the course
    if session['role'] == 'student':
        cursor.execute('''
            SELECT * FROM sms_course_enrollments ce
            JOIN sms_assignments a ON ce.course_id = a.course_id
            WHERE ce.student_id = %s AND a.assignment_id = %s
        ''', (session['userid'], assignment_id))
        enrollment = cursor.fetchone()
        if not enrollment:
            flash('You are not enrolled in this course!', 'error')
            return redirect(url_for('assignments'))
    
    if request.method == 'POST' and session['role'] == 'student':
        submission_text = request.form.get('submission_text')
        file = request.files.get('submission_file')
        
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        cursor.execute('''
            INSERT INTO sms_assignment_submissions 
            (assignment_id, student_id, submission_text, file_path, submission_date)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
            submission_text = VALUES(submission_text),
            file_path = VALUES(file_path),
            submission_date = NOW()
        ''', (assignment_id, session['userid'], submission_text, filename))
        mysql.connection.commit()
        flash('Assignment submitted successfully!', 'success')
        return redirect(url_for('assignment_details', assignment_id=assignment_id))
    
    # Get submission if student
    submission = None
    if session['role'] == 'student':
        cursor.execute('''
            SELECT * FROM sms_assignment_submissions 
            WHERE assignment_id = %s AND student_id = %s
        ''', (assignment_id, session['userid']))
        submission = cursor.fetchone()
    
    # Get all submissions if teacher or admin
    submissions = None
    if session['role'] in ['teacher', 'admin']:
        cursor.execute('''
            SELECT s.*, st.name, st.admission_no
            FROM sms_assignment_submissions s
            JOIN sms_students st ON s.student_id = st.id
            WHERE s.assignment_id = %s
            ORDER BY s.submission_date DESC
        ''', (assignment_id,))
        submissions = cursor.fetchall()
    
    return render_template("assignment_details.html", 
                          assignment=assignment, 
                          submission=submission,
                          submissions=submissions)

    # Create discussions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sms_discussions (
            discussion_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            content TEXT,
            course_id INT,
            created_by INT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES sms_courses(course_id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES sms_user(id) ON DELETE CASCADE
        )
    ''')

    # Create discussion replies table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sms_discussion_replies (
            reply_id INT AUTO_INCREMENT PRIMARY KEY,
            discussion_id INT,
            user_id INT,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (discussion_id) REFERENCES sms_discussions(discussion_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES sms_user(id) ON DELETE CASCADE
        )
    ''')

    # Create resources table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sms_resources (
            resource_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            course_id INT,
            resource_type ENUM('document', 'video', 'link', 'presentation') DEFAULT 'document',
            file_url VARCHAR(500),
            external_url VARCHAR(500),
            uploaded_by INT,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            downloads INT DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES sms_courses(course_id) ON DELETE CASCADE,
            FOREIGN KEY (uploaded_by) REFERENCES sms_user(id) ON DELETE CASCADE
        )
    ''')

    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sms_messages (
            message_id INT AUTO_INCREMENT PRIMARY KEY,
            sender_id INT,
            receiver_id INT,
            content TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES sms_user(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES sms_user(id) ON DELETE CASCADE
        )
    ''')

@app.route("/announcements", methods=['GET', 'POST'])
@login_required
def announcements():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST' and session['role'] in ['admin', 'teacher']:
        title = request.form.get('title')
        content = request.form.get('content')
        announcement_type = request.form.get('type')
        course_id = request.form.get('course_id')
        
        cursor.execute('''
            INSERT INTO sms_announcements 
            (title, content, announcement_type, course_id, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        ''', (title, content, announcement_type, course_id, session['userid']))
        mysql.connection.commit()
        flash('Announcement published successfully!', 'success')
        return redirect(url_for('announcements'))
    
    # Get announcements based on user role - FIXED: Use announcement_type instead of type
    if session['role'] == 'teacher':
        cursor.execute('''
            SELECT a.*, c.course_name, u.first_name as created_by_name
            FROM sms_announcements a
            LEFT JOIN sms_courses c ON a.course_id = c.course_id
            JOIN sms_user u ON a.created_by = u.id
            WHERE a.created_by = %s OR a.announcement_type = 'school'
            ORDER BY a.created_at DESC
        ''', (session['userid'],))
        announcements_list = cursor.fetchall()
        
        # Get courses for dropdown
        cursor.execute('SELECT course_id, course_name FROM sms_courses WHERE teacher_id = %s', (session['userid'],))
        courses = cursor.fetchall()
        
    elif session['role'] == 'student':
        cursor.execute('''
            SELECT a.*, c.course_name, u.first_name as created_by_name
            FROM sms_announcements a
            LEFT JOIN sms_courses c ON a.course_id = c.course_id
            JOIN sms_user u ON a.created_by = u.id
            WHERE a.announcement_type = 'school' 
               OR a.course_id IN (
                   SELECT course_id FROM sms_course_enrollments 
                   WHERE student_id = %s
               )
            ORDER BY a.created_at DESC
        ''', (session['userid'],))
        announcements_list = cursor.fetchall()
        courses = []
        
    else:  # Admin
        cursor.execute('''
            SELECT a.*, c.course_name, u.first_name as created_by_name
            FROM sms_announcements a
            LEFT JOIN sms_courses c ON a.course_id = c.course_id
            JOIN sms_user u ON a.created_by = u.id
            ORDER BY a.created_at DESC
        ''')
        announcements_list = cursor.fetchall()
        
        cursor.execute('SELECT course_id, course_name FROM sms_courses')
        courses = cursor.fetchall()
    
    return render_template("announcements.html", announcements=announcements_list, courses=courses)

@app.route('/gradebook')
def gradebook():
    
    cursor = mysql.connection.cursor()
    
    try:
        # Get teacher's courses
        cursor.execute('''
            SELECT c.id, c.course_name, 
                   COUNT(DISTINCT sc.student_id) as student_count
            FROM courses c
            LEFT JOIN student_courses sc ON c.id = sc.course_id
            WHERE c.teacher_id = %s
            GROUP BY c.id
        ''', (session['user_id'],))
        
        courses = cursor.fetchall()
        
        # Calculate total students across all courses
        total_students = 0
        for course in courses:
            total_students += course['student_count'] if course['student_count'] else 0
        
        # Get all grades for teacher's courses
        cursor.execute('''
            SELECT g.id, g.student_id, g.assignment_id, g.marks_obtained, 
                   g.max_marks, g.grade, g.remarks, g.graded_date,
                   a.title as assignment_title, a.due_date,
                   u.username as student_name,
                   c.course_name,
                   (g.marks_obtained / g.max_marks * 100) as percentage
            FROM grades g
            JOIN assignments a ON g.assignment_id = a.id
            JOIN courses c ON a.course_id = c.id
            JOIN users u ON g.student_id = u.id
            WHERE c.teacher_id = %s
            ORDER BY c.course_name, u.username, a.due_date DESC
        ''', (session['user_id'],))
        
        grades = cursor.fetchall()
        
        # Calculate statistics
        total_assignments = len(grades)
        graded_assignments = sum(1 for g in grades if g['marks_obtained'] is not None)
        pending_grades = total_assignments - graded_assignments
        
        cursor.close()
        
        return render_template("gradebook_teacher.html", 
                             grades=grades,
                             courses=courses,
                             total_students=total_students,
                             total_assignments=total_assignments,
                             graded_assignments=graded_assignments,
                             pending_grades=pending_grades)
                             
    except Exception as e:
        print(f"Error in gradebook: {e}")
        cursor.close()
        return render_template("gradebook_teacher.html", 
                             grades=[],
                             courses=[],
                             total_students=0,
                             total_assignments=0,
                             graded_assignments=0,
                             pending_grades=0)
    
    else:  # Student
        cursor.execute('''
            SELECT c.course_name, a.title as assignment_title,
                   a.max_marks, sub.marks_obtained,
                   ROUND((sub.marks_obtained / a.max_marks) * 100, 2) as percentage,
                   sub.submission_date, sub.feedback,
                   CASE 
                       WHEN sub.marks_obtained >= a.max_marks * 0.9 THEN 'A+'
                       WHEN sub.marks_obtained >= a.max_marks * 0.8 THEN 'A'
                       WHEN sub.marks_obtained >= a.max_marks * 0.7 THEN 'B'
                       WHEN sub.marks_obtained >= a.max_marks * 0.6 THEN 'C'
                       WHEN sub.marks_obtained >= a.max_marks * 0.5 THEN 'D'
                       ELSE 'F'
                   END as grade
            FROM sms_course_enrollments ce
            JOIN sms_courses c ON ce.course_id = c.course_id
            JOIN sms_assignments a ON c.course_id = a.course_id
            LEFT JOIN sms_assignment_submissions sub ON a.assignment_id = sub.assignment_id 
                AND sub.student_id = %s
            WHERE ce.student_id = %s
            ORDER BY c.course_name, a.due_date
        ''', (session['userid'], session['userid']))
        grades = cursor.fetchall()
        
        return render_template("gradebook_student.html", grades=grades)

@app.route("/online_classes", methods=['GET', 'POST'])
@login_required
def online_classes():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST' and session['role'] in ['admin', 'teacher']:
        title = request.form.get('title')
        description = request.form.get('description')
        course_id = request.form.get('course_id')
        meeting_link = request.form.get('meeting_link')
        schedule_time = request.form.get('schedule_time')
        duration = request.form.get('duration')
        
        cursor.execute('''
            INSERT INTO sms_online_classes 
            (title, description, course_id, meeting_link, schedule_time, duration, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (title, description, course_id, meeting_link, schedule_time, duration, session['userid']))
        mysql.connection.commit()
        flash('Online class scheduled successfully!', 'success')
        return redirect(url_for('online_classes'))
    
    # Get online classes based on role
    if session['role'] == 'teacher':
        cursor.execute('''
            SELECT oc.*, c.course_name
            FROM sms_online_classes oc
            JOIN sms_courses c ON oc.course_id = c.course_id
            WHERE oc.created_by = %s
            ORDER BY oc.schedule_time DESC
        ''', (session['userid'],))
        classes = cursor.fetchall()
        
        cursor.execute('SELECT course_id, course_name FROM sms_courses WHERE teacher_id = %s', (session['userid'],))
        courses = cursor.fetchall()
        
    elif session['role'] == 'student':
        cursor.execute('''
            SELECT oc.*, c.course_name,
                   CASE 
                       WHEN oc.schedule_time > NOW() THEN 'upcoming'
                       WHEN oc.schedule_time <= NOW() AND oc.schedule_time + INTERVAL oc.duration MINUTE >= NOW() THEN 'live'
                       ELSE 'completed'
                   END as status
            FROM sms_online_classes oc
            JOIN sms_courses c ON oc.course_id = c.course_id
            JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
            WHERE ce.student_id = %s
            ORDER BY oc.schedule_time DESC
        ''', (session['userid'],))
        classes = cursor.fetchall()
        
        cursor.execute('''
            SELECT c.course_id, c.course_name 
            FROM sms_courses c
            JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
            WHERE ce.student_id = %s
        ''', (session['userid'],))
        courses = cursor.fetchall()
        
    else:  # Admin
        cursor.execute('''
            SELECT oc.*, c.course_name, t.teacher
            FROM sms_online_classes oc
            JOIN sms_courses c ON oc.course_id = c.course_id
            LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
            ORDER BY oc.schedule_time DESC
        ''')
        classes = cursor.fetchall()
        
        cursor.execute('SELECT course_id, course_name FROM sms_courses')
        courses = cursor.fetchall()
    
    return render_template("online_classes.html", classes=classes, courses=courses)

# ==================== STUDENT PROFILE ====================

@app.route("/student_profile", methods=['GET', 'POST'])
@student_required
def student_profile():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get student details - FIXED: Use session['userid'] instead of session['userid']
    cursor.execute('''
        SELECT s.*, c.name as class_name, sec.section as section_name
        FROM sms_students s
        LEFT JOIN sms_classes c ON s.class = c.id
        LEFT JOIN sms_section sec ON s.section = sec.section_id
        WHERE s.id = %s
    ''', (session.get('student_id'),))  # Changed to session.get('student_id')
    
    student = cursor.fetchone()
    
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get academic stats
    cursor.execute('''
        SELECT 
            ROUND(AVG(CASE WHEN a.attendance_status = "present" THEN 1 ELSE 0 END) * 100, 1) as attendance_rate,
            COUNT(DISTINCT sub.assignment_id) as assignments_submitted,
            COUNT(DISTINCT a2.assignment_id) as total_assignments
        FROM sms_students s
        LEFT JOIN sms_attendance a ON s.id = a.student_id AND a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        LEFT JOIN sms_assignment_submissions sub ON s.id = sub.student_id
        LEFT JOIN sms_assignments a2 ON sub.assignment_id = a2.assignment_id
        WHERE s.id = %s
    ''', (session.get('student_id'),))
    stats = cursor.fetchone()
    
    if request.method == 'POST':
        # Update profile
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        address = request.form.get('address')
        new_password = request.form.get('new_password')
        
        update_fields = []
        values = []
        
        if email:
            update_fields.append("email = %s")
            values.append(email)
        if mobile:
            update_fields.append("mobile = %s")
            values.append(mobile)
        if address:
            update_fields.append("current_address = %s")
            values.append(address)
        
        if update_fields:
            values.append(session.get('student_id'))  # Changed to session.get('student_id')
            query = f"UPDATE sms_students SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(query, tuple(values))
            mysql.connection.commit()
            
            # Also update user table email
            if email:
                cursor.execute('UPDATE sms_user SET email = %s WHERE id = %s', (email, session['userid']))
                mysql.connection.commit()
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('student_profile'))
        
        # Update password if provided
        if new_password:
            cursor.execute('UPDATE sms_user SET password = %s WHERE id = %s', (new_password, session['userid']))
            mysql.connection.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('student_profile'))
    
    return render_template("student_profile.html", 
                         student=student,
                         attendance_rate=stats['attendance_rate'] if stats else 0,
                         assignments_submitted=stats['assignments_submitted'] if stats else 0,
                         total_assignments=stats['total_assignments'] if stats else 0)

# ==================== TEACHER-SPECIFIC PAGES ====================

@app.route("/my_classes")
@teacher_required
def my_classes():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('''
        SELECT c.*, COUNT(DISTINCT s.id) as student_count
        FROM sms_classes c
        LEFT JOIN sms_students s ON c.id = s.class
        WHERE c.teacher_id = %s
        GROUP BY c.id
        ORDER BY c.name
    ''', (session['userid'],))
    
    classes = cursor.fetchall()
    return render_template("teacher_classes.html", classes=classes)

@app.route("/my_students")
@teacher_required
def my_students():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('''
        SELECT s.*, c.name as class_name
        FROM sms_students s
        JOIN sms_classes c ON s.class = c.id
        WHERE c.teacher_id = %s
        ORDER BY s.name
    ''', (session['userid'],))
    
    students = cursor.fetchall()
    return render_template("teacher_students.html", students=students)

@app.route("/add_class", methods=['GET', 'POST'])
@teacher_required
def add_class():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        name = request.form.get('name')
        section = request.form.get('section')
        subject_id = request.form.get('subject_id')
        schedule = request.form.get('schedule')
        room = request.form.get('room')
        
        cursor.execute('''
            INSERT INTO sms_classes (name, section, teacher_id, subject_id, schedule, room)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (name, section, session['userid'], subject_id, schedule, room))
        mysql.connection.commit()
        
        flash('Class added successfully!', 'success')
        return redirect(url_for('my_classes'))
    
    cursor.execute('SELECT * FROM sms_subjects')
    subjects = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_section')
    sections = cursor.fetchall()
    
    return render_template("add_class.html", subjects=subjects, sections=sections)

# Add these routes to handle missing templates gracefully

@app.route("/add_course", methods=['GET', 'POST'])
@teacher_required
def add_course():
    """Add course - simplified version"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        course_name = request.form.get('course_name')
        course_code = request.form.get('course_code')
        description = request.form.get('description')
        
        cursor.execute('''
            INSERT INTO sms_courses (course_name, course_code, description, teacher_id, created_by)
            VALUES (%s, %s, %s, %s, %s)
        ''', (course_name, course_code, description, session['userid'], session['userid']))
        mysql.connection.commit()
        
        flash('Course added successfully!', 'success')
        return redirect(url_for('courses'))
    
    # Simple form for now
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Add Course</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-md mx-auto bg-white rounded-lg shadow-md p-6">
            <h1 class="text-2xl font-bold mb-6">Add New Course</h1>
            <form method="post">
                <div class="mb-4">
                    <label class="block text-gray-700 mb-2">Course Name</label>
                    <input type="text" name="course_name" class="w-full px-3 py-2 border rounded-lg" required>
                </div>
                <div class="mb-4">
                    <label class="block text-gray-700 mb-2">Course Code</label>
                    <input type="text" name="course_code" class="w-full px-3 py-2 border rounded-lg" required>
                </div>
                <div class="mb-4">
                    <label class="block text-gray-700 mb-2">Description</label>
                    <textarea name="description" class="w-full px-3 py-2 border rounded-lg" rows="3"></textarea>
                </div>
                <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700">
                    Add Course
                </button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route("/discussions", methods=['GET', 'POST'])
@login_required
def discussions():
    """Discussions page - simplified"""
    return redirect(url_for('courses'))  # Redirect to courses for now

@app.route("/quizzes", methods=['GET', 'POST'])
@login_required
def quizzes():
    """Quizzes page - simplified"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Quizzes</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold mb-6">Quizzes</h1>
            <div class="bg-white rounded-lg shadow-md p-6 text-center">
                <p class="text-gray-600 mb-4">Quiz feature is under development</p>
                <a href="{{ url_for('dashboard') }}" class="text-blue-600 hover:underline">
                    Return to Dashboard
                </a>
            </div>
        </div>
    </body>
    </html>
    '''
# ==================== STUDENT-SPECIFIC PAGES ====================

@app.route("/my_classes_student")
@student_required
def my_classes_student():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('''
        SELECT c.*, cr.course_name, t.teacher as teacher_name
        FROM sms_classes c
        JOIN sms_students s ON c.id = s.class
        LEFT JOIN sms_courses cr ON c.id = cr.class_id
        LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
        WHERE s.id = %s
        ORDER BY c.name
    ''', (session['userid'],))
    
    classes = cursor.fetchall()
    return render_template("student_my_classes.html", classes=classes)

# ==================== EXCEL IMPORT/EXPORT ====================

@app.route("/admin/import", methods=['GET'])
@admin_required
def admin_import():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('SELECT * FROM sms_classes')
    classes = cursor.fetchall()
    
    cursor.execute('SELECT * FROM sms_subjects')
    subjects = cursor.fetchall()
    
    # Get recent imports
    cursor.execute('''
        SELECT * FROM sms_import_log 
        ORDER BY import_date DESC 
        LIMIT 10
    ''')
    recent_imports = cursor.fetchall()
    
    return render_template("admin_import.html",
                         classes=classes,
                         subjects=subjects,
                         recent_imports=recent_imports)

@app.route("/import_students", methods=['POST'])
@admin_required
def import_students():
    if 'students_file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('admin_import'))
    
    file = request.files['students_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin_import'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Read Excel file
            df = pd.read_excel(filepath)
            
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            imported = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Check if student already exists
                    cursor.execute('SELECT id FROM sms_students WHERE admission_no = %s', (row.get('admission_no'),))
                    existing = cursor.fetchone()
                    
                    if existing and request.form.get('skip_duplicates') == 'on':
                        continue
                    
                    # Insert student
                    cursor.execute('''
                        INSERT INTO sms_students 
                        (admission_no, roll_no, name, email, mobile, gender, class, section, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ''', (
                        row.get('admission_no'),
                        row.get('roll_no'),
                        row.get('name'),
                        row.get('email'),
                        row.get('mobile'),
                        row.get('gender'),
                        request.form.get('default_class') or 1,
                        1  # Default section
                    ))
                    
                    student_id = cursor.lastrowid
                    
                    # Create user account
                    if row.get('email'):
                        password = generate_password()
                        cursor.execute('''
                            INSERT INTO sms_user (email, password, first_name, type, status)
                            VALUES (%s, %s, %s, 'student', 'active')
                        ''', (row.get('email'), password, row.get('name')))
                    
                    imported += 1
                    
                except Exception as e:
                    errors.append({
                        'row': index + 2,
                        'message': str(e),
                        'data': dict(row)
                    })
            
            mysql.connection.commit()
            
            # Log import
            cursor.execute('''
                INSERT INTO sms_import_log 
                (filename, import_type, records_imported, errors, import_date, status)
                VALUES (%s, 'students', %s, %s, NOW(), %s)
            ''', (filename, imported, json.dumps(errors), 'success' if imported > 0 else 'failed'))
            mysql.connection.commit()
            
            if imported > 0:
                flash(f'Successfully imported {imported} students', 'success')
            if errors:
                flash(f'{len(errors)} records had errors', 'warning')
            
        except Exception as e:
            flash(f'Error importing file: {str(e)}', 'error')
        
        # Clean up
        if os.path.exists(filepath):
            os.remove(filepath)
    
    return redirect(url_for('admin_import'))

@app.route("/import_teachers", methods=['POST'])
@admin_required
def import_teachers():
    if 'teachers_file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('admin_import'))
    
    file = request.files['teachers_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin_import'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            df = pd.read_excel(filepath)
            
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            imported = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Check if teacher already exists
                    cursor.execute('SELECT teacher_id FROM sms_teacher WHERE teacher = %s OR email = %s', 
                                 (row.get('teacher'), row.get('email')))
                    existing = cursor.fetchone()
                    
                    if existing and request.form.get('skip_duplicates') == 'on':
                        continue
                    
                    # Insert teacher record
                    cursor.execute('''
                        INSERT INTO sms_teacher 
                        (teacher, email, mobile, qualification, experience, subject_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (
                        row.get('teacher'),
                        row.get('email'),
                        row.get('mobile'),
                        row.get('qualification'),
                        row.get('experience'),
                        request.form.get('default_subject')
                    ))
                    
                    teacher_id = cursor.lastrowid
                    
                    # Create user account
                    if row.get('email'):
                        password = generate_password() if request.form.get('generate_password') == 'on' else 'teacher123'
                        cursor.execute('''
                            INSERT INTO sms_user (email, password, first_name, type, status)
                            VALUES (%s, %s, %s, 'teacher', 'active')
                        ''', (row.get('email'), password, row.get('teacher')))
                    
                    imported += 1
                    
                except Exception as e:
                    errors.append({
                        'row': index + 2,
                        'message': str(e),
                        'data': dict(row)
                    })
            
            mysql.connection.commit()
            
            # Log import
            cursor.execute('''
                INSERT INTO sms_import_log 
                (filename, import_type, records_imported, errors, import_date, status)
                VALUES (%s, 'teachers', %s, %s, NOW(), %s)
            ''', (filename, imported, json.dumps(errors), 'success' if imported > 0 else 'failed'))
            mysql.connection.commit()
            
            if imported > 0:
                flash(f'Successfully imported {imported} teachers', 'success')
            if errors:
                flash(f'{len(errors)} records had errors', 'warning')
            
        except Exception as e:
            flash(f'Error importing file: {str(e)}', 'error')
        
        # Clean up
        if os.path.exists(filepath):
            os.remove(filepath)
    
    return redirect(url_for('admin_import'))

@app.route("/download_template/<type>")
@admin_required
def download_template(type):
    if type == 'students':
        # Create sample student data
        data = {
            'admission_no': ['S2024001', 'S2024002', 'S2024003'],
            'roll_no': [1, 2, 3],
            'name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'email': ['john@email.com', 'jane@email.com', 'bob@email.com'],
            'mobile': ['9876543210', '9876543211', '9876543212'],
            'gender': ['male', 'female', 'male'],
            'dob': ['2005-01-15', '2005-03-22', '2005-05-30'],
            'father_name': ['John Doe Sr.', 'James Smith', 'William Johnson'],
            'mother_name': ['Mary Doe', 'Sarah Smith', 'Emma Johnson'],
            'address': ['123 Main St', '456 Oak Ave', '789 Pine Rd']
        }
    else:  # teachers
        data = {
            'teacher': ['Jane Smith', 'Robert Brown', 'Emily Davis'],
            'email': ['jane@email.com', 'robert@email.com', 'emily@email.com'],
            'mobile': ['9876543210', '9876543211', '9876543212'],
            'qualification': ['M.Ed, B.Ed', 'Ph.D, M.Sc', 'M.A, B.Ed'],
            'experience': [5, 8, 3]
        }
    
    df = pd.DataFrame(data)
    
    # Save to BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Template', index=False)
        worksheet = writer.sheets['Template']
        
        # Add formatting hints
        worksheet['L1'] = 'Instructions:'
        worksheet['L2'] = '1. Fill in all required fields'
        worksheet['L3'] = '2. Do not change column headers'
        worksheet['L4'] = '3. Save file as .xlsx format'
        worksheet['L5'] = '4. Remove these instructions before uploading'
    
    output.seek(0)
    
    return send_file(output, 
                     download_name=f'{type}_template.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ==================== ADDITIONAL ROUTES ====================

@app.route('/calendar')
def calendar():
    if 'user_id' not in session:
        session['user_id'] = 1  # Set to a valid user ID from your database
        session['username'] = 'testuser'
        session['role'] = 'teacher'
    
    cursor = mysql.connection.cursor()
    
    try:
        # Get user's courses - simplified version
        if session['role'] == 'teacher':
            cursor.execute('''
                SELECT course_id, course_name FROM sms_courses 
                WHERE teacher_id = %s
            ''', (session['user_id'],))
        else:  # student
            # Try with sms_student_courses table if it exists
            try:
                cursor.execute('''
                    SELECT c.course_id, c.course_name 
                    FROM sms_courses c
                    JOIN sms_student_courses sc ON c.course_id = sc.course_id
                    WHERE sc.student_id = %s
                ''', (session['user_id'],))
            except:
                # If table doesn't exist, just get all courses or empty list
                cursor.execute('SELECT course_id, course_name FROM sms_courses LIMIT 10')
        
        courses = cursor.fetchall()
        
        # Get upcoming events - simplified query
        try:
            cursor.execute('''
                SELECT e.*, c.course_name 
                FROM sms_calendar_events e
                LEFT JOIN sms_courses c ON e.course_id = c.course_id
                WHERE e.user_id = %s OR e.course_id IS NULL
                AND e.event_date >= CURDATE()
                ORDER BY e.event_date ASC, e.event_time ASC
                LIMIT 20
            ''', (session['user_id'],))
            
            upcoming_events = cursor.fetchall()
        except:
            upcoming_events = []
        
        # Get event statistics
        try:
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN event_type = 'assignment' THEN 1 ELSE 0 END) as assignments,
                    SUM(CASE WHEN event_type = 'exam' THEN 1 ELSE 0 END) as exams,
                    SUM(CASE WHEN event_type = 'holiday' THEN 1 ELSE 0 END) as holidays,
                    SUM(CASE WHEN event_type NOT IN ('assignment', 'exam', 'holiday') THEN 1 ELSE 0 END) as other,
                    COUNT(*) as total_events
                FROM sms_calendar_events
                WHERE user_id = %s
                AND MONTH(event_date) = MONTH(CURDATE())
                AND YEAR(event_date) = YEAR(CURDATE())
            ''', (session['user_id'],))
            
            stats_result = cursor.fetchone()
            if stats_result:
                stats = dict(stats_result)
            else:
                stats = {
                    'assignments': 0,
                    'exams': 0,
                    'holidays': 0,
                    'other': 0,
                    'total_events': 0
                }
        except:
            stats = {
                'assignments': 0,
                'exams': 0,
                'holidays': 0,
                'other': 0,
                'total_events': 0
            }
        
        cursor.close()
        
        current_datetime = datetime.now()  # Use datetime.now() not datetime.datetime.now()
        
        return render_template("calendar.html",
                             courses=courses,
                             upcoming_events=upcoming_events,
                             stats=stats,
                             current_datetime=current_datetime)
                             
    except Exception as e:
        print(f"Error loading calendar: {e}")
        import traceback
        traceback.print_exc()
        
        # Return minimal data on error
        current_datetime = datetime.now()
        cursor.close()
        
        return render_template("calendar.html",
                             courses=[],
                             upcoming_events=[],
                             stats={
                                 'assignments': 0,
                                 'exams': 0,
                                 'holidays': 0,
                                 'other': 0,
                                 'total_events': 0
                             },
                             current_datetime=current_datetime)

# ==================== DISCUSSION FORUMS ====================

# ==================== RESOURCES/STUDY MATERIALS ====================

@app.route("/resources", methods=['GET', 'POST'])
@login_required
def resources():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST' and session['role'] in ['admin', 'teacher']:
        title = request.form.get('title')
        description = request.form.get('description')
        course_id = request.form.get('course_id')
        resource_type = request.form.get('resource_type')
        file_url = request.form.get('file_url')
        external_url = request.form.get('external_url')
        
        cursor.execute('''
            INSERT INTO sms_resources 
            (title, description, course_id, resource_type, file_url, external_url, uploaded_by, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ''', (title, description, course_id, resource_type, file_url, external_url, session['userid']))
        mysql.connection.commit()
        
        flash('Resource uploaded successfully!', 'success')
        return redirect(url_for('resources'))
    
    # Get resources based on role
    if session['role'] == 'student':
        cursor.execute('''
            SELECT r.*, c.course_name, u.first_name as uploader_name
            FROM sms_resources r
            JOIN sms_courses c ON r.course_id = c.course_id
            JOIN sms_user u ON r.uploaded_by = u.id
            WHERE c.course_id IN (
                SELECT course_id FROM sms_course_enrollments 
                WHERE student_id = %s
            )
            ORDER BY r.uploaded_at DESC
        ''', (session['userid'],))
    elif session['role'] == 'teacher':
        cursor.execute('''
            SELECT r.*, c.course_name, u.first_name as uploader_name
            FROM sms_resources r
            JOIN sms_courses c ON r.course_id = c.course_id
            JOIN sms_user u ON r.uploaded_by = u.id
            WHERE r.uploaded_by = %s OR c.teacher_id = %s
            ORDER BY r.uploaded_at DESC
        ''', (session['userid'], session['userid']))
    else:  # Admin
        cursor.execute('''
            SELECT r.*, c.course_name, u.first_name as uploader_name
            FROM sms_resources r
            JOIN sms_courses c ON r.course_id = c.course_id
            JOIN sms_user u ON r.uploaded_by = u.id
            ORDER BY r.uploaded_at DESC
        ''')
    
    resources_list = cursor.fetchall()
    
    # Get courses for dropdown
    if session['role'] == 'teacher':
        cursor.execute('SELECT course_id, course_name FROM sms_courses WHERE teacher_id = %s', (session['userid'],))
    elif session['role'] == 'student':
        cursor.execute('''
            SELECT c.course_id, c.course_name 
            FROM sms_courses c
            JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
            WHERE ce.student_id = %s
        ''', (session['userid'],))
    else:
        cursor.execute('SELECT course_id, course_name FROM sms_courses')
    
    courses = cursor.fetchall()
    
    return render_template("resources.html", 
                          resources=resources_list, 
                          courses=courses)

# ==================== ADDITIONAL ROUTES NEEDED ====================

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        print(f"DEBUG: No user_id in session. Session: {dict(session)}")
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    try:
        # First, let's check if the messages table has the right structure
        cursor.execute("SHOW COLUMNS FROM messages")
        columns = [col[0] for col in cursor.fetchall()]
        print(f"DEBUG: Messages table columns: {columns}")
        
        # Determine the correct column name for message content
        content_column = 'content' if 'content' in columns else 'message'
        content_column = 'message_text' if 'message_text' in columns else content_column
        
        cursor.execute(f'''
            SELECT 
                m.id,
                m.sender_id,
                m.receiver_id,
                m.{content_column} as content,
                m.timestamp,
                m.status,
                u1.username as sender_name,
                u2.username as receiver_name
            FROM messages m
            LEFT JOIN users u1 ON m.sender_id = u1.id
            LEFT JOIN users u2 ON m.receiver_id = u2.id
            WHERE m.receiver_id = %s OR m.sender_id = %s
            ORDER BY m.timestamp DESC
        ''', (session['user_id'], session['user_id']))
        
        messages_list = cursor.fetchall()
        
        # Get users for messaging
        cursor.execute('SELECT id, username, role FROM users WHERE id != %s', (session['user_id'],))
        users = cursor.fetchall()
        
        cursor.close()
        
        print(f"DEBUG: User {session['user_id']} loaded {len(messages_list)} messages")
        
        return render_template("messages.html", 
                             messages=messages_list, 
                             users=users,
                             user_id=session['user_id'])
                             
    except Exception as e:
        print(f"Error in messages route: {e}")
        if cursor:
            cursor.close()
        return render_template("messages.html", 
                             messages=[], 
                             users=[],
                             user_id=session['user_id'])
    
@app.route("/send_message", methods=['POST'])
@login_required
def send_message():
    receiver_id = request.form.get('receiver_id')
    content = request.form.get('content')
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        INSERT INTO sms_messages (sender_id, receiver_id, content, created_at)
        VALUES (%s, %s, %s, NOW())
    ''', (session['userid'], receiver_id, content))
    mysql.connection.commit()
    
    flash('Message sent!', 'success')
    return redirect(url_for('messages', conversation_id=receiver_id))

# Add this route for class attendance
@app.route("/class_attendance/<int:class_id>")
@teacher_required
def class_attendance(class_id):
    """View attendance for a specific class"""
    return redirect(url_for('view_attendance', class_id=class_id))

# Update the teacher_profile route to handle POST requests
@app.route("/teacher_profile", methods=['GET', 'POST'])
@teacher_required
def teacher_profile():
    """Teacher profile - updated to handle form submission"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get teacher details
    cursor.execute('SELECT * FROM sms_teacher WHERE teacher_id = %s', (session['userid'],))
    teacher = cursor.fetchone()
    
    if not teacher:
        flash('Teacher not found!', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        qualification = request.form.get('qualification')
        experience = request.form.get('experience')
        bio = request.form.get('bio')
        new_password = request.form.get('new_password')
        
        # Update teacher table
        cursor.execute('''
            UPDATE sms_teacher 
            SET email = %s, mobile = %s, qualification = %s, experience = %s, bio = %s
            WHERE teacher_id = %s
        ''', (email, mobile, qualification, experience, bio, session['userid']))
        
        # Update user table
        if new_password:
            cursor.execute('UPDATE sms_user SET password = %s WHERE id = %s', (new_password, session['userid']))
        
        if email:
            cursor.execute('UPDATE sms_user SET email = %s WHERE id = %s', (email, session['userid']))
        
        mysql.connection.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('teacher_profile'))
    
    return render_template("teacher_profile.html", teacher=teacher)

@app.route("/notifications", methods=['GET'])
@login_required
def notifications():
    """Notifications page"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get notifications - FIXED: Remove reference to n.type or use correct column
    cursor.execute('''
        SELECT n.*,
               CASE 
                   WHEN n.notification_type = 'assignment' THEN 'fas fa-file-alt'
                   WHEN n.notification_type = 'quiz' THEN 'fas fa-question-circle'
                   WHEN n.notification_type = 'announcement' THEN 'fas fa-bullhorn'
                   WHEN n.notification_type = 'grade' THEN 'fas fa-chart-line'
                   ELSE 'fas fa-bell'
               END as icon
        FROM sms_notifications n
        WHERE n.user_id = %s
        ORDER BY n.created_at DESC
        LIMIT 20
    ''', (session['userid'],))
    notifications_list = cursor.fetchall()
    
    # Mark as read if requested
    if request.args.get('mark_read'):
        notification_id = request.args.get('mark_read')
        cursor.execute('UPDATE sms_notifications SET is_read = 1 WHERE notification_id = %s', (notification_id,))
        mysql.connection.commit()
        return redirect(url_for('notifications'))
    
    if request.args.get('mark_all_read'):
        cursor.execute('UPDATE sms_notifications SET is_read = 1 WHERE user_id = %s', (session['userid'],))
        mysql.connection.commit()
        return redirect(url_for('notifications'))
    
    return render_template("notifications.html", notifications=notifications_list)

# ==================== API ENDPOINTS ====================

@app.route("/api/notifications/count", methods=['GET'])
@login_required
def api_notification_count():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT COUNT(*) as count FROM sms_notifications WHERE user_id = %s AND is_read = 0', (session['userid'],))
    result = cursor.fetchone()
    return jsonify({'count': result['count']}) if result else jsonify({'count': 0})

@app.route('/api/calendar_events')
def api_calendar_events():
    if 'user_id' not in session:
        return jsonify([])
    
    try:
        cursor = mysql.connection.cursor()
        
        # Simplified query without sms_student_courses
        cursor.execute('''
            SELECT 
                e.id,
                e.title,
                e.description,
                e.event_type,
                e.event_date,
                e.event_time,
                e.priority,
                c.course_name
            FROM sms_calendar_events e
            LEFT JOIN sms_courses c ON e.course_id = c.course_id
            WHERE e.user_id = %s OR e.course_id IS NULL
            AND e.event_date >= CURDATE()
            ORDER BY e.event_date, e.event_time
        ''', (session['user_id'],))
        
        events = cursor.fetchall()
        cursor.close()
        
        # Format events for calendar
        formatted_events = []
        for event in events:
            event_dict = dict(event)
            
            # Determine color based on event type
            color_map = {
                'assignment': 'bg-blue-500',
                'exam': 'bg-red-500',
                'holiday': 'bg-green-500',
                'meeting': 'bg-purple-500',
                'deadline': 'bg-orange-500',
                'other': 'bg-gray-500'
            }
            
            # Format date and time
            event_date = event_dict['event_date']
            event_time = event_dict['event_time']
            
            start_str = str(event_date)
            if event_time:
                start_str += f"T{event_time}"
            
            formatted_events.append({
                'id': event_dict['id'],
                'title': event_dict['title'],
                'start': start_str,
                'color': color_map.get(event_dict['event_type'], 'bg-blue-500'),
                'extendedProps': {
                    'type': event_dict['event_type'],
                    'course': event_dict['course_name'],
                    'priority': event_dict['priority']
                }
            })
        
        return jsonify(formatted_events)
        
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        return jsonify([])

@app.route('/delete_calendar_event/<int:event_id>', methods=['DELETE'])
def delete_calendar_event(event_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        cursor = mysql.connection.cursor()
        
        # Check if user owns the event
        cursor.execute('SELECT user_id FROM sms_calendar_events WHERE id = %s', (event_id,))
        event = cursor.fetchone()
        
        if not event:
            cursor.close()
            return jsonify({'success': False, 'message': 'Event not found'})
        
        # Only allow deletion if user owns the event or is admin
        if event['user_id'] != session['user_id'] and session['role'] != 'admin':
            cursor.close()
            return jsonify({'success': False, 'message': 'Not authorized'})
        
        # Delete the event
        cursor.execute('DELETE FROM sms_calendar_events WHERE id = %s', (event_id,))
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'message': 'Event deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting calendar event: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# ==================== COMPLETE MISSING ROUTES ====================

@app.route("/progress")
@login_required
def progress():
    """Student progress tracking"""
    if session.get('type') != 'student':
        flash('Access denied. Student privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    student_id = session.get('student_id')
    
    if not student_id:
        cursor.execute('SELECT id FROM sms_students WHERE user_id = %s', (session['userid'],))
        student = cursor.fetchone()
        if student:
            student_id = student['id']
        else:
            flash('Student information not found!', 'error')
            return redirect(url_for('dashboard'))
    
    # Get course progress
    cursor.execute('''
        SELECT 
            c.course_name,
            COUNT(DISTINCT a.assignment_id) as total_assignments,
            COUNT(DISTINCT CASE WHEN sub.marks_obtained IS NOT NULL THEN a.assignment_id END) as completed_assignments,
            ROUND(AVG(sub.marks_obtained), 2) as avg_score,
            COUNT(DISTINCT CASE WHEN sub.marks_obtained >= a.max_marks * 0.7 THEN a.assignment_id END) as passed_assignments
        FROM sms_course_enrollments ce
        JOIN sms_courses c ON ce.course_id = c.course_id
        LEFT JOIN sms_assignments a ON c.course_id = a.course_id
        LEFT JOIN sms_assignment_submissions sub ON a.assignment_id = sub.assignment_id AND sub.student_id = %s
        WHERE ce.student_id = %s
        GROUP BY c.course_id, c.course_name
    ''', (student_id, student_id))
    
    course_progress = cursor.fetchall()
    
    # Get attendance summary - FIXED: Escape % signs by doubling them
    cursor.execute('''
        SELECT 
            DATE_FORMAT(attendance_date, '%%Y-%%m') as month,
            COUNT(CASE WHEN attendance_status = "present" THEN 1 END) as present_days,
            COUNT(*) as total_days,
            ROUND(COUNT(CASE WHEN attendance_status = "present" THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) as percentage
        FROM sms_attendance 
        WHERE student_id = %s 
        GROUP BY DATE_FORMAT(attendance_date, '%%Y-%%m')
        ORDER BY month DESC
        LIMIT 6
    ''', (student_id,))
    
    attendance_history = cursor.fetchall()
    
    # Get overall stats
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT ce.course_id) as total_courses,
            COUNT(DISTINCT a.assignment_id) as total_assignments,
            COUNT(DISTINCT sub.assignment_id) as submitted_assignments,
            ROUND(AVG(sub.marks_obtained), 2) as overall_avg
        FROM sms_course_enrollments ce
        LEFT JOIN sms_assignments a ON ce.course_id = a.course_id
        LEFT JOIN sms_assignment_submissions sub ON a.assignment_id = sub.assignment_id AND sub.student_id = %s
        WHERE ce.student_id = %s
    ''', (student_id, student_id))
    
    overall_stats = cursor.fetchone()
    
    return render_template("progress.html", 
                         course_progress=course_progress,
                         attendance_history=attendance_history,
                         overall_stats=overall_stats)
    
@app.route("/create_assignment", methods=['GET', 'POST'])
@teacher_required
def create_assignment():
    """Create new assignment"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        course_id = request.form.get('course_id')
        due_date = request.form.get('due_date')
        max_marks = request.form.get('max_marks', 100)
        weightage = request.form.get('weightage', 10)
        assignment_type = request.form.get('assignment_type', 'individual')
        instructions = request.form.get('instructions')
        
        # Handle file upload
        file = request.files.get('attachment')
        attachment_path = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            attachment_path = filename
        
        cursor.execute('''
            INSERT INTO sms_assignments 
            (title, description, course_id, due_date, max_marks, weightage, 
             assignment_type, instructions, attachment_path, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (title, description, course_id, due_date, max_marks, weightage,
              assignment_type, instructions, attachment_path, session['userid']))
        
        mysql.connection.commit()
        flash('Assignment created successfully!', 'success')
        return redirect(url_for('assignments'))
    
    # Get teacher's courses
    cursor.execute('''
        SELECT c.course_id, c.course_name, c.course_code
        FROM sms_courses c
        WHERE c.teacher_id = %s AND c.status = 'active'
        ORDER BY c.course_name
    ''', (session.get('teacher_id'),))
    
    courses = cursor.fetchall()
    
    return render_template("create_assignment.html", courses=courses)

@app.route("/users")
@admin_required
def users():
    """User management"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get all users with their roles
    cursor.execute('''
        SELECT u.*, 
               t.teacher_id,
               s.id as student_id,
               s.admission_no,
               s.name as student_name
        FROM sms_user u
        LEFT JOIN sms_teacher t ON u.id = t.user_id
        LEFT JOIN sms_students s ON u.id = s.user_id
        WHERE u.status != 'deleted'
        ORDER BY u.type, u.created_at DESC
    ''')
    
    users_list = cursor.fetchall()
    
    return render_template("users.html", users=users_list)

@app.route("/add_user", methods=['GET', 'POST'])
@admin_required
def add_user():
    """Add new user"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('type')
        status = request.form.get('status', 'active')
        
        # Check if email exists
        cursor.execute('SELECT id FROM sms_user WHERE email = %s', (email,))
        if cursor.fetchone():
            flash('Email already exists!', 'error')
            return redirect(url_for('add_user'))
        
        cursor.execute('''
            INSERT INTO sms_user 
            (first_name, last_name, email, password, type, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (first_name, last_name, email, password, user_type, status))
        
        user_id = cursor.lastrowid
        
        # Create related records based on type
        if user_type == 'teacher':
            cursor.execute('''
                INSERT INTO sms_teacher (teacher, user_id)
                VALUES (%s, %s)
            ''', (f"{first_name} {last_name}", user_id))
        elif user_type == 'student':
            # Generate admission number
            admission_no = f"STU{datetime.now().strftime('%Y%m')}{user_id:03d}"
            cursor.execute('''
                INSERT INTO sms_students 
                (name, email, admission_no, roll_no, user_id, admission_date, academic_year)
                VALUES (%s, %s, %s, %s, %s, CURDATE(), YEAR(CURDATE()))
            ''', (f"{first_name} {last_name}", email, admission_no, user_id, user_id))
        
        mysql.connection.commit()
        flash('User added successfully!', 'success')
        return redirect(url_for('users'))
    
    return render_template("add_user.html")

@app.route("/edit_user/<int:user_id>", methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        user_type = request.form.get('type')
        status = request.form.get('status')
        password = request.form.get('password')
        
        update_query = '''
            UPDATE sms_user 
            SET first_name = %s, last_name = %s, email = %s, type = %s, status = %s
        '''
        params = [first_name, last_name, email, user_type, status]
        
        if password:
            update_query = update_query.replace('status = %s', 'status = %s, password = %s')
            params.append(password)
        
        params.append(user_id)
        update_query += ' WHERE id = %s'
        
        cursor.execute(update_query, tuple(params))
        mysql.connection.commit()
        
        flash('User updated successfully!', 'success')
        return redirect(url_for('users'))
    
    # Get user details
    cursor.execute('SELECT * FROM sms_user WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    
    return render_template("edit_user.html", user=user)

@app.route("/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):
    """Soft delete user"""
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE sms_user SET status = "deleted" WHERE id = %s', (user_id,))
    mysql.connection.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('users'))

@app.route("/analytics")
@admin_required
def analytics():
    """Analytics dashboard"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Basic stats
    cursor.execute('SELECT COUNT(*) as count FROM sms_students')
    total_students = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM sms_teacher')
    total_teachers = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM sms_classes')
    total_classes = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM sms_courses')
    total_courses = cursor.fetchone()['count']
    
    # Attendance rate
    cursor.execute('''
        SELECT ROUND(AVG(CASE WHEN attendance_status = 'present' THEN 1 ELSE 0 END) * 100, 1) as rate
        FROM sms_attendance 
        WHERE attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    ''')
    attendance_rate = cursor.fetchone()['rate'] or 0
    
    # Course enrollments
    cursor.execute('''
        SELECT c.course_name, COUNT(ce.student_id) as enrolled
        FROM sms_courses c
        LEFT JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
        GROUP BY c.course_id
        ORDER BY enrolled DESC
        LIMIT 5
    ''')
    course_enrollments = cursor.fetchall()
    
    # Assignment submissions
    cursor.execute('''
        SELECT 
            DATE(submission_date) as date,
            COUNT(*) as submissions
        FROM sms_assignment_submissions
        WHERE submission_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY DATE(submission_date)
        ORDER BY date
    ''')
    submission_trends = cursor.fetchall()
    
    # Recent activities
    cursor.execute('''
        (SELECT 'user' as type, CONCAT('New ', type, ' registered') as title, created_at as time
         FROM sms_user ORDER BY created_at DESC LIMIT 2)
        UNION
        (SELECT 'assignment' as type, 'New assignment posted' as title, created_at as time
         FROM sms_assignments ORDER BY created_at DESC LIMIT 2)
        UNION
        (SELECT 'submission' as type, 'Assignment submitted' as title, submission_date as time
         FROM sms_assignment_submissions ORDER BY submission_date DESC LIMIT 1)
        ORDER BY time DESC LIMIT 5
    ''')
    recent_activities = cursor.fetchall()
    
    return render_template("analytics.html",
                         total_students=total_students,
                         total_teachers=total_teachers,
                         total_classes=total_classes,
                         total_courses=total_courses,
                         attendance_rate=attendance_rate,
                         course_enrollments=course_enrollments,
                         submission_trends=submission_trends,
                         recent_activities=recent_activities)

@app.route("/settings", methods=['GET', 'POST'])
@login_required
def settings():
    """User settings"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            mobile = request.form.get('mobile')
            
            cursor.execute('''
                UPDATE sms_user 
                SET first_name = %s, last_name = %s, email = %s, mobile = %s
                WHERE id = %s
            ''', (first_name, last_name, email, mobile, session['userid']))
            
            # Update session
            session['name'] = f"{first_name} {last_name}"
            session['email'] = email
            
            flash('Profile updated successfully!', 'success')
        
        elif action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # Verify current password
            cursor.execute('SELECT password FROM sms_user WHERE id = %s', (session['userid'],))
            user = cursor.fetchone()
            
            if user['password'] != current_password:
                flash('Current password is incorrect!', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match!', 'error')
            else:
                cursor.execute('UPDATE sms_user SET password = %s WHERE id = %s', (new_password, session['userid']))
                flash('Password changed successfully!', 'success')
        
        mysql.connection.commit()
        return redirect(url_for('settings'))
    
    # Get user details
    cursor.execute('SELECT * FROM sms_user WHERE id = %s', (session['userid'],))
    user = cursor.fetchone()
    
    return render_template("settings.html", user=user)

@app.route("/reports")
@login_required
def reports():
    """Reports page"""
    user_type = session.get('type')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if user_type == 'admin':
        # Admin reports
        cursor.execute('SELECT * FROM sms_classes')
        classes = cursor.fetchall()
        
        cursor.execute('''
            SELECT c.name as class_name, 
                   COUNT(s.id) as student_count,
                   ROUND(AVG(CASE WHEN a.attendance_status = 'present' THEN 1 ELSE 0 END) * 100, 1) as attendance_rate
            FROM sms_classes c
            LEFT JOIN sms_students s ON c.id = s.class
            LEFT JOIN sms_attendance a ON s.id = a.student_id AND a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY c.id
        ''')
        class_reports = cursor.fetchall()
        
        return render_template("admin_reports.html", classes=classes, class_reports=class_reports)
    
    elif user_type == 'teacher':
        # Teacher reports
        cursor.execute('''
            SELECT c.course_name, 
                   COUNT(DISTINCT ce.student_id) as enrolled_students,
                   COUNT(DISTINCT a.assignment_id) as total_assignments,
                   ROUND(AVG(sub.marks_obtained), 2) as avg_score
            FROM sms_courses c
            LEFT JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
            LEFT JOIN sms_assignments a ON c.course_id = a.course_id
            LEFT JOIN sms_assignment_submissions sub ON a.assignment_id = sub.assignment_id
            WHERE c.teacher_id = %s
            GROUP BY c.course_id
        ''', (session.get('teacher_id'),))
        
        course_reports = cursor.fetchall()
        
        return render_template("teacher_reports.html", course_reports=course_reports)
    
    else:
        # Student reports
        student_id = session.get('student_id')
        if not student_id:
            cursor.execute('SELECT id FROM sms_students WHERE user_id = %s', (session['userid'],))
            student = cursor.fetchone()
            if student:
                student_id = student['id']
            else:
                return redirect(url_for('dashboard'))
        
        # Get performance report
        cursor.execute('''
            SELECT c.course_name,
                   a.title as assignment_title,
                   sub.marks_obtained,
                   a.max_marks,
                   ROUND((sub.marks_obtained / a.max_marks) * 100, 2) as percentage,
                   sub.feedback,
                   sub.submission_date
            FROM sms_assignment_submissions sub
            JOIN sms_assignments a ON sub.assignment_id = a.assignment_id
            JOIN sms_courses c ON a.course_id = c.course_id
            WHERE sub.student_id = %s AND sub.marks_obtained IS NOT NULL
            ORDER BY sub.submission_date DESC
        ''', (student_id,))
        
        performance_report = cursor.fetchall()
        
        return render_template("student_reports.html", performance_report=performance_report)

@app.route("/calendar_events")
@login_required
def calendar_events():
    """Get events for calendar (JSON API)"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    start = request.args.get('start', datetime.now().strftime('%Y-%m-01'))
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    
    user_type = session.get('type')
    
    if user_type == 'student':
        cursor.execute('''
            SELECT e.*, c.course_name,
                   CASE 
                       WHEN e.event_type = 'exam' THEN '#dc2626'
                       WHEN e.event_type = 'assignment' THEN '#2563eb'
                       WHEN e.event_type = 'holiday' THEN '#16a34a'
                       ELSE '#7c3aed'
                   END as color
            FROM sms_events e
            LEFT JOIN sms_courses c ON e.course_id = c.course_id
            WHERE (e.course_id IN (
                    SELECT course_id FROM sms_course_enrollments 
                    WHERE student_id = %s
                ) OR e.course_id IS NULL)
                AND e.event_date BETWEEN %s AND %s
        ''', (session.get('student_id') or session['userid'], start, end))
    else:
        cursor.execute('''
            SELECT e.*, c.course_name,
                   CASE 
                       WHEN e.event_type = 'exam' THEN '#dc2626'
                       WHEN e.event_type = 'assignment' THEN '#2563eb'
                       WHEN e.event_type = 'holiday' THEN '#16a34a'
                       ELSE '#7c3aed'
                   END as color
            FROM sms_events e
            LEFT JOIN sms_courses c ON e.course_id = c.course_id
            WHERE e.event_date BETWEEN %s AND %s
        ''', (start, end))
    
    events = cursor.fetchall()
    
    calendar_events = []
    for event in events:
        start_str = str(event['event_date'])
        if event.get('event_time'):
            start_str = f"{start_str}T{event['event_time']}"
        
        calendar_events.append({
            'id': event['event_id'],
            'title': event['title'],
            'start': start_str,
            'color': event.get('color'),
            'description': event.get('description', ''),
            'extendedProps': {
                'course': event.get('course_name', ''),
                'type': event.get('event_type', ''),
                'location': event.get('location', '')
            }
        })
    
    return jsonify(calendar_events)

@app.route("/notifications/read/<int:notification_id>")
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE sms_notifications SET is_read = 1 WHERE notification_id = %s AND user_id = %s', 
                  (notification_id, session['userid']))
    mysql.connection.commit()
    return jsonify({'success': True})

@app.route("/notifications/read_all")
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE sms_notifications SET is_read = 1 WHERE user_id = %s', (session['userid'],))
    mysql.connection.commit()
    return jsonify({'success': True})

# ==================== ATTENDANCE ROUTES ====================

@app.route("/take_attendance", methods=['GET', 'POST'])
@teacher_required
def take_attendance():
    """Teacher take attendance for a class"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        class_id = request.form.get('class_id')
        attendance_date = request.form.get('attendance_date')
        
        if not class_id or not attendance_date:
            flash('Please select class and date!', 'error')
            return redirect(url_for('take_attendance'))
        
        # Get students in the class
        cursor.execute('''
            SELECT s.id, s.name, s.roll_no, s.admission_no
            FROM sms_students s
            WHERE s.class = %s
            ORDER BY s.roll_no
        ''', (class_id,))
        
        students = cursor.fetchall()
        
        # Check if attendance already taken for this date
        cursor.execute('''
            SELECT student_id FROM sms_attendance 
            WHERE class_id = %s AND attendance_date = %s LIMIT 1
        ''', (class_id, attendance_date))
        
        if cursor.fetchone():
            flash('Attendance already taken for this date!', 'warning')
        
        return render_template("take_attendance.html", 
                             students=students, 
                             class_id=class_id, 
                             attendance_date=attendance_date)
    
    # Get teacher's classes
    cursor.execute('''
        SELECT c.id, c.name, s.section
        FROM sms_classes c
        JOIN sms_section s ON c.section = s.section_id
        WHERE c.teacher_id = %s
        ORDER BY c.name
    ''', (session.get('teacher_id'),))
    
    classes = cursor.fetchall()
    
    return render_template("take_attendance_form.html", classes=classes)

@app.route("/save_attendance", methods=['POST'])
@teacher_required
def save_attendance():
    """Save attendance records"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    class_id = request.form.get('class_id')
    attendance_date = request.form.get('attendance_date')
    
    # Get all students in the class
    cursor.execute('SELECT id FROM sms_students WHERE class = %s', (class_id,))
    students = cursor.fetchall()
    
    attendance_saved = 0
    
    for student in students:
        student_id = student['id']
        attendance_status = request.form.get(f'attendance_{student_id}', 'absent')
        
        # Check if attendance already exists for this date
        cursor.execute('''
            SELECT attendance_id FROM sms_attendance 
            WHERE student_id = %s AND attendance_date = %s
        ''', (student_id, attendance_date))
        
        if cursor.fetchone():
            # Update existing attendance
            cursor.execute('''
                UPDATE sms_attendance 
                SET attendance_status = %s, recorded_by = %s
                WHERE student_id = %s AND attendance_date = %s
            ''', (attendance_status, session['userid'], student_id, attendance_date))
        else:
            # Insert new attendance
            cursor.execute('''
                INSERT INTO sms_attendance 
                (student_id, class_id, section_id, attendance_status, attendance_date, recorded_by)
                SELECT s.id, s.class, s.section, %s, %s, %s
                FROM sms_students s
                WHERE s.id = %s
            ''', (attendance_status, attendance_date, session['userid'], student_id))
        
        attendance_saved += 1
    
    mysql.connection.commit()
    flash(f'Attendance saved for {attendance_saved} students!', 'success')
    return redirect(url_for('take_attendance'))

@app.route("/view_attendance/<int:class_id>")
@login_required
def view_attendance(class_id):
    """View attendance for a specific class"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get class details
    cursor.execute('''
        SELECT c.*, s.section, t.teacher
        FROM sms_classes c
        JOIN sms_section s ON c.section = s.section_id
        LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
        WHERE c.id = %s
    ''', (class_id,))
    
    class_info = cursor.fetchone()
    
    if not class_info:
        flash('Class not found!', 'error')
        return redirect(url_for('attendance'))
    
    # Get attendance summary
    cursor.execute('''
        SELECT 
            a.attendance_date,
            COUNT(CASE WHEN a.attendance_status = 'present' THEN 1 END) as present_count,
            COUNT(*) as total_students,
            ROUND(COUNT(CASE WHEN a.attendance_status = 'present' THEN 1 END) * 100.0 / COUNT(*), 1) as percentage
        FROM sms_attendance a
        JOIN sms_students s ON a.student_id = s.id
        WHERE s.class = %s
        GROUP BY a.attendance_date
        ORDER BY a.attendance_date DESC
        LIMIT 30
    ''', (class_id,))
    
    attendance_summary = cursor.fetchall()
    
    # Get today's attendance
    cursor.execute('''
        SELECT s.name, s.roll_no, a.attendance_status, a.remarks
        FROM sms_students s
        LEFT JOIN sms_attendance a ON s.id = a.student_id AND a.attendance_date = CURDATE()
        WHERE s.class = %s
        ORDER BY s.roll_no
    ''', (class_id,))
    
    todays_attendance = cursor.fetchall()
    
    user_type = session.get('type')
    if user_type == 'teacher':
        template = "teacher_view_attendance.html"
    elif user_type == 'admin':
        template = "admin_view_attendance.html"
    else:
        template = "view_attendance.html"
    
    return render_template(template,
                         class_info=class_info,
                         attendance_summary=attendance_summary,
                         todays_attendance=todays_attendance)

# ==================== OTHER MISSING ROUTES ====================

@app.route("/grade_assignment/<int:assignment_id>", methods=['GET', 'POST'])
@teacher_required
def grade_assignment(assignment_id):
    """Grade student assignments"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get assignment details
    cursor.execute('''
        SELECT a.*, c.course_name, c.course_code
        FROM sms_assignments a
        JOIN sms_courses c ON a.course_id = c.course_id
        WHERE a.assignment_id = %s
    ''', (assignment_id,))
    
    assignment = cursor.fetchone()
    
    if not assignment:
        flash('Assignment not found!', 'error')
        return redirect(url_for('assignments'))
    
    # Get submissions
    cursor.execute('''
        SELECT s.*, st.name, st.admission_no, st.roll_no
        FROM sms_assignment_submissions s
        JOIN sms_students st ON s.student_id = st.id
        WHERE s.assignment_id = %s
        ORDER BY s.submission_date
    ''', (assignment_id,))
    
    submissions = cursor.fetchall()
    
    if request.method == 'POST':
        for submission in submissions:
            marks_obtained = request.form.get(f'marks_{submission["submission_id"]}')
            feedback = request.form.get(f'feedback_{submission["submission_id"]}')
            
            if marks_obtained is not None:
                cursor.execute('''
                    UPDATE sms_assignment_submissions 
                    SET marks_obtained = %s, feedback = %s, graded_by = %s, graded_at = NOW()
                    WHERE submission_id = %s
                ''', (marks_obtained, feedback, session['userid'], submission['submission_id']))
        
        mysql.connection.commit()
        flash('Grades updated successfully!', 'success')
        return redirect(url_for('grade_assignment', assignment_id=assignment_id))
    
    return render_template("grade_assignment.html",
                         assignment=assignment,
                         submissions=submissions)

@app.route("/download_file/<filename>")
@login_required
def download_file(filename):
    """Download uploaded files"""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('File not found!', 'error')
        return redirect(request.referrer or url_for('dashboard'))

@app.route("/enroll_course/<int:course_id>")
@student_required
def enroll_course(course_id):
    """Student enroll in a course"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get student ID
    student_id = session.get('student_id')
    if not student_id:
        cursor.execute('SELECT id FROM sms_students WHERE user_id = %s', (session['userid'],))
        student = cursor.fetchone()
        if student:
            student_id = student['id']
        else:
            flash('Student information not found!', 'error')
            return redirect(url_for('courses'))
    
    # Check if already enrolled
    cursor.execute('''
        SELECT enrollment_id FROM sms_course_enrollments 
        WHERE student_id = %s AND course_id = %s
    ''', (student_id, course_id))
    
    if cursor.fetchone():
        flash('You are already enrolled in this course!', 'warning')
        return redirect(url_for('courses'))
    
    # Enroll in course
    cursor.execute('''
        INSERT INTO sms_course_enrollments (student_id, course_id, enrolled_at)
        VALUES (%s, %s, NOW())
    ''', (student_id, course_id))
    
    mysql.connection.commit()
    flash('Successfully enrolled in the course!', 'success')
    return redirect(url_for('courses'))

@app.route("/unenroll_course/<int:course_id>")
@student_required
def unenroll_course(course_id):
    """Student unenroll from a course"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    student_id = session.get('student_id')
    if not student_id:
        cursor.execute('SELECT id FROM sms_students WHERE user_id = %s', (session['userid'],))
        student = cursor.fetchone()
        if student:
            student_id = student['id']
    
    if student_id:
        cursor.execute('''
            DELETE FROM sms_course_enrollments 
            WHERE student_id = %s AND course_id = %s
        ''', (student_id, course_id))
        mysql.connection.commit()
        flash('Successfully unenrolled from the course!', 'success')
    
    return redirect(url_for('courses'))

@app.route("/upload_material/<int:course_id>", methods=['GET', 'POST'])
@teacher_required
def upload_material(course_id):
    """Teacher upload course material"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get course details
    cursor.execute('SELECT * FROM sms_courses WHERE course_id = %s', (course_id,))
    course = cursor.fetchone()
    
    if not course:
        flash('Course not found!', 'error')
        return redirect(url_for('courses'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        material_type = request.form.get('material_type', 'lecture')
        week_number = request.form.get('week_number')
        topic = request.form.get('topic')
        
        # Handle file upload
        file = request.files.get('file')
        file_path = None
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            file_path = filename
        
        cursor.execute('''
            INSERT INTO sms_course_materials 
            (course_id, title, description, material_type, file_path, week_number, topic, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (course_id, title, description, material_type, file_path, week_number, topic, session['userid']))
        
        mysql.connection.commit()
        flash('Material uploaded successfully!', 'success')
        return redirect(url_for('course_details', course_id=course_id))
    
    return render_template("upload_material.html", course=course)

# ==================== QUICK ROUTES FOR TEMPLATE REFERENCES ====================

@app.route("/my_courses")
@student_required
def my_courses():
    """Student's enrolled courses"""
    return redirect(url_for('courses'))

@app.route("/course_materials")
@login_required
def course_materials():
    """Course materials page"""
    return redirect(url_for('courses'))

@app.route("/grades")
@login_required
def grades():
    """Grades page - redirect based on role"""
    if session.get('type') == 'teacher':
        return redirect(url_for('gradebook'))
    else:
        return redirect(url_for('gradebook'))

@app.route("/schedule")
@login_required
def schedule():
    """Class schedule"""
    return redirect(url_for('calendar'))

@app.route("/profile")
@login_required
def profile():
    """User profile"""
    user_type = session.get('type')
    if user_type == 'student':
        return redirect(url_for('student_profile'))
    elif user_type == 'teacher':
        return redirect(url_for('teacher_profile'))
    else:
        return redirect(url_for('settings'))

# ==================== CLASS MANAGEMENT ROUTES ====================

@app.route("/class_students/<int:class_id>")
@login_required
def class_students(class_id):
    """View all students in a specific class"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get class details
    cursor.execute('''
        SELECT c.*, s.section, t.teacher
        FROM sms_classes c
        LEFT JOIN sms_section s ON c.section = s.section_id
        LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
        WHERE c.id = %s
    ''', (class_id,))
    
    class_info = cursor.fetchone()
    
    if not class_info:
        flash('Class not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get students in the class
    cursor.execute('''
        SELECT s.*, 
               (SELECT COUNT(*) FROM sms_attendance a 
                WHERE a.student_id = s.id AND a.attendance_status = 'present' 
                AND a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)) as present_days,
               (SELECT COUNT(*) FROM sms_attendance a 
                WHERE a.student_id = s.id 
                AND a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)) as total_days
        FROM sms_students s
        WHERE s.class = %s
        ORDER BY s.roll_no
    ''', (class_id,))
    
    students = cursor.fetchall()
    
    # Calculate attendance percentage for each student
    for student in students:
        if student['total_days'] and student['total_days'] > 0:
            student['attendance_percentage'] = round((student['present_days'] / student['total_days']) * 100, 1)
        else:
            student['attendance_percentage'] = 0
    
    user_type = session.get('type')
    if user_type == 'admin':
        template = "admin_class_students.html"
    elif user_type == 'teacher':
        # Check if teacher teaches this class
        if class_info['teacher_id'] != session.get('teacher_id'):
            flash('You are not assigned to this class!', 'error')
            return redirect(url_for('dashboard'))
        template = "teacher_class_students.html"
    else:
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template(template,
                         class_info=class_info,
                         students=students)

@app.route("/class_details/<int:class_id>")
@login_required
def class_details(class_id):
    """View detailed information about a class"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get class details
    cursor.execute('''
        SELECT c.*, s.section, t.teacher, t.teacher_id,
               COUNT(st.id) as student_count
        FROM sms_classes c
        LEFT JOIN sms_section s ON c.section = s.section_id
        LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
        LEFT JOIN sms_students st ON c.id = st.class
        WHERE c.id = %s
        GROUP BY c.id
    ''', (class_id,))
    
    class_info = cursor.fetchone()
    
    if not class_info:
        flash('Class not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get class schedule (courses assigned to this class)
    cursor.execute('''
        SELECT cr.course_id, cr.course_name, cr.course_code, 
               t.teacher as course_teacher, cr.credit_hours
        FROM sms_courses cr
        LEFT JOIN sms_teacher t ON cr.teacher_id = t.teacher_id
        WHERE cr.class_id = %s AND cr.status = 'active'
        ORDER BY cr.course_name
    ''', (class_id,))
    
    courses = cursor.fetchall()
    
    # Get recent announcements for this class
    cursor.execute('''
        SELECT a.*, u.first_name as created_by_name
        FROM sms_announcements a
        JOIN sms_user u ON a.created_by = u.id
        WHERE a.class_id = %s OR (a.announcement_type = 'school' AND a.target_audience = 'all')
        ORDER BY a.created_at DESC
        LIMIT 5
    ''', (class_id,))
    
    announcements = cursor.fetchall()
    
    # Get upcoming events for this class
    cursor.execute('''
        SELECT e.*
        FROM sms_events e
        WHERE e.class_id = %s AND e.event_date >= CURDATE()
        ORDER BY e.event_date ASC
        LIMIT 5
    ''', (class_id,))
    
    events = cursor.fetchall()
    
    return render_template("class_details.html",
                         class_info=class_info,
                         courses=courses,
                         announcements=announcements,
                         events=events)

@app.route("/assign_teacher/<int:class_id>", methods=['GET', 'POST'])
@admin_required
def assign_teacher(class_id):
    """Assign teacher to a class"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get class details
    cursor.execute('SELECT * FROM sms_classes WHERE id = %s', (class_id,))
    class_info = cursor.fetchone()
    
    if not class_info:
        flash('Class not found!', 'error')
        return redirect(url_for('classes'))
    
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        
        cursor.execute('UPDATE sms_classes SET teacher_id = %s WHERE id = %s', 
                      (teacher_id, class_id))
        mysql.connection.commit()
        
        flash('Teacher assigned successfully!', 'success')
        return redirect(url_for('class_details', class_id=class_id))
    
    # Get all teachers for dropdown
    cursor.execute('SELECT teacher_id, teacher FROM sms_teacher ORDER BY teacher')
    teachers = cursor.fetchall()
    
    # Get current teacher if any
    current_teacher = None
    if class_info['teacher_id']:
        cursor.execute('SELECT teacher_id, teacher FROM sms_teacher WHERE teacher_id = %s', 
                      (class_info['teacher_id'],))
        current_teacher = cursor.fetchone()
    
    return render_template("assign_teacher.html",
                         class_info=class_info,
                         teachers=teachers,
                         current_teacher=current_teacher)

@app.route("/add_student_to_class/<int:class_id>", methods=['GET', 'POST'])
@admin_required
def add_student_to_class(class_id):
    """Add student to a class"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get class details
    cursor.execute('SELECT * FROM sms_classes WHERE id = %s', (class_id,))
    class_info = cursor.fetchone()
    
    if not class_info:
        flash('Class not found!', 'error')
        return redirect(url_for('classes'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        
        if student_id:
            cursor.execute('UPDATE sms_students SET class = %s WHERE id = %s', 
                          (class_id, student_id))
            mysql.connection.commit()
            flash('Student added to class successfully!', 'success')
        
        return redirect(url_for('class_students', class_id=class_id))
    
    # Get students not assigned to any class or in other classes
    cursor.execute('''
        SELECT s.id, s.name, s.admission_no, s.roll_no, c.name as current_class
        FROM sms_students s
        LEFT JOIN sms_classes c ON s.class = c.id
        WHERE s.class != %s OR s.class IS NULL
        ORDER BY s.name
    ''', (class_id,))
    
    students = cursor.fetchall()
    
    return render_template("add_student_to_class.html",
                         class_info=class_info,
                         students=students)

# ==================== OTHER POTENTIALLY MISSING ROUTES ====================

@app.route("/student_details/<int:student_id>")
@login_required
def student_details(student_id):
    """View detailed student information"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get student details
    cursor.execute('''
        SELECT s.*, c.name as class_name, sec.section, u.email as user_email
        FROM sms_students s
        LEFT JOIN sms_classes c ON s.class = c.id
        LEFT JOIN sms_section sec ON s.section = sec.section_id
        LEFT JOIN sms_user u ON s.user_id = u.id
        WHERE s.id = %s
    ''', (student_id,))
    
    student = cursor.fetchone()
    
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Check permissions
    user_type = session.get('type')
    if user_type == 'student' and session.get('student_id') != student_id:
        flash('Access denied!', 'error')
        return redirect(url_for('dashboard'))
    
    if user_type == 'teacher':
        # Check if student is in teacher's class
        cursor.execute('''
            SELECT c.id FROM sms_classes c
            JOIN sms_students s ON c.id = s.class
            WHERE s.id = %s AND c.teacher_id = %s
        ''', (student_id, session.get('teacher_id')))
        
        if not cursor.fetchone():
            flash('Student is not in your class!', 'error')
            return redirect(url_for('dashboard'))
    
    # Get student's courses
    cursor.execute('''
        SELECT c.course_name, c.course_code, t.teacher, ce.enrolled_at
        FROM sms_course_enrollments ce
        JOIN sms_courses c ON ce.course_id = c.course_id
        LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
        WHERE ce.student_id = %s AND ce.status = 'active'
        ORDER BY c.course_name
    ''', (student_id,))
    
    courses = cursor.fetchall()
    
    # Get recent attendance
    cursor.execute('''
        SELECT a.attendance_date, a.attendance_status, a.remarks
        FROM sms_attendance a
        WHERE a.student_id = %s
        ORDER BY a.attendance_date DESC
        LIMIT 10
    ''', (student_id,))
    
    attendance = cursor.fetchall()
    
    # Get recent assignments
    cursor.execute('''
        SELECT a.title, c.course_name, sub.marks_obtained, a.max_marks,
               sub.submission_date, sub.feedback
        FROM sms_assignment_submissions sub
        JOIN sms_assignments a ON sub.assignment_id = a.assignment_id
        JOIN sms_courses c ON a.course_id = c.course_id
        WHERE sub.student_id = %s
        ORDER BY sub.submission_date DESC
        LIMIT 5
    ''', (student_id,))
    
    assignments = cursor.fetchall()
    
    return render_template("student_details.html",
                         student=student,
                         courses=courses,
                         attendance=attendance,
                         assignments=assignments)

@app.route("/teacher_details/<int:teacher_id>")
@login_required
def teacher_details(teacher_id):
    """View detailed teacher information"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get teacher details
    cursor.execute('''
        SELECT t.*, s.subject, u.email, u.mobile as user_mobile
        FROM sms_teacher t
        LEFT JOIN sms_subjects s ON t.subject_id = s.subject_id
        LEFT JOIN sms_user u ON t.user_id = u.id
        WHERE t.teacher_id = %s
    ''', (teacher_id,))
    
    teacher = cursor.fetchone()
    
    if not teacher:
        flash('Teacher not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get teacher's classes
    cursor.execute('''
        SELECT c.*, s.section, COUNT(st.id) as student_count
        FROM sms_classes c
        LEFT JOIN sms_section s ON c.section = s.section_id
        LEFT JOIN sms_students st ON c.id = st.class
        WHERE c.teacher_id = %s
        GROUP BY c.id
        ORDER BY c.name
    ''', (teacher_id,))
    
    classes = cursor.fetchall()
    
    # Get teacher's courses
    cursor.execute('''
        SELECT c.*, COUNT(ce.student_id) as enrolled_students
        FROM sms_courses c
        LEFT JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
        WHERE c.teacher_id = %s
        GROUP BY c.course_id
        ORDER BY c.course_name
    ''', (teacher_id,))
    
    courses = cursor.fetchall()
    
    return render_template("teacher_details.html",
                         teacher=teacher,
                         classes=classes,
                         courses=courses)

@app.route("/course_enrollments/<int:course_id>")
@login_required
def course_enrollments(course_id):
    """View all students enrolled in a course"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get course details
    cursor.execute('''
        SELECT c.*, t.teacher
        FROM sms_courses c
        LEFT JOIN sms_teacher t ON c.teacher_id = t.teacher_id
        WHERE c.course_id = %s
    ''', (course_id,))
    
    course = cursor.fetchone()
    
    if not course:
        flash('Course not found!', 'error')
        return redirect(url_for('courses'))
    
    # Check permissions
    user_type = session.get('type')
    if user_type == 'teacher' and course['teacher_id'] != session.get('teacher_id'):
        flash('This is not your course!', 'error')
        return redirect(url_for('courses'))
    
    # Get enrolled students
    cursor.execute('''
        SELECT s.*, ce.enrolled_at, ce.status as enrollment_status
        FROM sms_course_enrollments ce
        JOIN sms_students s ON ce.student_id = s.id
        WHERE ce.course_id = %s
        ORDER BY s.name
    ''', (course_id,))
    
    enrolled_students = cursor.fetchall()
    
    # Get assignment submissions summary
    for student in enrolled_students:
        cursor.execute('''
            SELECT COUNT(DISTINCT a.assignment_id) as total_assignments,
                   COUNT(DISTINCT sub.assignment_id) as submitted_assignments,
                   ROUND(AVG(sub.marks_obtained), 2) as avg_score
            FROM sms_assignments a
            LEFT JOIN sms_assignment_submissions sub ON a.assignment_id = sub.assignment_id AND sub.student_id = %s
            WHERE a.course_id = %s
        ''', (student['id'], course_id))
        
        stats = cursor.fetchone()
        student['assignment_stats'] = stats
    
    return render_template("course_enrollments.html",
                         course=course,
                         enrolled_students=enrolled_students)

# ==================== GRADE SUBMISSION ROUTE ====================

@app.route("/grade_submission/<int:submission_id>", methods=['GET', 'POST'])
@teacher_required
def grade_submission(submission_id):
    """Grade individual assignment submission"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get submission details
    cursor.execute('''
        SELECT s.*, st.name as student_name, st.admission_no, st.roll_no,
               a.title as assignment_title, a.max_marks, a.assignment_id,
               c.course_name, c.course_code
        FROM sms_assignment_submissions s
        JOIN sms_students st ON s.student_id = st.id
        JOIN sms_assignments a ON s.assignment_id = a.assignment_id
        JOIN sms_courses c ON a.course_id = c.course_id
        WHERE s.submission_id = %s
    ''', (submission_id,))
    
    submission = cursor.fetchone()
    
    if not submission:
        flash('Submission not found!', 'error')
        return redirect(url_for('assignments'))
    
    # Check if teacher teaches this course
    cursor.execute('SELECT teacher_id FROM sms_courses WHERE course_id = %s', (submission['course_id'],))
    course = cursor.fetchone()
    
    if not course or course['teacher_id'] != session.get('teacher_id'):
        flash('You are not authorized to grade this submission!', 'error')
        return redirect(url_for('assignments'))
    
    if request.method == 'POST':
        marks_obtained = request.form.get('marks_obtained')
        feedback = request.form.get('feedback')
        
        if marks_obtained:
            try:
                marks = float(marks_obtained)
                if marks < 0 or marks > submission['max_marks']:
                    flash(f'Marks must be between 0 and {submission["max_marks"]}!', 'error')
                else:
                    cursor.execute('''
                        UPDATE sms_assignment_submissions 
                        SET marks_obtained = %s, feedback = %s, graded_by = %s, graded_at = NOW()
                        WHERE submission_id = %s
                    ''', (marks, feedback, session['userid'], submission_id))
                    
                    mysql.connection.commit()
                    flash('Submission graded successfully!', 'success')
                    return redirect(url_for('assignment_details', assignment_id=submission['assignment_id']))
            except ValueError:
                flash('Please enter a valid number for marks!', 'error')
        else:
            flash('Please enter marks!', 'error')
    
    return render_template("grade_submission.html", submission=submission)

# ==================== OTHER POTENTIALLY MISSING ROUTES ====================

@app.route("/delete_submission/<int:submission_id>")
@teacher_required
def delete_submission(submission_id):
    """Delete assignment submission (teacher only)"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get submission details to check permissions
    cursor.execute('''
        SELECT a.assignment_id, c.teacher_id
        FROM sms_assignment_submissions s
        JOIN sms_assignments a ON s.assignment_id = a.assignment_id
        JOIN sms_courses c ON a.course_id = c.course_id
        WHERE s.submission_id = %s
    ''', (submission_id,))
    
    submission = cursor.fetchone()
    
    if not submission:
        flash('Submission not found!', 'error')
        return redirect(url_for('assignments'))
    
    # Check if teacher teaches this course
    if submission['teacher_id'] != session.get('teacher_id'):
        flash('You are not authorized to delete this submission!', 'error')
        return redirect(url_for('assignments'))
    
    cursor.execute('DELETE FROM sms_assignment_submissions WHERE submission_id = %s', (submission_id,))
    mysql.connection.commit()
    
    flash('Submission deleted successfully!', 'success')
    return redirect(url_for('assignment_details', assignment_id=submission['assignment_id']))

@app.route("/delete_assignment/<int:assignment_id>")
@teacher_required
def delete_assignment(assignment_id):
    """Delete assignment"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Check if teacher created this assignment
    cursor.execute('SELECT created_by FROM sms_assignments WHERE assignment_id = %s', (assignment_id,))
    assignment = cursor.fetchone()
    
    if not assignment:
        flash('Assignment not found!', 'error')
        return redirect(url_for('assignments'))
    
    if assignment['created_by'] != session['userid'] and session.get('type') != 'administrator':
        flash('You are not authorized to delete this assignment!', 'error')
        return redirect(url_for('assignments'))
    
    cursor.execute('DELETE FROM sms_assignments WHERE assignment_id = %s', (assignment_id,))
    mysql.connection.commit()
    
    flash('Assignment deleted successfully!', 'success')
    return redirect(url_for('assignments'))

@app.route("/delete_course/<int:course_id>")
@admin_required
def delete_course(course_id):
    """Delete course (admin only)"""
    cursor = mysql.connection.cursor()
    
    cursor.execute('DELETE FROM sms_courses WHERE course_id = %s', (course_id,))
    mysql.connection.commit()
    
    flash('Course deleted successfully!', 'success')
    return redirect(url_for('courses'))

@app.route("/edit_assignment/<int:assignment_id>", methods=['GET', 'POST'])
@teacher_required
def edit_assignment(assignment_id):
    """Edit assignment"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get assignment details
    cursor.execute('''
        SELECT a.*, c.course_name, c.course_code
        FROM sms_assignments a
        JOIN sms_courses c ON a.course_id = c.course_id
        WHERE a.assignment_id = %s
    ''', (assignment_id,))
    
    assignment = cursor.fetchone()
    
    if not assignment:
        flash('Assignment not found!', 'error')
        return redirect(url_for('assignments'))
    
    # Check if teacher created this assignment
    if assignment['created_by'] != session['userid'] and session.get('type') != 'administrator':
        flash('You are not authorized to edit this assignment!', 'error')
        return redirect(url_for('assignments'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date = request.form.get('due_date')
        max_marks = request.form.get('max_marks')
        weightage = request.form.get('weightage')
        assignment_type = request.form.get('assignment_type')
        instructions = request.form.get('instructions')
        
        cursor.execute('''
            UPDATE sms_assignments 
            SET title = %s, description = %s, due_date = %s, max_marks = %s,
                weightage = %s, assignment_type = %s, instructions = %s
            WHERE assignment_id = %s
        ''', (title, description, due_date, max_marks, weightage, assignment_type, instructions, assignment_id))
        
        mysql.connection.commit()
        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('assignment_details', assignment_id=assignment_id))
    
    # Get teacher's courses for dropdown
    cursor.execute('SELECT course_id, course_name FROM sms_courses WHERE teacher_id = %s', (session.get('teacher_id'),))
    courses = cursor.fetchall()
    
    return render_template("edit_assignment.html", assignment=assignment, courses=courses)

@app.route("/edit_course/<int:course_id>", methods=['GET', 'POST'])
@admin_required
def edit_course(course_id):
    """Edit course (admin only)"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get course details
    cursor.execute('SELECT * FROM sms_courses WHERE course_id = %s', (course_id,))
    course = cursor.fetchone()
    
    if not course:
        flash('Course not found!', 'error')
        return redirect(url_for('courses'))
    
    if request.method == 'POST':
        course_name = request.form.get('course_name')
        course_code = request.form.get('course_code')
        description = request.form.get('description')
        teacher_id = request.form.get('teacher_id')
        credit_hours = request.form.get('credit_hours')
        semester = request.form.get('semester')
        status = request.form.get('status')
        
        cursor.execute('''
            UPDATE sms_courses 
            SET course_name = %s, course_code = %s, description = %s,
                teacher_id = %s, credit_hours = %s, semester = %s, status = %s
            WHERE course_id = %s
        ''', (course_name, course_code, description, teacher_id, credit_hours, semester, status, course_id))
        
        mysql.connection.commit()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('courses'))
    
    # Get teachers for dropdown
    cursor.execute('SELECT teacher_id, teacher FROM sms_teacher ORDER BY teacher')
    teachers = cursor.fetchall()
    
    return render_template("edit_course.html", course=course, teachers=teachers)

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page Not Found</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100 h-screen flex items-center justify-center">
        <div class="text-center">
            <h1 class="text-6xl font-bold text-gray-800 mb-4">404</h1>
            <p class="text-xl text-gray-600 mb-8">Page not found</p>
            <a href="{{ url_for('dashboard') }}" class="text-blue-600 hover:underline">
                Return to Dashboard
            </a>
        </div>
    </body>
    </html>
    ''', 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Server Error</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100 h-screen flex items-center justify-center">
        <div class="text-center">
            <h1 class="text-6xl font-bold text-red-800 mb-4">500</h1>
            <p class="text-xl text-gray-600 mb-8">Internal server error</p>
            <a href="{{ url_for('dashboard') }}" class="text-blue-600 hover:underline">
                Return to Dashboard
            </a>
        </div>
    </body>
    </html>
    ''', 500

def is_recent(date_string, days=7):
    """Check if a date is within the last N days"""
    if not date_string:
        return False
    try:
        # Parse the date string (adjust format if needed)
        date_obj = datetime.strptime(str(date_string), '%Y-%m-%d %H:%M:%S')
        cutoff_date = datetime.now() - timedelta(days=days)
        return date_obj > cutoff_date
    except:
        return False

app.jinja_env.tests['recent'] = is_recent
app.jinja_env.filters['time_ago'] = time_ago_filter

# ==================== MAIN ====================

if __name__ == "__main__":
    # Create an application context
    with app.app_context():
        # Create necessary tables if they don't exist
        cursor = mysql.connection.cursor()
        
        # ... existing table creation code ...
        
        # Create notifications table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sms_notifications (
                notification_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                title VARCHAR(255),
                content TEXT,
                notification_type VARCHAR(50),
                is_read BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES sms_user(id) ON DELETE CASCADE
            )
        ''')
        
        # Create messages table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sms_messages (
                message_id INT AUTO_INCREMENT PRIMARY KEY,
                sender_id INT,
                receiver_id INT,
                content TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES sms_user(id) ON DELETE CASCADE,
                FOREIGN KEY (receiver_id) REFERENCES sms_user(id) ON DELETE CASCADE
            )
        ''')
        
        # Create announcements table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sms_announcements (
                announcement_id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255),
                content TEXT,
                announcement_type VARCHAR(50) DEFAULT 'school',
                course_id INT,
                created_by INT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES sms_courses(course_id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES sms_user(id) ON DELETE CASCADE
            )
        ''')
        
        mysql.connection.commit()
    
    app.run(debug=True, host='0.0.0.0', port=5000)