from flask import Blueprint, render_template
from flask_login import login_required
from flask_app.models import Account

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/view_reports/<int:account_id>', methods=['GET'])
@login_required
def view_reports(account_id):
    """Displays investment reports and analytics for the selected account."""
    account = Account.query.get_or_404(account_id)
    return render_template('reports.html', account=account)