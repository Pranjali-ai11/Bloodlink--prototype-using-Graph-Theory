#!/usr/bin/env python
import os
from app import create_app, db
from app.models import User, Donor, BloodRequest, Report, Hospital, BloodBank, BloodInventory

app = create_app(os.environ.get('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    """Make models available in shell context"""
    return {
        'db': db,
        'User': User,
        'Donor': Donor,
        'BloodRequest': BloodRequest,
        'Report': Report,
        'Hospital': Hospital,
        'BloodBank': BloodBank,
        'BloodInventory': BloodInventory
    }

if __name__ == '__main__':
    app.run(
        debug=app.config['DEBUG'],
        host=os.environ.get('HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', 5000)),
    )
