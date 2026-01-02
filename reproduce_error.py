
from flask import Flask, render_template
from flask_login import LoginManager, UserMixin

app = Flask(__name__, template_folder='app/templates')
app.config['SECRET_KEY'] = 'secret'

# Mock Blueprints
from flask import Blueprint
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)

# Mock endpoints referenced in templates
@main_bp.route('/dashboard')
def dashboard(): return ''
@main_bp.route('/profile')
def profile(): return ''
@main_bp.route('/admin/users')
def admin_users(): return ''
@main_bp.route('/admin/games')
def admin_games(): return ''
@main_bp.route('/admin/reports')
def admin_reports(): return ''
@main_bp.route('/admin/messages')
def admin_messages(): return ''
@main_bp.route('/manage_patients')
def manage_patients(): return ''
@main_bp.route('/games')
def games_list(): return ''
@main_bp.route('/analytics')
def analytics(): return ''
@main_bp.route('/sessions')
def sessions(): return ''
@main_bp.route('/reports')
def reports(): return ''
@main_bp.route('/messages')
def messages_list(): return ''
@main_bp.route('/admin/dashboard')
def admin_dashboard(): return ''
@auth_bp.route('/logout')
def logout(): return ''

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, role):
        self.id = 1
        self.role = role
        self.username = 'admin'
        self.email = 'admin@test.com'

@login_manager.user_loader
def load_user(user_id):
    return User('admin')

# Mock overview data
overview = {
    'therapists': 10,
    'patients': 20,
    'sessions_total': 100,
    'avg_accuracy': 85.5
}

if __name__ == '__main__':
    with app.app_context():
        with app.test_request_context():
            # Login as admin
            from flask_login import login_user
            user = User('admin')
            login_user(user)
            
            try:
                print("Rendering admin/dashboard.html...")
                render_template('admin/dashboard.html', overview=overview, active_page='admin_dashboard')
                print("Success!")
            except Exception as e:
                print(f"CAUGHT ERROR: {e}")
