"""
Investment Portfolio Tracker - Flask Application
A comprehensive web application to track and manage investment portfolios.
Features: CRUD operations, interest calculation, portfolio analytics, and more.

Author: SAM BaQuibillah Sagor
GitHub: https://github.com/sksagor
Version: 1.0.0
"""

# ============================================================================
# IMPORT SECTION
# ============================================================================
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta


# ============================================================================
# FLASK APPLICATION CONFIGURATION
# ============================================================================

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'  # For flash messages
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///investment.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy ORM
db = SQLAlchemy(app)


# ============================================================================
# DATABASE MODELS
# ============================================================================

class Investment(db.Model):
    """
    Investment Model representing a single investment entry in the portfolio.
    
    Attributes:
        id (int): Primary key, unique identifier
        title (str): Investment title/name
        description (str): Detailed description
        amount (float): Investment amount in BDT
        interest_rate (float): Annual interest rate in percentage
        investment_date (datetime): Date when investment was made
        maturity_date (datetime): Date when investment matures
        investment_type (str): Type of investment (Fixed Deposit, Stocks, etc.)
        fd_type (str): Fixed Deposit subtype (FSP, BSP, or custom)
    """
    
    # Table columns
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, default=0.0)
    investment_date = db.Column(db.DateTime, default=datetime.utcnow)
    maturity_date = db.Column(db.DateTime, nullable=False)
    investment_type = db.Column(db.String(50), default="Fixed Deposit")
    fd_type = db.Column(db.String(50), default="")  # FD subtype: FSP, BSP, or custom
    
    # ------------------------------------------------------------------------
    # MAGIC METHODS
    # ------------------------------------------------------------------------
    
    def __repr__(self):
        """
        String representation of the Investment object.
        Used for debugging and logging.
        """
        fd_type_display = f" ({self.fd_type})" if self.fd_type and self.investment_type == "Fixed Deposit" else ""
        return f"{self.id} - {self.title}{fd_type_display} - ৳{self.amount}"
    
    # ------------------------------------------------------------------------
    # BUSINESS LOGIC METHODS
    # ------------------------------------------------------------------------
    
    def calculate_maturity_amount(self):
        """
        Calculate the maturity amount including interest.
        
        Returns:
            float: Maturity amount after applying interest
        """
        # Return principal if no interest
        if self.interest_rate <= 0:
            return self.amount
        
        # Calculate time difference in years
        time_diff = (self.maturity_date - self.investment_date).days / 365.25
        
        # Calculate simple interest
        interest = self.amount * (self.interest_rate / 100) * time_diff
        
        # Return total amount rounded to 2 decimal places
        return round(self.amount + interest, 2)
    
    def days_remaining(self):
        """
        Calculate days remaining until maturity.
        
        Returns:
            int: Number of days remaining, 0 if already matured
        """
        today = datetime.utcnow()
        if self.maturity_date > today:
            return (self.maturity_date - today).days
        return 0
    
    def get_display_type(self):
        """
        Get formatted display string for investment type.
        Includes FD subtype for Fixed Deposits.
        
        Returns:
            str: Formatted investment type for display
        """
        if self.investment_type == "Fixed Deposit" and self.fd_type:
            return f"FD - {self.fd_type}"
        return self.investment_type
    
    # ------------------------------------------------------------------------
    # FORMATTING METHODS
    # ------------------------------------------------------------------------
    
    def format_amount(self):
        """
        Format amount with BDT symbol and proper decimal handling.
        Removes .00 for whole numbers.
        
        Returns:
            str: Formatted amount string
        """
        if self.amount.is_integer():
            return f"৳{int(self.amount):,}"
        return f"৳{self.amount:,.2f}"
    
    def format_maturity_amount(self):
        """
        Format maturity amount with BDT symbol and proper decimal handling.
        Removes .00 for whole numbers.
        
        Returns:
            str: Formatted maturity amount string
        """
        maturity = self.calculate_maturity_amount()
        if maturity.is_integer():
            return f"৳{int(maturity):,}"
        return f"৳{maturity:,.2f}"


# ============================================================================
# JINJA2 CUSTOM FILTERS
# ============================================================================

def format_currency(value):
    """
    Custom Jinja2 filter to format currency values.
    Formats with BDT symbol and removes .00 for whole numbers.
    
    Args:
        value: Numeric value to format
        
    Returns:
        str: Formatted currency string
    """
    try:
        # Convert to float and check if it's a whole number
        float_value = float(value)
        if float_value.is_integer():
            return f"৳{int(float_value):,}"
        return f"৳{float_value:,.2f}"
    except (ValueError, TypeError):
        # Return original value with symbol if conversion fails
        return f"৳{value}"

# Register custom filter with Jinja2 environment
app.jinja_env.filters['currency'] = format_currency


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_float_conversion(value, default=0.0):
    """
    Safely convert a string to float, returning default if conversion fails.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        float: Converted value or default
    """
    try:
        if value is None or value.strip() == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_portfolio_totals(investments):
    """
    Calculate portfolio totals and analytics.
    
    Args:
        investments: List of Investment objects
        
    Returns:
        tuple: (total_invested, total_maturity_value, total_profit, investments_by_type)
    """
    total_invested = sum(inv.amount for inv in investments)
    total_maturity_value = sum(inv.calculate_maturity_amount() for inv in investments)
    total_profit = total_maturity_value - total_invested
    
    # Group investments by type for analytics
    investments_by_type = {}
    for inv in investments:
        display_type = inv.get_display_type()
        if display_type not in investments_by_type:
            investments_by_type[display_type] = 0
        investments_by_type[display_type] += inv.amount
    
    return total_invested, total_maturity_value, total_profit, investments_by_type


def parse_fd_type(investment_type, fd_type_option, fd_type_other):
    """
    Parse Fixed Deposit type from form data.
    
    Args:
        investment_type: Selected investment type
        fd_type_option: Selected FD type option
        fd_type_other: Custom FD type input
        
    Returns:
        str: FD type string
    """
    fd_type = ""
    if investment_type == "Fixed Deposit":
        if fd_type_option == "other":
            fd_type = fd_type_other.strip() if fd_type_other else ""
        elif fd_type_option:
            fd_type = fd_type_option
    return fd_type


def validate_form_data(form_data):
    """
    Validate form data before processing.
    
    Args:
        form_data: Flask request.form object
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check required fields
    required_fields = ['title', 'amount', 'investment_date', 'maturity_date']
    for field in required_fields:
        if not form_data.get(field):
            return False, f"{field.replace('_', ' ').title()} is required."
    
    # Validate amount
    amount_str = form_data.get('amount')
    if amount_str:
        try:
            amount = float(amount_str)
            if amount <= 0:
                return False, "Amount must be greater than 0."
        except ValueError:
            return False, "Amount must be a valid number."
    
    # Validate interest rate
    interest_rate_str = form_data.get('interest_rate', '0')
    if interest_rate_str:
        try:
            interest_rate = float(interest_rate_str)
            if interest_rate < 0 or interest_rate > 100:
                return False, "Interest rate must be between 0 and 100."
        except ValueError:
            return False, "Interest rate must be a valid number."
    
    # Validate dates
    investment_date_str = form_data.get('investment_date')
    maturity_date_str = form_data.get('maturity_date')
    
    try:
        investment_date = datetime.strptime(investment_date_str, '%Y-%m-%d')
        maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d')
        
        if maturity_date <= investment_date:
            return False, "Maturity date must be after investment date."
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD format."
    
    return True, ""


# ============================================================================
# ROUTES AND VIEW FUNCTIONS
# ============================================================================

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Homepage route - Display all investments and handle new investment creation.
    
    GET: Display investment portfolio with analytics
    POST: Create new investment entry
    
    Returns:
        Rendered template or redirect
    """
    
    # Handle POST request (Create new investment)
    if request.method == "POST":
        # Validate form data
        is_valid, error_message = validate_form_data(request.form)
        if not is_valid:
            flash(f"Error: {error_message}", "danger")
            return redirect('/')
        
        # Extract form data with safe conversion
        title = request.form.get('title')
        description = request.form.get('description', '')
        amount = safe_float_conversion(request.form.get('amount'))
        interest_rate = safe_float_conversion(request.form.get('interest_rate'), 0.0)
        investment_type = request.form.get('investment_type', 'Fixed Deposit')
        investment_date_str = request.form.get('investment_date')
        maturity_date_str = request.form.get('maturity_date')
        
        # Parse FD type
        fd_type = parse_fd_type(
            investment_type,
            request.form.get('fd_type', ''),
            request.form.get('fd_type_other', '')
        )
        
        try:
            # Convert string dates to datetime objects
            investment_date = datetime.strptime(investment_date_str, '%Y-%m-%d')
            maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d')
            
            # Create new investment object
            investment = Investment(
                title=title,
                description=description,
                amount=amount,
                interest_rate=interest_rate,
                investment_type=investment_type,
                investment_date=investment_date,
                maturity_date=maturity_date,
                fd_type=fd_type
            )
            
            # Save to database
            db.session.add(investment)
            db.session.commit()
            
            flash("Investment added successfully!", "success")
            
        except ValueError as e:
            flash(f"Error processing dates: {str(e)}", "danger")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
        
        # Redirect to homepage (PRG pattern)
        return redirect('/')
    
    # Handle GET request (Display all investments)
    all_investments = Investment.query.all()
    
    # Calculate portfolio totals
    total_invested, total_maturity_value, total_profit, investments_by_type = \
        calculate_portfolio_totals(all_investments)
    
    # Render template with data
    return render_template(
        'index.html',
        investments=all_investments,
        total_invested=total_invested,
        total_maturity_value=total_maturity_value,
        total_profit=total_profit,
        investments_by_type=investments_by_type,
        datetime=datetime,
        timedelta=timedelta
    )


@app.route("/delete/<int:id>")
def delete_investment(id):
    """
    Delete an investment by ID.
    
    Args:
        id: Investment ID to delete
        
    Returns:
        Redirect to homepage
    """
    try:
        # Find investment by ID
        investment = Investment.query.get_or_404(id)
        
        # Delete if exists
        db.session.delete(investment)
        db.session.commit()
        
        flash("Investment deleted successfully!", "success")
        
    except Exception as e:
        flash(f"Error deleting investment: {str(e)}", "danger")
    
    return redirect('/')


@app.route("/update/<int:id>", methods=["GET", "POST"])
def update_investment(id):
    """
    Update an existing investment.
    
    GET: Display edit form with current investment data
    POST: Update investment with new data
    
    Args:
        id: Investment ID to update
        
    Returns:
        Rendered template or redirect
    """
    
    try:
        # Get investment to update
        investment = Investment.query.get_or_404(id)
        
    except Exception as e:
        flash(f"Investment not found: {str(e)}", "danger")
        return redirect('/')
    
    # Handle POST request (Update investment)
    if request.method == "POST":
        # Validate form data
        is_valid, error_message = validate_form_data(request.form)
        if not is_valid:
            flash(f"Error: {error_message}", "danger")
            return redirect(f'/update/{id}')
        
        try:
            # Update investment attributes with safe conversion
            investment.title = request.form.get('title')
            investment.description = request.form.get('description', '')
            investment.amount = safe_float_conversion(request.form.get('amount'))
            investment.interest_rate = safe_float_conversion(request.form.get('interest_rate'), 0.0)
            investment.investment_type = request.form.get('investment_type', 'Fixed Deposit')
            investment_date_str = request.form.get('investment_date')
            maturity_date_str = request.form.get('maturity_date')
            
            # Update FD type
            if investment.investment_type == "Fixed Deposit":
                fd_type_option = request.form.get('fd_type', '')
                if fd_type_option == "other":
                    investment.fd_type = request.form.get('fd_type_other', '').strip()
                elif fd_type_option:
                    investment.fd_type = fd_type_option
                else:
                    investment.fd_type = ""
            else:
                investment.fd_type = ""
            
            # Update dates
            investment.investment_date = datetime.strptime(investment_date_str, '%Y-%m-%d')
            investment.maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d')
            
            # Commit changes
            db.session.commit()
            
            flash("Investment updated successfully!", "success")
            
        except ValueError as e:
            flash(f"Error processing data: {str(e)}", "danger")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
        
        return redirect('/')
    
    # Handle GET request (Display edit form)
    all_investments = Investment.query.all()
    
    # Calculate portfolio totals
    total_invested, total_maturity_value, total_profit, investments_by_type = \
        calculate_portfolio_totals(all_investments)
    
    # Render template with current investment data
    return render_template(
        'index.html',
        investment=investment,
        investments=all_investments,
        total_invested=total_invested,
        total_maturity_value=total_maturity_value,
        total_profit=total_profit,
        investments_by_type=investments_by_type,
        datetime=datetime,
        timedelta=timedelta
    )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    flash("Page not found.", "warning")
    return redirect('/')


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    flash("An internal error occurred. Please try again.", "danger")
    return redirect('/')


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

def initialize_database():
    """
    Initialize database tables on application startup.
    """
    with app.app_context():
        try:
            db.create_all()
            print("✅ Investment Portfolio Tracker Database Initialized!")
            print("✅ Tables created successfully!")
        except Exception as e:
            print(f"⚠️  Database initialization error: {e}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """
    Main entry point for the Flask application.
    """
    
    # Initialize database
    initialize_database()
    
    # Run Flask development server
    print("🚀 Starting Investment Portfolio Tracker...")
    print("📊 Visit: http://127.0.0.1:5001")
    print("⚡ Debug mode: ON")
    print("🔒 Secret key set for flash messages")
    print("=" * 50)
    
    app.run(
        debug=True,
        port=5001,
        host='127.0.0.1'
    )