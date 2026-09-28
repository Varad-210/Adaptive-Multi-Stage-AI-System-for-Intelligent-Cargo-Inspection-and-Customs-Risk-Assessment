from flask import Blueprint, render_template, request
from auth.decorators import login_required
from auth.models import get_analytics_overview, get_trend_data

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/historical-analytics')
@login_required
def historical_analytics():
    overview = get_analytics_overview()
    return render_template('historical_analytics.html', overview=overview)
