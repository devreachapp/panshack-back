import os, requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Wallet, CryptoTransaction
from app.auth.views import token_required
from app.crypto import bp as crypto_bp





import os
import requests
from bip_utils import Bip39SeedGenerator, Bip44Changes, Bip84, Bip84Coins
from tronpy.keys import PrivateKey, to_base58check_address
from eth_account import Account
from flask import current_app, jsonify, request
from tronpy.keys import PrivateKey

TATUM_KEY = os.getenv("TATUM_API_KEY")
TATUM_URL = "https://api.tatum.io/v3"
HEADERS = {
    "x-api-key": TATUM_KEY,
    "accept": "application/json",
    "content-type": "application/json",
}

# Shared master mnemonic for local deterministic BTC derivation
# Replace this with a secure secret from your environment variables in production!
BTC_MASTER_MNEMONIC = os.getenv(
    "BTC_MASTER_MNEMONIC",
    "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
)

CHAIN_MAP = {
    # Bitcoin variations
    "BTC": "bitcoin",
    "BITCOIN": "bitcoin",
    # Tron / USDT variations
    "USDT_TRC20": "tron",
    "USDT": "tron",
    "TRX": "tron",
    "TRON": "tron",
    # Ethereum / ERC20 variations
    "ETH": "ethereum",
    "ETHEREUM": "ethereum",
    "USDT_ERC20": "ethereum",
}





@crypto_bp.route("/crypto/address", methods=["POST"])
@token_required
def get_or_generate_address(current_user):
    data = request.get_json() or {}

    raw_currency = (
        data.get("currency") or data.get("asset") or "USDT_TRC20"
    ).upper()
    user_id = current_user.id

    chain = CHAIN_MAP.get(raw_currency)
    if not chain:
        return jsonify({"error": f"Unsupported currency: {raw_currency}"}), 400

    canonical_currency = raw_currency
    if raw_currency in ["USDT", "TRX", "TRON"]:
        canonical_currency = "USDT_TRC20" if chain == "tron" else raw_currency

    # 1. Existing wallet lookup
    wallet = Wallet.query.filter_by(
        user_id=user_id, currency=canonical_currency
    ).first()
    if wallet and wallet.deposit_address:
        return (
            jsonify(
                {"address": wallet.deposit_address, "currency": canonical_currency}
            ),
            200,
        )

    try:
        address = None

        # 2. Local Address Derivation
        if chain == "tron":
            private_key = PrivateKey.random()
            # to_base58check_address safely handles bytes/address objects and returns a string starting with 'T'
            address = to_base58check_address(private_key.public_key.to_address())

        elif chain == "ethereum":
            acct = Account.create()
            address = acct.address

        elif chain == "bitcoin":
            # Derives a deterministic SegWit address (bc1q...) using user_id as index
            seed_bytes = Bip39SeedGenerator(BTC_MASTER_MNEMONIC).Generate()
            bip84_mst_ctx = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)
            bip84_acc_ctx = (
                bip84_mst_ctx.Purpose()
                .Coin()
                .Account(0)
                .Change(Bip44Changes.CHAIN_EXT)  # Fixed: Uses the Bip44Changes enum
                .AddressIndex(user_id)
            )
            address = bip84_acc_ctx.PublicKey().ToAddress()

        if not address:
            return jsonify({"error": "Failed to generate wallet address"}), 500

        # 3. Database Persistence
        if not wallet:
            wallet = Wallet(
                user_id=user_id,
                currency=canonical_currency,
                balance=0.0,
                deposit_address=address,
            )
            db.session.add(wallet)
        else:
            wallet.deposit_address = address

        db.session.commit()

        # 4. Tatum Webhook Subscription
        sub_payload = {
            "type": "ADDRESS_EVENT",
            "attr": {
                "address": address,
                "chain": chain.upper(),
                "url": f"{os.getenv('APP_BASE_URL')}/api/webhooks/tatum",
            },
        }
        sub_resp = requests.post(
            f"{TATUM_URL}/subscription",
            json=sub_payload,
            headers=HEADERS,
            timeout=10,
        )

        if sub_resp.status_code not in (200, 201):
            current_app.logger.error(
                f"Tatum webhook subscription failed [{sub_resp.status_code}]: {sub_resp.text}"
            )

        return jsonify({"address": address, "currency": canonical_currency}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating address: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@crypto_bp.route('/sell', methods=['POST'])
@token_required
def sell_crypto(current_user):
    user_id = current_user.id
    data = request.json # { currency: 'USDT_TRC20', amount: 100, pin: '1234' }
    
    wallet = Wallet.query.filter_by(user_id=user_id, currency=data['currency']).first()
    if not wallet or wallet.balance < float(data['amount']):
        return jsonify({"error": "Insufficient crypto balance"}), 400

    # Rate Engine (Example: 1 USDT = 1450 NGN)
    rate = 1450.00
    payout_ngn = float(data['amount']) * rate

    # Execute Internal Swap
    wallet.balance -= float(data['amount'])
    
    ngn_wallet = Wallet.query.filter_by(user_id=user_id, currency='NGN').first()
    ngn_wallet.balance += payout_ngn

    tx = CryptoTransaction(
        user_id=user_id, asset=data['currency'], network='TRC20',
        tx_type='SWAP_SELL', amount_crypto=data['amount'], payout_ngn=payout_ngn, status='CONFIRMED'
    )
    db.session.add(tx)
    db.session.commit()

    return jsonify({"message": "Crypto sold successfully", "ngn_credited": payout_ngn}), 200

@crypto_bp.route('/crypto/rates', methods=['GET'])
def get_crypto_rates():
    # Live exchange rates engine (USDT/BTC to NGN)
    rates = {
        "BTC": {"buy": 105000000.00, "sell": 102000000.00},
        "USDT": {"buy": 1520.00, "sell": 1490.00},
        "ETH": {"buy": 5200000.00, "sell": 5050000.00}
    }
    return jsonify(rates), 200