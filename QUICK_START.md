# BloodLink - Quick Start Guide

## 🚀 Project Successfully Created!

Your BloodLink emergency blood donor finder platform has been fully built and is ready to use!

## 📋 What's Included

### ✅ Backend (Flask Application)
- Complete Flask server with SQLAlchemy ORM
- Database models for Users, Donors, Requests, and Reports
- RESTful API endpoints
- Authentication system with bcrypt password hashing
- Smart donor matching algorithm using Haversine formula
- Location-based search functionality

### ✅ Frontend (HTML/CSS/JavaScript)
- Responsive design for desktop and mobile
- Modern UI with emergency blood red color scheme
- Interactive map integration with Leaflet.js
- Real-time search functionality
- User dashboard
- Registration and login pages

### ✅ Database
- SQLite database with 4 tables
- Automatic table creation on first run
- Foreign key relationships
- Ready to migrate to PostgreSQL for production

### ✅ Features Implemented
1. **User Registration & Authentication**
   - Role-based registration (Donor/Seeker)
   - Secure password hashing
   - Session management

2. **Donor Management**
   - Register with blood group and location
   - Update profile and availability
   - Track donation history

3. **Smart Search**
   - Find nearest donors by blood group
   - Location-based filtering
   - Distance calculation
   - Interactive map visualization

4. **Blood Requests**
   - Create urgent blood requests
   - Set urgency levels
   - Track request status

5. **Admin Panel API**
   - User management
   - Donor verification
   - Report handling

## 🎯 How to Use

### 1. Start the Server
The server is currently running at: **http://localhost:5000**

If you need to restart it:
```bash
python run.py
```

### 2. Access the Application
- **Home Page**: http://localhost:5000/
- **Register**: http://localhost:5000/register
- **Login**: http://localhost:5000/login
- **Search Donors**: http://localhost:5000/search
- **Dashboard**: http://localhost:5000/dashboard (after login)

## 📝 Test Account Setup

### Option 1: Register as Donor
1. Go to http://localhost:5000/register
2. Select "Blood Donor" as role
3. Fill in details and click "Get My Location"
4. Submit registration

### Option 2: Register as Blood Seeker
1. Go to http://localhost:5000/register
2. Select "Blood Seeker" as role
3. Fill in details and submit

### Option 3: Use API Directly
```bash
# Register a donor
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Donor",
    "email": "john@example.com",
    "phone": "9876543210",
    "password": "password123",
    "role": "donor",
    "blood_group": "O+",
    "city": "Mumbai",
    "address": "123 Main St",
    "latitude": 19.0760,
    "longitude": 72.8777
  }'

# Login
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password123"
  }'

# Search donors
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "blood_group": "O+",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "radius_km": 10
  }'
```

## 🔧 Project Structure

```
bloodlink final/
│
├── app/
│   ├── __init__.py              # App factory
│   ├── models.py                # Database models
│   ├── routes.py               # All API endpoints
│   ├── utils.py                # Helper functions
│   ├── templates/
│   │   ├── index.html
│   │   ├── register.html
│   │   ├── login.html
│   │   ├── search.html
│   │   └── dashboard.html
│   └── static/
│       ├── css/style.css        # Responsive styling
│       ├── js/
│       │   ├── app.js           # Global functions
│       │   ├── auth.js          # Auth logic
│       │   ├── search.js        # Search functionality
│       │   └── dashboard.js     # Dashboard logic
│       └── images/              # Image assets
│
├── config.py                    # Configuration
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
├── .env                        # Environment variables
├── .gitignore                  # Git ignore rules
├── README.md                   # Full documentation
├── design.md                   # System design
└── requirement.md              # Requirements document
```

## 📊 Database Schema

### Users Table
```sql
- user_id (Primary Key)
- name, email, password_hash, phone
- role (donor/seeker/admin)
- is_verified, created_at
```

### Donors Table
```sql
- donor_id (Primary Key)
- user_id (Foreign Key)
- blood_group, latitude, longitude
- address, city, is_available
- last_donation_date, donation_count
```

### Blood Requests Table
```sql
- request_id (Primary Key)
- requester_id, blood_group
- urgency_level, location
- latitude, longitude, status, created_at
```

### Reports Table
```sql
- report_id (Primary Key)
- reporter_id, reported_user_id
- reason, status, created_at
```

## 🔐 Security Features

✅ Password hashing with bcrypt
✅ SQL injection prevention (SQLAlchemy ORM)
✅ Session management
✅ Input validation
✅ CSRF protection ready
✅ HTTPS ready for production

## 🚀 Deployment Ready

### For Development
```bash
python run.py
```

### For Production
1. Set environment variables in `.env`
2. Use Gunicorn as application server
3. Deploy database to PostgreSQL
4. Set up Nginx reverse proxy
5. Enable SSL/TLS with certificates
6. Deploy to AWS/Heroku/DigitalOcean

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

## 📱 Responsive Design

✅ Works on desktop (1920px+)
✅ Works on tablet (768px - 1024px)
✅ Works on mobile (320px - 767px)
✅ Touch-friendly buttons (>=44px)
✅ Fast loading and smooth animations

## 🎨 Color Scheme

- Primary Red: #e74c3c (Emergency blood red)
- Secondary Blue: #3498db (Calm blue)
- Success Green: #27ae60 (Availability green)
- Dark Gray: #2c3e50 (Text)
- Light Gray: #ecf0f1 (Background)

## 📦 Dependencies

```
Flask==2.3.0
Flask-SQLAlchemy==3.0.3
python-dotenv==1.0.0
bcrypt==4.0.1
geopy==2.2.0
```

## 🤝 Next Steps

1. **Test the Application**
   - Register as donor
   - Register as seeker
   - Search for donors
   - Create blood requests

2. **Customize**
   - Add your branding/logo
   - Modify color scheme in `style.css`
   - Add more custom fields to registration

3. **Extend Features**
   - Add email notifications
   - Integrate Maps API for better visualization
   - Add donation tracking
   - Create admin dashboard

4. **Deploy**
   - Set up production database
   - Configure environment variables
   - Deploy to cloud hosting
   - Set up monitoring and logging

## 🐛 Troubleshooting

### Port 5000 already in use?
Edit `run.py` and change:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Database not found?
The database is created automatically. Check that you have write permissions.

### Geolocation not working?
Make sure browser has permission to access location. Works best over HTTPS.

### Maps not loading?
This uses OpenStreetMap (Leaflet.js), which doesn't require API key.

## 📞 Support

For issues or queries, check:
1. README.md - Full documentation
2. design.md - System architecture
3. requirement.md - Requirements
4. Flask documentation: https://flask.palletsprojects.com/

## ✨ You're All Set!

Your BloodLink application is ready to save lives! 🩸💙

Start by visiting: **http://localhost:5000**
