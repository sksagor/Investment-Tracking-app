"""
Investment Portfolio Tracker - Flask Application
Author: SAM BaQuibillah Sagor
Version: 2.0.2 (Robust Auth Fix)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import functools

# ============================================================================
# FLASK APPLICATION CONFIGURATION
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///investment.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    investments = db.relationship('Investment', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, default=0.0)
    investment_date = db.Column(db.DateTime, default=datetime.utcnow)
    maturity_date = db.Column(db.DateTime, nullable=False)
    investment_type = db.Column(db.String(50), default="Fixed Deposit")
    fd_type = db.Column(db.String(50), default="")

    def calculate_maturity_amount(self):
        if self.interest_rate <= 0:
            return self.amount
        time_diff = (self.maturity_date - self.investment_date).days / 365.25
        interest = self.amount * (self.interest_rate / 100) * time_diff
        return round(self.amount + interest, 2)
    
    def days_remaining(self):
        today = datetime.utcnow()
        if self.maturity_date > today:
            return (self.maturity_date - today).days
        return 0
    
    def get_display_type(self):
        if self.investment_type == "Fixed Deposit" and self.fd_type:
            return f"FD - {self.fd_type}"
        return self.investment_type

# ============================================================================
# AUTHENTICATION HELPERS (FIXED)
# ============================================================================

def get_current_user():
    """Safely retrieves the user from DB or returns None if not found/logged out."""
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        user = get_current_user()
        if user is None:
            # If session exists but user is not in DB, clear the session
            session.clear()
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# ============================================================================
# HELPERS & FILTERS
# ============================================================================

@app.template_filter('currency')
def format_currency(value):
    try:
        return f"৳{float(value):,.2f}"
    except (ValueError, TypeError):
        return f"৳{value}"

def calculate_portfolio_totals(investments):
    total_invested = sum(inv.amount for inv in investments)
    total_maturity_value = sum(inv.calculate_maturity_amount() for inv in investments)
    total_profit = total_maturity_value - total_invested
    return total_invested, total_maturity_value, total_profit

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or Email already exists.', 'danger')
        else:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username_or_email')
        password = request.form.get('password')
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
        
        if user and user.check_password(password):
            session.clear() # Clear any old/stale session data
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        flash('Invalid username/email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user = get_current_user()
    if request.method == "POST":
        try:
            inv = Investment(
                user_id=user.id,
                title=request.form.get('title'),
                amount=float(request.form.get('amount')),
                interest_rate=float(request.form.get('interest_rate', 0)),
                investment_date=datetime.strptime(request.form.get('investment_date'), '%Y-%m-%d'),
                maturity_date=datetime.strptime(request.form.get('maturity_date'), '%Y-%m-%d'),
                investment_type=request.form.get('investment_type'),
                fd_type=request.form.get('fd_type_other') if request.form.get('fd_type') == 'other' else request.form.get('fd_type', ''),
                description=request.form.get('description', '')
            )
            db.session.add(inv)
            db.session.commit()
            flash("Investment added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

    investments = Investment.query.filter_by(user_id=user.id).all()
    total_invested, total_maturity, total_profit = calculate_portfolio_totals(investments)
    return render_template('index.html', investments=investments, 
                           total_invested=total_invested, 
                           total_maturity_value=total_maturity, 
                           total_profit=total_profit)

@app.route("/update/<int:id>", methods=["GET", "POST"])
@login_required
def update_investment(id):
    user = get_current_user()
    inv = Investment.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    if request.method == "POST":
        inv.title = request.form.get('title')
        inv.amount = float(request.form.get('amount'))
        inv.interest_rate = float(request.form.get('interest_rate', 0))
        inv.investment_date = datetime.strptime(request.form.get('investment_date'), '%Y-%m-%d')
        inv.maturity_date = datetime.strptime(request.form.get('maturity_date'), '%Y-%m-%d')
        inv.investment_type = request.form.get('investment_type')
        inv.fd_type = request.form.get('fd_type_other') if request.form.get('fd_type') == 'other' else request.form.get('fd_type', '')
        inv.description = request.form.get('description', '')
        
        db.session.commit()
        flash("Updated successfully!", "success")
        return redirect(url_for('dashboard'))

    investments = Investment.query.filter_by(user_id=user.id).all()
    total_invested, total_maturity, total_profit = calculate_portfolio_totals(investments)
    return render_template('index.html', investment=inv, investments=investments, 
                           total_invested=total_invested, 
                           total_maturity_value=total_maturity, 
                           total_profit=total_profit)

@app.route("/delete/<int:id>")
@login_required
def delete_investment(id):
    user = get_current_user()
    inv = Investment.query.filter_by(id=id, user_id=user.id).first_or_404()
    db.session.delete(inv)
    db.session.commit()
    flash("Investment deleted.", "info")
    return redirect(url_for('dashboard'))

@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    return render_template('profile.html', user=user, investment_count=len(user.investments))


@app.context_processor
def inject_globals():
    now = datetime.utcnow()
    return {
        'datetime': datetime,
        'timedelta': timedelta,
        'current_year': now.strftime('%Y'),
        'today_str': now.strftime('%Y-%m-%d'),
        'next_year_str': (now + timedelta(days=365)).strftime('%Y-%m-%d')
    }
# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)