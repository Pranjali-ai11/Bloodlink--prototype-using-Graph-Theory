from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt
from .eligibility import is_donor_eligible

db = SQLAlchemy()

class User(db.Model):
    """User model for both donors and blood seekers"""
    __tablename__ = 'users'
    __table_args__ = (
        db.Index('uq_users_email_normalized', 'email_normalized', unique=True),
        db.Index('uq_users_phone_normalized', 'phone_normalized', unique=True),
    )
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    email_normalized = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    phone_normalized = db.Column(db.String(15), nullable=True)
    role = db.Column(db.String(20), default='donor')  
    gender = db.Column(db.String(20))  
    age = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    donor_profile = db.relationship('Donor', uselist=False, backref='user', cascade='all, delete-orphan')
    medical_history = db.relationship('MedicalHistory', uselist=False, back_populates='user', cascade='all, delete-orphan')
    requests_created = db.relationship('BloodRequest', foreign_keys='BloodRequest.requester_id', backref='requester', cascade='all, delete-orphan')
    reports_filed = db.relationship('Report', foreign_keys='Report.reporter_id', backref='reporter', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Check if password matches hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'gender': self.gender,
            'age': self.age,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat()
        }

class Donor(db.Model):
    """Donor profile model"""
    __tablename__ = 'donors'
    
    donor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)  # A+, A-, B+, B-, O+, O-, AB+, AB-
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    is_available = db.Column(db.Boolean, default=True)
    last_donation_date = db.Column(db.Date)
    donation_count = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        eligibility = is_donor_eligible(self)
        return {
            'donor_id': self.donor_id,
            'user_id': self.user_id,
            'name': self.user.name,
            'email': self.user.email,
            'phone': self.user.phone,
            'blood_group': self.blood_group,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'city': self.city,
            'age': self.user.age,
            'is_available': self.is_available,
            'last_donation_date': self.last_donation_date.isoformat() if self.last_donation_date else None,
            'donation_count': self.donation_count,
            'is_eligible': eligibility['eligible'],
            'eligibility_status': eligibility['status'],
            'eligibility_reason': eligibility['reason'],
            'eligible_after': eligibility['eligible_after'].isoformat() if eligibility['eligible_after'] else None,
            'is_verified': self.user.is_verified
        }

class MedicalHistory(db.Model):
    """Private, self-reported medical history owned by one user."""
    __tablename__ = 'medical_histories'

    medical_history_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True, index=True)
    allergies = db.Column(db.Text, nullable=True)
    chronic_conditions = db.Column(db.Text, nullable=True)
    current_medications = db.Column(db.Text, nullable=True)
    previous_surgeries = db.Column(db.Text, nullable=True)
    previous_major_illnesses = db.Column(db.Text, nullable=True)
    recent_illness = db.Column(db.Text, nullable=True)
    last_checkup_date = db.Column(db.Date, nullable=True)
    additional_notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='medical_history')

    def to_dict(self):
        return {
            'medical_history_id': self.medical_history_id,
            'user_id': self.user_id,
            'allergies': self.allergies,
            'chronic_conditions': self.chronic_conditions,
            'current_medications': self.current_medications,
            'previous_surgeries': self.previous_surgeries,
            'previous_major_illnesses': self.previous_major_illnesses,
            'recent_illness': self.recent_illness,
            'last_checkup_date': self.last_checkup_date.isoformat() if self.last_checkup_date else None,
            'additional_notes': self.additional_notes,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class BloodRequest(db.Model):
    """Blood request model"""
    __tablename__ = 'blood_requests'
    
    request_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    urgency_level = db.Column(db.String(20), default='normal')  # 'critical', 'urgent', 'normal'
    location = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(20), default='active')  # 'active', 'fulfilled', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'request_id': self.request_id,
            'requester_id': self.requester_id,
            'requester_name': self.requester.name,
            'requester_phone': self.requester.phone,
            'blood_group': self.blood_group,
            'urgency_level': self.urgency_level,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class Report(db.Model):
    """Report model for spam/abuse reporting"""
    __tablename__ = 'reports'
    
    report_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reported_user = db.relationship('User', foreign_keys=[reported_user_id], backref='reports_against')
    
    def to_dict(self):
        return {
            'report_id': self.report_id,
            'reporter_id': self.reporter_id,
            'reported_user_id': self.reported_user_id,
            'reported_user_name': self.reported_user.name,
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class Hospital(db.Model):
    """A hospital directory entry; demo rows are explicitly marked."""
    __tablename__ = 'hospitals'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(80))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    phone = db.Column(db.String(30))
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'address': self.address,
            'city': self.city, 'latitude': self.latitude, 'longitude': self.longitude,
            'phone': self.phone, 'is_demo': bool(self.is_demo),
        }


class BloodBank(db.Model):
    """Blood bank directory entry with one-to-many inventory records."""
    __tablename__ = 'blood_banks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(80))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    phone = db.Column(db.String(30))
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    inventory = db.relationship(
        'BloodInventory', back_populates='blood_bank',
        cascade='all, delete-orphan', order_by='BloodInventory.blood_group'
    )

    def to_dict(self, include_inventory=False):
        data = {
            'id': self.id, 'name': self.name, 'address': self.address,
            'city': self.city, 'latitude': self.latitude, 'longitude': self.longitude,
            'phone': self.phone, 'is_demo': bool(self.is_demo),
        }
        if include_inventory:
            data['inventory'] = [item.to_dict() for item in self.inventory]
        return data


class BloodInventory(db.Model):
    """One recorded group and unit count for a blood bank."""
    __tablename__ = 'blood_inventory'
    __table_args__ = (
        db.UniqueConstraint('blood_bank_id', 'blood_group', name='uq_bank_blood_group'),
        db.CheckConstraint('units >= 0', name='ck_blood_inventory_nonnegative_units'),
    )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    blood_bank_id = db.Column(
        db.Integer, db.ForeignKey('blood_banks.id'), nullable=False, index=True
    )
    blood_group = db.Column(db.String(5), nullable=False)
    units = db.Column(db.Integer, nullable=False, default=0)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    blood_bank = db.relationship('BloodBank', back_populates='inventory')

    def to_dict(self):
        return {
            'id': self.id, 'blood_bank_id': self.blood_bank_id,
            'blood_group': self.blood_group, 'units': self.units,
            'is_demo': bool(self.is_demo),
        }
