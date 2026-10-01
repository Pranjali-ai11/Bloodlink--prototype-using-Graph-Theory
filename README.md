# BloodLink - Setup Instructions

## Project Structure
```
bloodlink final/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # Database models
│   ├── routes.py            # All API endpoints
│   ├── utils.py             # Helper functions
│   ├── templates/           # HTML templates
│   │   ├── index.html       # Home page
│   │   ├── register.html    # Registration page
│   │   ├── login.html       # Login page
│   │   ├── search.html      # Search page
│   │   └── dashboard.html   # User dashboard
│   └── static/
│       ├── css/
│       │   └── style.css    # Main stylesheet
│       ├── js/
│       │   ├── app.js       # Global app functions
│       │   ├── auth.js      # Authentication scripts
│       │   ├── search.js    # Search functionality
│       │   └── dashboard.js # Dashboard scripts
│       └── images/          # Images folder
├── config.py                # Configuration settings
├── run.py                   # Entry point
├── requirements.txt         # Python dependencies
├── design.md               # System design document
└── requirement.md          # Requirements document
```

## Installation Steps

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```
FLASK_ENV=development
SECRET_KEY=replace-with-a-random-development-secret
DATABASE_URL=sqlite:///bloodlink.db
```

To bootstrap an administrator, set both values before starting the app:
```
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=use-a-strong-unique-password
```
The app creates that administrator only when both variables are present. There is no built-in admin password. Production startup requires `SECRET_KEY`; development uses a development-only fallback.

### 3. Initialize Database
The database will be created automatically when the app first runs.

### 4. Run the Application
```bash
python run.py
```

The application will start at: **http://localhost:5000**

## System Features

### 1. User Management
- **Donor Registration**: Register as a blood donor with blood group and location
- **User Authentication**: Secure login/logout with password hashing
- **Profile Management**: Update donor profiles and availability status

### 2. Smart Donor Search
- **Location-based Search**: Find nearest donors using Haversine formula
- **Blood Group Matching**: Filter donors by blood type
- **Interactive Map**: Visualize donor locations on map
- **Distance Calculation**: Show distance from patient to donor

### 3. Blood Requests
- **Create Requests**: Patients can create urgent blood requests
- **Urgency Levels**: Critical, Urgent, or Normal
- **Request Tracking**: Monitor request status

### 4. Admin Panel
- **User Management**: View and manage all users
- **Verification**: Verify donor accounts
- **Report Handling**: Process user reports

## API Endpoints

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/current-user` - Get current user info

### Donors
- `GET /api/donors` - List all donors
- `GET /api/donors/<id>` - Get specific donor
- `PUT /api/donors/<id>` - Update donor profile
- `PATCH /api/donors/<id>/availability` - Toggle availability

### Search
- `POST /api/search` - Search donors by blood group and location
- `GET /api/donors/nearby` - Get nearby donors

### Requests
- `POST /api/requests` - Create blood request
- `GET /api/requests/<id>` - Get request details
- `PUT /api/requests/<id>` - Update request status

### Admin
- `GET /api/admin/users` - List all users (admin only)
- `POST /api/admin/verify/<id>` - Verify user (admin only)
- `GET /api/admin/reports` - View reports (admin only)
- `PUT /api/admin/reports/<id>` - Handle report (admin only)

## Database Models

### User
- user_id (Primary Key)
- name
- email (Unique)
- password_hash
- phone
- role (donor/seeker/admin)
- is_verified
- created_at

### Donor
- donor_id (Primary Key)
- user_id (Foreign Key)
- blood_group
- latitude, longitude
- address, city
- is_available
- last_donation_date
- donation_count

### BloodRequest
- request_id (Primary Key)
- requester_id (Foreign Key)
- blood_group
- urgency_level
- location
- latitude, longitude
- status
- created_at

### Report
- report_id (Primary Key)
- reporter_id (Foreign Key)
- reported_user_id (Foreign Key)
- reason
- status
- created_at

## Key Algorithms

### Haversine Distance Formula
Calculates the shortest distance between two points on Earth given their coordinates.

### Smart Donor Matching
1. Find all available donors with matching blood group
2. Calculate distance from patient location
3. Filter by search radius
4. Sort by distance (nearest first)
5. Apply reliability scoring

### Reliability Score
- Base score: 50
- Donation count bonus: up to +30 (1 point per 10 donations)
- Verification bonus: +20

## Security Features

1. **Password Hashing**: Using bcrypt
2. **Session Management**: Flask session handling
3. **SQL Injection Prevention**: SQLAlchemy parameterized queries
4. **Input Validation**: Server-side validation
5. **CSRF Protection**: Flask default protection
6. **HTTPS Ready**: Can be deployed with SSL

## Future Enhancements

1. Email/SMS notifications
2. Real-time chat between donor and seeker
3. Mobile app (React Native/Flutter)
4. Blood bank integration
5. Donation camps calendar
6. Gamification system
7. Social media integration
8. Advanced analytics dashboard

## Troubleshooting

### Database Not Creating
Make sure you have write permissions in the project directory.

### Port Already in Use
Change the port in `run.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Location Issues
Make sure browser has permission to access geolocation.

## Technology Stack

- **Backend**: Flask 2.3.0
- **Database**: SQLite (SQLAlchemy ORM)
- **Frontend**: HTML5, CSS3, JavaScript
- **Maps**: Leaflet.js with OpenStreetMap
- **Security**: bcrypt for password hashing
- **Geolocation**: Haversine formula for distance

## License
This project is open source and available for educational purposes.

## Contact & Support
For issues or questions, feel free to reach out.


## Hospital and Blood Bank Directory

The BloodLink Network page includes a hospital directory and blood bank inventory. These are separate directory records; they are not automatically used as donor locations or global assignment candidates. Existing blood requests remain compatible and are not altered to require a hospital foreign key.

Initialize optional sample records from the project root with:

    python tools/seed_facilities.py

The script is idempotent. Its example facilities and unit counts are explicitly marked as demo data and must not be treated as live availability. Replace them with verified information before operational use.

Facility APIs:

- GET /api/hospitals — hospital directory
- GET /api/blood-banks — blood banks and recorded inventory
- GET /api/blood-banks/<id>/inventory — one bank's inventory
