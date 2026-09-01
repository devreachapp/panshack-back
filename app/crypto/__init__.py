from flask import Blueprint

bp = Blueprint('crypto', __name__)

from . import views