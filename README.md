# School Management System (SMS) - Flask Application

## 📋 Project Overview

A comprehensive School Management System built with **Flask** that provides role-based access for **Administrators, Teachers, and Students**. The system includes features for attendance tracking, assignment management, course enrollment, gradebook, online classes, and more.

![Dashboard Preview](https://raw.githubusercontent.com/BawanthaBeliwaththa/School-Management-System/refs/heads/main/images/dashboard.png)

## 🚀 Features

### 👨‍🏫 **For Administrators**
- User management (Students, Teachers, Admins)
- Class and section management
- Subject management
- System analytics and reports
- Bulk data import/export via Excel

### 👩‍🏫 **For Teachers**
- Class attendance management
- Assignment creation and grading
- Course material upload
- Student progress tracking
- Online class scheduling

### 👨‍🎓 **For Students**
- Course enrollment
- Assignment submission
- Grade viewing
- Attendance tracking
- Profile management

## 🛠️ Technology Stack

- **Backend:** Python Flask
- **Database:** MySQL
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **File Upload:** PDF, DOC, XLSX, Images
- **Templates:** Jinja2 templating engine
- **Authentication:** Session-based with role-based access control

## 📦 Installation

### Prerequisites
- Python 3.8+
- MySQL 5.7+
- pip (Python package manager)

### Step 1: Clone the Repository
```bash
git clone https://github.com/bawanthabeliwaththa/school-management-system.git
cd school-management-system
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Database Setup

#### Create MySQL Database
```sql
CREATE DATABASE python_sms;
CREATE USER 'sms_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON python_sms.* TO 'sms_user'@'localhost';
FLUSH PRIVILEGES;
```

#### Update Database Configuration
Edit `app.py` with your MySQL credentials:
```python
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'your_username'
app.config['MYSQL_PASSWORD'] = 'your_password'
app.config['MYSQL_DB'] = 'python_sms'
```

### Step 5: Initialize Database
Run the application once to create tables automatically:
```bash
python app.py
```

### Step 6: Create Uploads Directory
```bash
mkdir uploads
```

## 🗄️ Database Schema

The system uses the following main tables:

- **sms_user** - User authentication and basic info
- **sms_students** - Student details
- **sms_teacher** - Teacher details
- **sms_classes** - Class information
- **sms_courses** - Course information
- **sms_assignments** - Assignment details
- **sms_attendance** - Attendance records
- **sms_course_enrollments** - Student course enrollments
- **sms_assignment_submissions** - Assignment submissions

![Database Schema](https://raw.githubusercontent.com/BawanthaBeliwaththa/School-Management-System/refs/heads/main/images/DB.png)

## 🔐 Default Login Credentials

After initial setup, create admin account:

```sql
-- Insert default admin user
INSERT INTO sms_user (email, password, first_name, last_name, type, status) 
VALUES ('admin@school.com', 'admin123', 'System', 'Admin', 'administrator', 'active');
```

**Default Logins:**
- **Admin:** admin@school.com / admin123
- **Teacher:** teacher@school.com / teacher123 (create via admin)
- **Student:** student@school.com / student123 (create via admin)

## 🚦 Running the Application

### Development Mode
```bash
python app.py
```

The application will run at: `http://localhost:5000`

### Production Deployment
For production, use a WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📁 Project Structure

```
school-management-system/
│
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── uploads/                  # File uploads directory
├── templates/               # HTML templates
│   ├── dashboard.html       # Main dashboard
│   ├── teacher_dashboard.html
│   ├── student_profile.html
│   └── ...
├── static/                  # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── images/
└── README.md                # This file
```

## 🎨 Screenshots

### Dashboard View
![Admin Dashboard](https://raw.githubusercontent.com/BawanthaBeliwaththa/School-Management-System/refs/heads/main/images/dashboard.png)

### Teacher Interface
![Teacher Panel](https://raw.githubusercontent.com/BawanthaBeliwaththa/School-Management-System/refs/heads/main/images/teacher.png)

### Student Portal
![Student Portal](https://raw.githubusercontent.com/BawanthaBeliwaththa/School-Management-System/refs/heads/main/images/student.png)

## 🔧 Configuration

### Environment Variables
Create a `.env` file for sensitive data:
```env
SECRET_KEY=your_secret_key_here
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=python_sms
```

### File Upload Settings
```python
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
```

## 🔐 Security Features

1. **Role-Based Access Control:** Three user roles with specific permissions
2. **Password Hashing:** Store passwords securely (implement in production)
3. **Session Management:** Secure session handling
4. **File Upload Validation:** Type and size restrictions
5. **SQL Injection Protection:** Parameterized queries

## 📊 API Endpoints

### Authentication
- `POST /login` - User login
- `GET /logout` - User logout

### Admin Management
- `GET /teacher` - Teacher management
- `GET /student` - Student management
- `GET /classes` - Class management
- `POST /save_teacher` - Add/Update teacher
- `POST /save_student` - Add/Update student

### LMS Features
- `GET /courses` - Course listing
- `POST /courses` - Create course
- `GET /assignments` - Assignment listing
- `POST /assignments` - Create assignment
- `GET /online_classes` - Online classes

## 🌐 Deployment Options

### Option 1: Heroku Deployment
```bash
# Create Procfile
echo "web: gunicorn app:app" > Procfile

# Create runtime.txt
echo "python-3.9.7" > runtime.txt

# Deploy to Heroku
heroku create school-management-system
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

### Option 2: PythonAnywhere
1. Upload files via PythonAnywhere dashboard
2. Configure MySQL database
3. Set up virtual environment
4. Configure WSGI file
5. Reload web app

### Option 3: VPS Deployment (Ubuntu)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3-pip python3-venv mysql-server nginx -y

# Configure MySQL
sudo mysql_secure_installation

# Clone repository
git clone https://github.com/bawanthabeliwaththa/school-management-system.git
cd school-management-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt gunicorn

# Configure Nginx
sudo nano /etc/nginx/sites-available/sms

# Restart services
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 🐛 Troubleshooting

### Common Issues

1. **MySQL Connection Error**
   - Check MySQL service is running
   - Verify credentials in app.py
   - Ensure database exists

2. **ImportError: No module named 'flask_mysqldb'**
   ```bash
   pip install flask-mysqldb
   ```

3. **Template Not Found**
   - Ensure templates are in correct directory
   - Check template file permissions

4. **File Upload Issues**
   - Check uploads directory exists
   - Verify file permissions
   - Check file size limits

### Debug Mode
Enable debug mode for development:
```python
if __name__ == "__main__":
    app.run(debug=True)
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Contact

For questions or support:
- Email: admin@bawantha-beliwaththa.me
- GitHub Issues: [Report Issues](https://github.com/bawanthabeliwaththa/school-management-system/issues)

## 🙏 Acknowledgments

- Flask Community
- Bootstrap Team
- All contributors and testers

---

**⭐ Star this repository if you found it useful!**
