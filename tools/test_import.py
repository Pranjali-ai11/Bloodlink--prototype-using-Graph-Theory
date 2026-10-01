from app import create_app
from app.utils import geocode_address, find_nearby_donors
app = create_app()
print('App OK, DB:', app.config.get('SQLALCHEMY_DATABASE_URI'))
print('Geocode empty ->', geocode_address(''))
print('find_nearby_donors callable ->', callable(find_nearby_donors))
