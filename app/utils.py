from math import radians, cos, sin, asin, sqrt
from .models import Donor, db
from .eligibility import is_donor_eligible
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderServiceError
import time

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  
    
    return c * r

def find_nearby_donors(blood_groups, lat, lon, radius_km):

    donors = Donor.query.filter(
        Donor.blood_group == blood_groups,
        Donor.is_available == True
    ).all()

    nearby = []

    for donor in donors:
        if not is_donor_eligible(donor)['eligible']:
            continue
        if donor.latitude is None or donor.longitude is None:
            continue
        distance = haversine_distance(lat, lon, donor.latitude, donor.longitude)

        if distance <= radius_km:
            nearby.append({
                "donor_id": donor.donor_id,
                "name": donor.user.name,
                "email": donor.user.email,
                "age": donor.user.age,
                "city": donor.city,
                "blood_group": donor.blood_group,
                "latitude": donor.latitude,
                "longitude": donor.longitude,
                "distance_km": distance,
                "is_available": donor.is_available,
                "is_verified": donor.user.is_verified,
                "last_donation_date": donor.last_donation_date.isoformat() if donor.last_donation_date else None,
                "donation_count": donor.donation_count or 0,
                "donations": donor.donation_count or 0,
            })

    return nearby


def geocode_address(address, retry=2, delay=1.0):
    """Geocode an address string to (latitude, longitude) using Nominatim.

    Returns tuple (lat, lon) or (None, None) on failure.
    """
    if not address:
        return None, None

    geolocator = Nominatim(user_agent="bloodlink_app")
    attempts = 0
    while attempts <= retry:
        try:
            loc = geolocator.geocode(address, timeout=10)
            if loc:
                return loc.latitude, loc.longitude
            return None, None
        except (GeocoderUnavailable, GeocoderServiceError):
            attempts += 1
            time.sleep(delay)
    return None, None

def calculate_donor_reliability_score(donor):
    """
    Calculate donor reliability score based on donation history
    
    Args:
        donor: Donor object
    
    Returns:
        Score between 0-100
    """
    base_score = 50
    donation_bonus = min((donor.donation_count / 10) * 30, 30)
    verified_bonus = 20 if donor.user.is_verified else 0
    
    score = base_score + donation_bonus + verified_bonus
    return min(score, 100)

def get_urgency_priority(urgency_level):
    """
    Get priority value for urgency level
    
    Args:
        urgency_level: 'critical', 'urgent', or 'normal'
    
    Returns:
        Priority value (higher = more urgent)
    """
    priority_map = {
        'critical': 3,
        'urgent': 2,
        'normal': 1
    }
    return priority_map.get(urgency_level, 1)

def get_compatible_blood_groups(patient_group, urgency=2):
    """
    AI blood compatibility logic.
    urgency: 1=low, 2=medium, 3=high
    """

    compatibility = {
        "O-": ["O-"],
        "O+": ["O+", "O-"],
        "A-": ["A-", "O-"],
        "A+": ["A+", "A-", "O+", "O-"],
        "B-": ["B-", "O-"],
        "B+": ["B+", "B-", "O+", "O-"],
        "AB-": ["AB-", "A-", "B-", "O-"],
        "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
    }

    base_groups = compatibility.get(patient_group, [patient_group])
    if urgency == 3:  
        return base_groups
    elif urgency == 2:  
        return base_groups[:3]
    else:  
        return [patient_group]

