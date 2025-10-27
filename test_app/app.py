"""
Test Flask Application for Foundation Platform Templates
This simple app demonstrates the usage of the foundation templates.
"""

from flask import Flask, render_template, redirect, url_for
import os
import sys

# Add parent directory to path to import foundation package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = Flask(__name__,
            template_folder='../foundation/templates',
            static_folder='../foundation/static',
            static_url_path='/static')

# Secret key for session management
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'


@app.route('/')
def index():
    """Home page - demonstrates base.html template"""
    return render_template('base.html')


@app.route('/login')
def login():
    """Login page - demonstrates login.html template"""
    return render_template('login.html')


@app.route('/pipeline')
def pipeline():
    """Pipeline page example"""
    return render_template('base.html')


@app.route('/reports')
def reports():
    """Reports page example"""
    return render_template('base.html')


@app.route('/receipts')
def receipts():
    """Receipts page example"""
    return render_template('base.html')


@app.route('/budgets')
def budgets():
    """Budgets page example"""
    return render_template('base.html')


@app.route('/auth/login')
def auth_login():
    """Mock authentication endpoint - redirects to home"""
    # In a real app, this would initiate Microsoft OAuth flow
    return redirect(url_for('index'))


@app.route('/auth/logout')
def auth_logout():
    """Mock logout endpoint - redirects to login"""
    # In a real app, this would clear session and logout
    return redirect(url_for('login'))


# Context processor to add user info to all templates
@app.context_processor
def inject_user():
    """Add user information to template context"""
    return {
        'user_name': 'Test User'
    }


if __name__ == '__main__':
    print("Starting Foundation Platform Test Server...")
    print("Visit http://localhost:5000/login to see the login page")
    print("Visit http://localhost:5000/ to see the main dashboard")
    print("\nPress Ctrl+C to stop the server\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
