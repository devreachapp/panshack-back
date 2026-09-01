import os, requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Wallet,CryptoTransaction, BillPayment,GiftCardTrade

from app.wallet import bp as wallet_bp
from app.auth.views import token_required

PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY")

@wallet_bp.route('/wallet/balance', methods=['GET'])
@token_required
def get_balances(current_user):
    user_id = current_user.id
    wallets = Wallet.query.filter_by(user_id=user_id).all()
    res = {w.currency: float(w.balance) for w in wallets}
    return jsonify(res), 200

@wallet_bp.route('/withdraw', methods=['POST'])
@token_required
def withdraw_ngn(current_user):
    user_id = current_user.id
    data = request.json # bank_code, account_number, amount, pin
    
    user = User.query.get(user_id)
    if not user.check_pin(data['pin']):
        return jsonify({"error": "Invalid Transaction PIN"}), 401

    ngn_wallet = Wallet.query.filter_by(user_id=user_id, currency='NGN').first()
    if not ngn_wallet or ngn_wallet.balance < float(data['amount']):
        return jsonify({"error": "Insufficient NGN funds"}), 400

    # 1. Deduct Balance Immediately
    ngn_wallet.balance -= float(data['amount'])

    # 2. Initiate Paystack Payout (Recipient + Transfer)
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}", "Content-Type": "application/json"}
    
    # Create Recipient
    rec_payload = {"type": "nuban", "name": user.full_name, "account_number": data['account_number'], "bank_code": data['bank_code'], "currency": "NGN"}
    rec_res = requests.post("https://api.paystack.co/transferrecipient", json=rec_payload, headers=headers).json()
    
    recipient_code = rec_res['data']['recipient_code']

    # Execute Transfer
    transfer_payload = {"source": "balance", "amount": int(float(data['amount']) * 100), "recipient": recipient_code, "reason": "Jeroid Withdrawal"}
    transfer_res = requests.post("https://api.paystack.co/transfer", json=transfer_payload, headers=headers).json()

    db.session.commit()
    return jsonify({"message": "Transfer initiated", "details": transfer_res.get('data')}), 200


from flask import Blueprint, request, jsonify



RATES_TABLE = {
    "STEAM": {"PHYSICAL": 1100, "ECODE": 1050},
    "AMAZON": {"PHYSICAL": 1000, "ECODE": 950},
    "ITUNES": {"PHYSICAL": 980, "ECODE": 920}
}

@wallet_bp.route('/gift-cards/rates', methods=['GET'])
def get_rates():
    return jsonify(RATES_TABLE), 200

@wallet_bp.route('/sell', methods=['POST'])
@token_required
def sell_giftcard(current_user):
    user_id = current_user.id
    data = request.json # { card_name: 'STEAM', card_type: 'PHYSICAL', face_value: 100, image_url: '...' }

    rate = RATES_TABLE.get(data['card_name'], {}).get(data['card_type'], 0)
    if not rate:
        return jsonify({"error": "Invalid card selected"}), 400

    payout = float(data['face_value']) * rate

    trade = GiftCardTrade(
        user_id=user_id,
        card_name=data['card_name'],
        card_type=data['card_type'],
        face_value=data['face_value'],
        rate_per_unit=rate,
        payout_ngn=payout,
        card_image_url=data.get('image_url'),
        status='PENDING'
    )
    db.session.add(trade)
    db.session.commit()

    return jsonify({"message": "Trade submitted for verification", "payout_ngn": payout}), 201


import os, requests, uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity



@wallet_bp.route('/pay', methods=['POST'])
@token_required
def pay_bill(current_user):
    user_id = current_user.id
    data = request.json # service_type, biller_code, customer_id, amount, pin
    
    user = User.query.get(user_id)
    if not user.check_pin(data['pin']):
        return jsonify({"error": "Invalid PIN"}), 401

    ngn_wallet = Wallet.query.filter_by(user_id=user_id, currency='NGN').first()
    if ngn_wallet.balance < float(data['amount']):
        return jsonify({"error": "Insufficient NGN balance"}), 400

    reference = str(uuid.uuid4())
    
    # Execute Bill Purchase with Provider API (VTpass sample)
    vtpass_payload = {
        "request_id": reference,
        "serviceID": data['biller_code'],
        "billersCode": data['customer_id'],
        "amount": data['amount']
    }
    # Execute request to provider...

    # Deduct Balance & Save Log
    ngn_wallet.balance -= float(data['amount'])
    bill = BillPayment(
        user_id=user_id, service_type=data['service_type'], biller_code=data['biller_code'],
        customer_id=data['customer_id'], amount_ngn=data['amount'], reference=reference, status='SUCCESS'
    )
    db.session.add(bill)
    db.session.commit()

    return jsonify({"message": "Bill paid successfully", "reference": reference}), 200





@wallet_bp.route('/tatum', methods=['POST'])
def tatum_webhook():
    event = request.json
    
    # Process valid incoming deposit notification
    if event.get("type") in ["NATIVE", "TOKEN"]:
        address = event.get("address")
        amount = float(event.get("amount"))
        tx_hash = event.get("txId")

        wallet = Wallet.query.filter_by(deposit_address=address).first()
        if wallet:
            # Credit User Crypto Wallet
            wallet.balance += amount
            
            # Record Confirmed Crypto Transaction
            tx = CryptoTransaction(
                user_id=wallet.user_id, asset=wallet.currency, network='TRC20',
                tx_type='DEPOSIT', amount_crypto=amount, tx_hash=tx_hash, status='CONFIRMED'
            )
            db.session.add(tx)
            db.session.commit()

    return jsonify({"status": "acknowledged"}), 200

