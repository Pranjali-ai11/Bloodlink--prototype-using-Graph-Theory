import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.utils import geocode_address, find_nearby_donors
app = create_app("testing")
print('App OK, DB:', app.config.get('SQLALCHEMY_DATABASE_URI'))
print('Geocode empty ->', geocode_address(''))
print('find_nearby_donors callable ->', callable(find_nearby_donors))
