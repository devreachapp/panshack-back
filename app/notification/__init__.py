from flask import Blueprint

bp = Blueprint('notification', __name__)

from app.notification import views