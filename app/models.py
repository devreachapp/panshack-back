from datetime import datetime, timezone
import uuid
from .extensions import db
from flask import request
import base64
import os
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string

import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


def generate_uuid():
    return str(uuid.uuid4())

def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(8))

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    transaction_pin = db.Column(db.String(256), nullable=True)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    wallets = db.relationship('Wallet', backref='user', lazy=True)
    gift_card_trades = db.relationship('GiftCardTrade', backref='user', lazy=True)
    crypto_transactions = db.relationship('CryptoTransaction', backref='user', lazy=True)
    bill_payments = db.relationship('BillPayment', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_pin(self, pin):
        self.transaction_pin = generate_password_hash(str(pin))

    def check_pin(self, pin):
        return check_password_hash(self.transaction_pin, str(pin))

class Wallet(db.Model):
    __tablename__ = 'wallets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    currency = db.Column(db.String(10), nullable=False) # NGN, BTC, USDT_TRC20, ETH
    balance = db.Column(db.Numeric(18, 8), default=0.0)
    deposit_address = db.Column(db.String(128), nullable=True) # Tatum generated address
    derivation_index = db.Column(db.Integer, nullable=True) # xPub derivation index

    __table_args__ = (db.UniqueConstraint('user_id', 'currency', name='_user_currency_uc'),)

class GiftCardTrade(db.Model):
    __tablename__ = 'gift_card_trades'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_name = db.Column(db.String(50), nullable=False) # Amazon, Steam, iTunes
    card_type = db.Column(db.String(20), nullable=False) # Physical, E-Code
    face_value = db.Column(db.Numeric(12, 2), nullable=False)
    rate_per_unit = db.Column(db.Numeric(12, 2), nullable=False)
    payout_ngn = db.Column(db.Numeric(12, 2), nullable=False)
    card_image_url = db.Column(db.String(255), nullable=True)
    card_code = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='PENDING') # PENDING, APPROVED, REJECTED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CryptoTransaction(db.Model):
    __tablename__ = 'crypto_transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    asset = db.Column(db.String(10), nullable=False) # BTC, USDT
    network = db.Column(db.String(20), nullable=False) # TRC20, ERC20, BITCOIN
    tx_type = db.Column(db.String(20), nullable=False) # DEPOSIT, SWAP_SELL
    amount_crypto = db.Column(db.Numeric(18, 8), nullable=False)
    payout_ngn = db.Column(db.Numeric(12, 2), nullable=True)
    tx_hash = db.Column(db.String(128), unique=True, nullable=True)
    status = db.Column(db.String(20), default='PENDING') # PENDING, CONFIRMED, FAILED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BillPayment(db.Model):
    __tablename__ = 'bill_payments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_type = db.Column(db.String(50), nullable=False) # airtime, data, electricity, cable
    biller_code = db.Column(db.String(50), nullable=False) # mtn, dstv, ikeja-electric
    customer_id = db.Column(db.String(100), nullable=False) # Phone/Meter/Smartcard
    amount_ngn = db.Column(db.Numeric(12, 2), nullable=False)
    reference = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='SUCCESS') # SUCCESS, FAILED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)