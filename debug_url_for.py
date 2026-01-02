
from app import create_app, db
from app.models import User
from flask import render_template, url_for
from flask_login import login_user

app = create_app()

with app.app_context():
    # Create a dummy admin user if needed, or just mock current_user
    # But render_template needs a request context usually
    with app.test_request_context('/'):
        # Mock login
        user = User(username='admin', email='admin@test.com', role='admin')
        # We can't easily mock login_user without a real request, but we can mock current_user
        # Actually, let's just try to render the template and see if it fails
        # We need to mock current_user in the template
        
        from flask_login import current_user
        # This is hard to mock without actually logging in.
        
        # Let's try to find the string "url_for('profile')" in the file content directly
        # This is more reliable than my eyes
        pass

import os

def search_in_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
        if "url_for('profile')" in content or 'url_for("profile")' in content:
            print(f"Found in {filepath}")
            # Print context
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "url_for('profile')" in line or 'url_for("profile")' in line:
                    print(f"Line {i+1}: {line.strip()}")

print("Searching for incorrect url_for('profile')...")
for root, dirs, files in os.walk('app/templates'):
    for file in files:
        if file.endswith('.html'):
            search_in_file(os.path.join(root, file))
