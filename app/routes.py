from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, send_file
from sqlalchemy.exc import IntegrityError
from .account_identity import normalize_email, normalize_phone
from .models import (db, User, Donor, BloodRequest, Report, MedicalHistory,
                     Hospital, BloodBank, BloodInventory)
from .utils import find_nearby_donors, geocode_address
from .eligibility import is_donor_eligible
from .graph_service import build_network_data, compatibility_order_data
from .matching_service import assign_donors
from sqlalchemy.orm import joinedload, selectinload
from functools import wraps
from datetime import datetime, date
from types import SimpleNamespace


main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
donor_bp = Blueprint('donor', __name__)
search_bp = Blueprint('search', __name__)
admin_bp = Blueprint('admin', __name__)

def login_required(f):
    """Decorator to check if user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to check if user is admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@main_bp.route('/register')
def register_page():
    """Registration page"""
    return render_template('register.html')

@main_bp.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@main_bp.route('/dashboard')
def dashboard():
    """User dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))
    return render_template('dashboard.html')

@main_bp.route('/network')
def network_page():
    """Graph dashboard for signed-in users and administrators."""
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('main.login_page'))
    query = BloodRequest.query.filter_by(status='active')
    if user.role != 'admin':
        query = query.filter_by(requester_id=user.user_id)
    requests = query.order_by(BloodRequest.request_id.desc()).all()
    return render_template('network.html', blood_requests=requests, is_admin=user.role == 'admin')


@main_bp.route('/medical-history')
def medical_history_page():
    """Private medical history page for the logged-in account."""
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))
    return render_template('medical_history.html')

@main_bp.route('/search')
def search_page():
    """Search donors page"""
    return render_template('search.html')

@main_bp.route('/admin/hospitals')
def admin_hospitals():
    """Admin hospital management page"""
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))
    
    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('main.dashboard'))
    
    return render_template('admin_hospitals.html')
@main_bp.route('/admin/donors')
def admin_donors():
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('main.dashboard'))

    donors = Donor.query.all()
    eligibility_by_id = {donor.donor_id: is_donor_eligible(donor) for donor in donors}

    return render_template('admin_donors.html', donors=donors, eligibility_by_id=eligibility_by_id)


@main_bp.route('/admin/requests')
def admin_requests():
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('main.dashboard'))

    requests = BloodRequest.query.order_by(BloodRequest.request_id.desc()).all()

    return render_template('admin_requests.html', requests=requests)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new user"""
    try:
        data = request.get_json()
        
        if not all([data.get('name'), data.get('email'), data.get('password'), data.get('phone')]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        email = normalize_email(data.get('email'))
        phone = normalize_phone(data.get('phone'))
        if not email:
            return jsonify({'error': 'Missing required fields'}), 400
        if not phone.isdigit() or len(phone) != 10:
            return jsonify({'error': 'Phone must be exactly 10 digits'}), 400
        raw_age = data.get('age')
        try:
            if isinstance(raw_age, bool):
                raise ValueError
            numeric_age = float(raw_age)
            if not numeric_age.is_integer():
                raise ValueError
            age = int(numeric_age)
        except (TypeError, ValueError):
            return jsonify({'error': 'Please enter your age as a whole number.'}), 400
        role = data.get('role', 'donor')
        if role == 'donor' and age < 18:
            return jsonify({'error': 'Donors must be 18 or older to register.'}), 400
        if age < 0:
            return jsonify({'error': 'Please enter a valid age.'}), 400
        password = data.get('password', '')
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        if not any(c.isupper() for c in password):
            return jsonify({'error': 'Password must contain at least 1 uppercase letter'}), 400
        if not any(c in '!@#$%^&*()_+-=[]{};\':"|,.<>?\/' for c in password):
            return jsonify({'error': 'Password must contain at least 1 special character'}), 400
        
        for existing_email, existing_phone in User.query.with_entities(
                User.email, User.phone).yield_per(500):
            if normalize_email(existing_email) == email:
                return jsonify({'error': 'An account already exists with this email.'}), 409
        for existing_phone, in User.query.with_entities(User.phone).yield_per(500):
            if normalize_phone(existing_phone) == phone:
                return jsonify({'error': 'An account already exists with this mobile number.'}), 409
        
        user = User(
            name=data['name'],
            email=email,
            email_normalized=email,
            phone=phone,
            phone_normalized=phone,
            gender=data.get('gender'),
            role=role,
            age=age
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.flush()
        if user.role == 'donor':
            donor = Donor(
                user_id=user.user_id,
                blood_group=data.get('blood_group', ''),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                address=data.get('address', ''),
                city=data.get('city', '')
            )
            db.session.add(donor)
        db.session.commit()
        
        session['user_id'] = user.user_id
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201
    
    except IntegrityError as e:
        db.session.rollback()
        constraint = str(getattr(e, 'orig', e)).lower()
        if 'email_normalized' in constraint or 'users.email' in constraint:
            return jsonify({'error': 'An account already exists with this email.'}), 409
        if 'phone_normalized' in constraint:
            return jsonify({'error': 'An account already exists with this mobile number.'}), 409
        return jsonify({'error': 'Unable to create account'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing email or password'}), 400

        normalized_email = normalize_email(data['email'])
        user = User.query.filter_by(email_normalized=normalized_email).first()
        if not user:
            # Keep legacy accounts with pre-normalization duplicate identifiers
            # accessible by their exact stored email.
            user = User.query.filter_by(email=data['email']).first()

        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401

        session['user_id'] = user.user_id

        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/current-user', methods=['GET'])
@login_required
def current_user():
    """Get current user info"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user_data = user.to_dict()
    if user.donor_profile:
        user_data['donor'] = user.donor_profile.to_dict()
    
    return jsonify(user_data), 200

@auth_bp.route('/medical-history', methods=['GET'])
@login_required
def get_own_medical_history():
    """Return only the authenticated user's private medical history."""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    history = MedicalHistory.query.filter_by(user_id=user.user_id).first()
    return jsonify({'medical_history': history.to_dict() if history else None}), 200

@auth_bp.route('/medical-history', methods=['POST', 'PUT'])
@login_required
def save_own_medical_history():
    """Create or update the authenticated user's self-reported history."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Please submit medical history as a JSON object.'}), 400

    text_fields = (
        'allergies', 'chronic_conditions', 'current_medications', 'previous_surgeries',
        'previous_major_illnesses', 'recent_illness', 'additional_notes'
    )
    normalized = {}
    for field in text_fields:
        if field not in data:
            continue
        value = data[field]
        if value is not None and not isinstance(value, str):
            return jsonify({'error': f'{field.replace("_", " ").capitalize()} must be text.'}), 400
        value = value.strip() if value is not None else None
        if value and len(value) > 5000:
            return jsonify({'error': f'{field.replace("_", " ").capitalize()} must be 5000 characters or fewer.'}), 400
        normalized[field] = value or None

    if 'last_checkup_date' in data:
        raw_date = data['last_checkup_date']
        if raw_date in (None, ''):
            normalized['last_checkup_date'] = None
        elif not isinstance(raw_date, str):
            return jsonify({'error': 'Last medical checkup must be a valid date.'}), 400
        else:
            try:
                parsed_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
                if parsed_date.isoformat() != raw_date or parsed_date > date.today():
                    raise ValueError
                normalized['last_checkup_date'] = parsed_date
            except ValueError:
                return jsonify({'error': 'Last medical checkup must be a valid date no later than today.'}), 400

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    history = MedicalHistory.query.filter_by(user_id=user.user_id).first()
    if not history:
        history = MedicalHistory(user_id=user.user_id)
        db.session.add(history)
    for field, value in normalized.items():
        setattr(history, field, value)
    history.updated_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({'message': 'Medical history saved.', 'medical_history': history.to_dict()}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Could not save medical history.'}), 500

@donor_bp.route('/donors', methods=['GET'])
def get_donors():
    """Get all donors with pagination and filters"""
    try:
        page = request.args.get('page', 1, type=int)
        blood_group = request.args.get('blood_group')
        city = request.args.get('city')
        
        query = Donor.query.join(User).filter(
            Donor.is_available.is_(True),
            User.age >= 18
        )
        
        if blood_group:
            query = query.filter_by(blood_group=blood_group)
        
        if city:
            query = query.filter_by(city=city)
        
        donors = [donor for donor in query.all() if is_donor_eligible(donor)['eligible']]
        total = len(donors)
        page = max(page, 1)
        page_donors = donors[(page - 1) * 10:page * 10]

        return jsonify({
            'donors': [d.to_dict() for d in page_donors],
            'total': total,
            'pages': (total + 9) // 10
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@donor_bp.route('/donors/<int:donor_id>', methods=['GET'])
def get_donor(donor_id):
    """Get specific donor"""
    try:
        donor = Donor.query.get(donor_id)
        
        if not donor:
            return jsonify({'error': 'Donor not found'}), 404
        
        return jsonify(donor.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@donor_bp.route('/donors/<int:donor_id>', methods=['PUT'])
@login_required
def update_donor(donor_id):
    """Update donor profile"""
    try:
        donor = Donor.query.get(donor_id)
        
        if not donor or donor.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json() or {}

        updated_age = None
        if 'age' in data:
            try:
                raw_age = data['age']
                if isinstance(raw_age, bool):
                    raise ValueError
                numeric_age = float(raw_age)
                if not numeric_age.is_integer() or numeric_age < 0:
                    raise ValueError
                updated_age = int(numeric_age)
            except (TypeError, ValueError):
                return jsonify({'error': 'Please enter a valid age as a whole number.'}), 400

        if 'blood_group' in data:
            donor.blood_group = data['blood_group']
        if updated_age is not None:
            donor.user.age = updated_age
        if 'latitude' in data:
            donor.latitude = data['latitude']
        if 'longitude' in data:
            donor.longitude = data['longitude']
        if 'address' in data:
            donor.address = data['address']
        if 'city' in data:
            donor.city = data['city']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Donor profile updated',
            'donor': donor.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@donor_bp.route('/donors/<int:donor_id>/availability', methods=['PATCH'])
@login_required
def toggle_availability(donor_id):
    """Toggle donor availability"""
    try:
        donor = Donor.query.get(donor_id)
        
        if not donor or donor.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        requested_availability = data.get('is_available', not donor.is_available)
        if not isinstance(requested_availability, bool):
            return jsonify({'error': 'Availability must be true or false.'}), 400
        eligibility = is_donor_eligible(donor)
        if requested_availability and not eligibility['eligible']:
            return jsonify({
                'error': eligibility['reason'],
                'eligibility': eligibility
            }), 400

        donor.is_available = requested_availability
        
        db.session.commit()
        
        return jsonify({
            'message': 'Availability updated',
            'donor': donor.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@search_bp.route('/search', methods=['POST'])
def search():
    """Search radius-limited donors using the Network page's ranked graph result."""
    try:
        data = request.get_json() or {}
        patient_group = data.get('blood_group')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        location_text = data.get('location')
        radius_km = float(data.get('radius_km', 10))

        if (latitude is None or longitude is None) and location_text:
            lat, lon = geocode_address(location_text)
            latitude = latitude if latitude is not None else lat
            longitude = longitude if longitude is not None else lon

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return jsonify({'error': 'Missing or invalid coordinates'}), 400
        if not patient_group:
            return jsonify({'error': 'Blood group is required'}), 400
        if radius_km < 0:
            return jsonify({'error': 'Radius must be zero or greater'}), 400

        raw_urgency = data.get('urgency', 2)
        urgency_names = {1: 'normal', 2: 'urgent', 3: 'critical'}
        if isinstance(raw_urgency, str) and raw_urgency.lower() in ('normal', 'urgent', 'critical'):
            urgency_level = raw_urgency.lower()
        else:
            try:
                urgency_level = urgency_names.get(int(raw_urgency), 'urgent')
            except (TypeError, ValueError):
                urgency_level = 'urgent'

        # The graph service is the single source for compatibility, Dijkstra
        # distance, normalized ai_score and donor ordering used by both pages.
        search_request = SimpleNamespace(
            request_id='search', blood_group=patient_group,
            urgency_level=urgency_level, location=location_text or 'Search location',
            latitude=latitude, longitude=longitude, status='active',
        )
        donor_records = Donor.query.options(joinedload(Donor.user)).all()
        donor_by_id = {donor.donor_id: donor for donor in donor_records}
        ranked = build_network_data(search_request, donors=donor_records)['donors']

        results = []
        for match in ranked:
            distance = match['distance_km']
            if distance is None or distance > radius_km:
                continue
            donor = donor_by_id[match['donor_id']]
            results.append({
                'donor_id': donor.donor_id,
                'name': donor.user.name,
                'email': donor.user.email,
                'age': donor.user.age,
                'city': donor.city,
                'blood_group': donor.blood_group,
                'latitude': donor.latitude,
                'longitude': donor.longitude,
                'distance_km': distance,
                'route_distance_km': match['route_distance_km'],
                'is_available': bool(donor.is_available),
                'is_verified': bool(donor.user.is_verified),
                'is_eligible': match['is_eligible'],
                'last_donation_date': donor.last_donation_date.isoformat() if donor.last_donation_date else None,
                'donation_count': donor.donation_count or 0,
                'donations': donor.donation_count or 0,
                'reliability_score': match['reliability_score'],
                'ai_score': match['ai_score'],
                'rank': match['rank'],
                'match_level': match['match_level'],
                'blood_match': match['blood_match'],
                'why_recommended': match['why_recommended'],
            })

        return jsonify({'donors': results, 'count': len(results)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/donors/nearby', methods=['GET'])
def get_nearby_donors():
    """Get nearby donors (alternative endpoint)"""
    try:
        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')
        location_text = request.args.get('location')
        blood_group = request.args.get('blood_group')
        radius_km = float(request.args.get('radius_km', 10))

        if (not latitude or not longitude) and location_text:
            lat, lon = geocode_address(location_text)
            latitude = latitude or lat
            longitude = longitude or lon

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return jsonify({'error': 'Missing or invalid coordinates'}), 400

        donors = find_nearby_donors(blood_group, latitude, longitude, radius_km)
        return jsonify(donors), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@search_bp.route('/hospitals', methods=['GET'])
def get_hospitals():
    """List BloodLink hospital directory records."""
    hospitals = Hospital.query.order_by(Hospital.city, Hospital.name).all()
    return jsonify({'hospitals': [hospital.to_dict() for hospital in hospitals],
                    'count': len(hospitals)}), 200


@search_bp.route('/blood-banks', methods=['GET'])
def get_blood_banks():
    """List blood banks and their recorded inventory."""
    blood_banks = BloodBank.query.options(
        selectinload(BloodBank.inventory)
    ).order_by(BloodBank.city, BloodBank.name).all()
    return jsonify({
        'blood_banks': [bank.to_dict(include_inventory=True) for bank in blood_banks],
        'count': len(blood_banks),
        'inventory_notice': 'Recorded sample/demo quantities are not live availability.',
    }), 200


@search_bp.route('/blood-banks/<int:bank_id>/inventory', methods=['GET'])
def get_blood_bank_inventory(bank_id):
    """Return the recorded inventory for one blood bank."""
    blood_bank = BloodBank.query.options(
        selectinload(BloodBank.inventory)
    ).filter_by(id=bank_id).first()
    if not blood_bank:
        return jsonify({'error': 'Blood bank not found'}), 404
    return jsonify({
        'blood_bank': blood_bank.to_dict(),
        'inventory': [item.to_dict() for item in blood_bank.inventory],
        'inventory_notice': 'Recorded sample/demo quantities are not live availability.',
    }), 200

@search_bp.route('/assign', methods=['GET'])
@login_required
def get_assignments():
    """Run global donor assignment; non-admins see only their request and no donor identity."""
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'error': 'Unauthorized'}), 401
    active_requests = BloodRequest.query.filter_by(status='active').order_by(
        BloodRequest.request_id.asc()
    ).all()
    donors = Donor.query.options(joinedload(Donor.user)).all()
    result = assign_donors(active_requests, donors)
    is_admin = user.role == 'admin'

    def request_summary(blood_request):
        summary = {
            'request_id': blood_request.request_id,
            'blood_group': blood_request.blood_group,
            'urgency_level': blood_request.urgency_level,
            'location': blood_request.location,
            'status': blood_request.status,
        }
        if is_admin:
            summary['requester_name'] = blood_request.requester.name
        return summary

    assignments = []
    for item in result['assignments']:
        blood_request, donor = item['request'], item['donor']
        if not is_admin and blood_request.requester_id != user.user_id:
            continue
        assignment = {
            'request': request_summary(blood_request),
            'donor_assigned': True,
        }
        if is_admin:
            assignment['donor'] = {
                'donor_id': donor.donor_id,
                'name': donor.user.name,
                'email': donor.user.email,
                'phone': donor.user.phone,
                'blood_group': donor.blood_group,
                'city': donor.city,
                'is_verified': bool(donor.user.is_verified),
                'donation_count': donor.donation_count or 0,
            }
        assignments.append(assignment)

    unmatched_requests = []
    for item in result['unmatched_requests']:
        blood_request = item['request']
        if not is_admin and blood_request.requester_id != user.user_id:
            continue
        unmatched = {
            'request': request_summary(blood_request),
            'hall_explanation': item['hall_explanation'],
        }
        if is_admin:
            unmatched['hall_request_ids'] = item['hall_request_ids']
            unmatched['hall_donor_ids'] = item['hall_donor_ids']
        unmatched_requests.append(unmatched)
    return jsonify({
        'assignments': assignments,
        'unmatched_requests': unmatched_requests,
        'assignment_count': len(assignments),
        'unmatched_count': len(unmatched_requests),
    }), 200


@search_bp.route('/compatibility/order', methods=['GET'])
def get_compatibility_order():
    """Return partial-order properties and Hasse cover edges from the compatibility graph."""
    return jsonify(compatibility_order_data()), 200


@search_bp.route('/network', methods=['GET'])
@login_required
def get_network():
    """Return graph data for an owned request, or any active request for admins."""
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'error': 'Unauthorized'}), 401
    query = BloodRequest.query.filter_by(status='active')
    if user.role != 'admin':
        query = query.filter_by(requester_id=user.user_id)
    request_id = request.args.get('request_id', type=int)
    blood_request = query.filter_by(request_id=request_id).first() if request_id is not None else query.order_by(BloodRequest.request_id.desc()).first()
    if request_id is not None and not blood_request:
        return jsonify({'error': 'Active blood request not found'}), 404
    return jsonify(build_network_data(blood_request)), 200


@search_bp.route('/requests', methods=['POST'])
@login_required
def create_request():
    """Create blood request"""
    try:
        data = request.get_json()
        
        blood_request = BloodRequest(
            requester_id=session['user_id'],
            blood_group=data.get('blood_group'),
            urgency_level=data.get('urgency_level', 'normal'),
            location=data.get('location'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )
        
        db.session.add(blood_request)
        db.session.commit()
        
        return jsonify({
            'message': 'Blood request created',
            'request': blood_request.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@search_bp.route('/requests', methods=['GET'])
@login_required
def get_user_requests():
    """List blood requests created by the signed-in user."""
    try:
        requests = BloodRequest.query.filter_by(
            requester_id=session['user_id']
        ).order_by(BloodRequest.request_id.desc()).all()
        return jsonify({
            'requests': [blood_request.to_dict() for blood_request in requests],
            'count': len(requests)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/requests/<int:request_id>', methods=['GET'])
def get_request(request_id):
    """Get blood request details"""
    try:
        blood_request = BloodRequest.query.get(request_id)
        
        if not blood_request:
            return jsonify({'error': 'Request not found'}), 404
        
        return jsonify(blood_request.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/requests/<int:request_id>', methods=['PUT'])
@login_required
def update_request(request_id):
    """Update blood request"""
    try:
        blood_request = BloodRequest.query.get(request_id)
        
        if not blood_request or blood_request.requester_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        if 'status' in data:
            blood_request.status = data['status']
        if 'urgency_level' in data:
            blood_request.urgency_level = data['urgency_level']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Request updated',
            'request': blood_request.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        role = request.args.get('role')
        
        from sqlalchemy import or_

        query = User.query.filter(
    or_(User.role == 'donor', User.role == 'seeker')
)
        if role:
            query = query.filter_by(role=role)
        
        users = query.paginate(page=page, per_page=10)
        
        return jsonify({
            'users': [u.to_dict() for u in users.items],
            'total': users.total,
            'pages': users.pages
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/users/<int:user_id>/medical-history', methods=['GET'])
@admin_required
def get_user_medical_history(user_id):
    """Admin-only, explicit access to one user's private health history."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    history = MedicalHistory.query.filter_by(user_id=user.user_id).first()
    return jsonify({
        'user': {'user_id': user.user_id, 'name': user.name, 'role': user.role},
        'medical_history': history.to_dict() if history else None
    }), 200

@admin_bp.route('/admin/donors/<int:donor_id>/complete-donation', methods=['POST'])
@admin_required
def complete_donation(donor_id):
    """Record one completed donation using the existing donor history fields."""
    try:
        donor = Donor.query.get(donor_id)
        if not donor:
            return jsonify({'error': 'Donor not found'}), 404

        today = date.today()
        if donor.last_donation_date == today:
            return jsonify({'error': 'A donation has already been recorded for this donor today.'}), 409

        eligibility = is_donor_eligible(donor, today=today)
        if not eligibility['eligible']:
            return jsonify({'error': eligibility['reason'], 'eligibility': eligibility}), 400

        donor.last_donation_date = today
        donor.donation_count = (donor.donation_count or 0) + 1
        donor.is_available = False
        db.session.commit()

        return jsonify({
            'message': 'Donation recorded successfully.',
            'donor': donor.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user details (admin only)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']
        if 'is_verified' in data:
            user.is_verified = data['is_verified']
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete user (admin only)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/verify/<int:user_id>', methods=['POST'])
@admin_required
def verify_user(user_id):
    """Verify user (admin only)"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.is_verified = True
        db.session.commit()
        
        return jsonify({
            'message': 'User verified',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/reports', methods=['GET'])
@admin_required
def get_reports():
    """Get all reports (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status')
        
        query = Report.query
        if status:
            query = query.filter_by(status=status)
        
        reports = query.paginate(page=page, per_page=10)
        
        return jsonify({
            'reports': [r.to_dict() for r in reports.items],
            'total': reports.total,
            'pages': reports.pages
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/reports/<int:report_id>', methods=['PUT'])
@admin_required
def handle_report(report_id):
    """Handle report (admin only)"""
    try:
        report = Report.query.get(report_id)
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        data = request.get_json()
        report.status = data.get('status', 'pending')
        
        db.session.commit()
        
        return jsonify({
            'message': 'Report updated',
            'report': report.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/reports', methods=['POST'])
@login_required
def create_report():
    """Create report about user"""
    try:
        data = request.get_json()
        
        report = Report(
            reporter_id=session['user_id'],
            reported_user_id=data.get('reported_user_id'),
            reason=data.get('reason')
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'message': 'Report submitted',
            'report': report.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
