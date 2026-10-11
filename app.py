import os
import re
import uuid
import hmac
import hashlib
import secrets
import smtplib
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps

from bson import ObjectId  # pyright: ignore[reportMissingImports]
from flask import Flask, jsonify, redirect, render_template, request, session, url_for  # pyright: ignore[reportMissingImports]
from pymongo import MongoClient  # pyright: ignore[reportMissingImports]
from pymongo.errors import DuplicateKeyError  # pyright: ignore[reportMissingImports]
from werkzeug.security import check_password_hash, generate_password_hash  # pyright: ignore[reportMissingImports]
try:
    from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mini-fresh-basket-change-this-secret")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
DB_NAME = os.getenv("DB_NAME", "mini_fresh_basket")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "pratiksha3767@gmail.com").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Pratiksha@gmail123")
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip()
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "").strip()
MAIL_FROM = os.getenv("MAIL_FROM", MAIL_USERNAME).strip()

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
users = db.users
products = db.products
orders = db.orders

users.create_index("email", unique=True)
products.create_index("name")
orders.create_index("user_id")
orders.create_index("created_at")

PAYMENT_METHODS = {"COD", "UPI", "CARD"}
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
UPLOAD_DIR = Path(app.root_path) / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ORDER_STATUSES = {"Placed", "Packed", "Out for Delivery", "Delivered", "Cancelled"}


def money(value):
    return round(float(value), 2)


def json_product(p):
    return {
        "id": str(p["_id"]),
        "name": p["name"],
        "category": p["category"],
        "price": money(p["price"]),
        "unit": p.get("unit", "1 pc"),
        "stock": int(p.get("stock", 0)),
        "image": p.get("image"),
        "description": p.get("description", ""),
    }


def serialize_datetime(value):
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id") or session.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin login required"}), 403
        return fn(*args, **kwargs)

    return wrapper


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"success": False, "message": "Please login first"}), 401
        return fn(*args, **kwargs)

    return wrapper


def current_user():
    if not session.get("user_id"):
        return None
    try:
        return users.find_one({"_id": ObjectId(session["user_id"])})
    except Exception:
        return None


def validate_customer_details(data):
    name = str(data.get("name", "")).strip()
    phone = re.sub(r"\s+", "", str(data.get("phone", "")))
    email = str(data.get("email", "")).strip().lower()
    address = str(data.get("address", "")).strip()
    city = str(data.get("city", "")).strip()
    pincode = re.sub(r"\s+", "", str(data.get("pincode", "")))

    if not 2 <= len(name) <= 60:
        return None, "Full name must be 2-60 characters"
    if not re.fullmatch(r"[6-9]\d{9}", phone):
        return None, "Enter a valid 10-digit Indian mobile number"
    if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return None, "Enter a valid email address"
    if len(address) < 10 or len(address) > 250:
        return None, "Address must be 10-250 characters"
    if len(city) < 2 or len(city) > 60:
        return None, "Enter a valid city"
    if not re.fullmatch(r"[1-9]\d{5}", pincode):
        return None, "Enter a valid 6-digit PIN code"

    return {
        "name": name,
        "phone": phone,
        "email": email,
        "address": address,
        "city": city,
        "pincode": pincode,
    }, None


def seed_data():
    # Local student-project admin account; change ADMIN_PASSWORD in .env before deployment.
    users.update_one(
        {"email": ADMIN_EMAIL},
        {"$set": {"name": "Mini Fresh Basket Admin", "email": ADMIN_EMAIL,
                   "password": generate_password_hash(ADMIN_PASSWORD), "role": "admin"},
         "$setOnInsert": {"phone": "", "created_at": datetime.utcnow()}},
        upsert=True,
    )

    if products.count_documents({}) == 0:
        data = [
            ("Fresh Apples", "Fruits", 120, "1 kg", 50, "🍎"),
            ("Bananas", "Fruits", 55, "1 dozen", 70, "🍌"),
            ("Mangoes", "Fruits", 150, "1 kg", 40, "🥭"),
            ("Oranges", "Fruits", 90, "1 kg", 45, "🍊"),
            ("Tomatoes", "Vegetables", 45, "1 kg", 80, "🍅"),
            ("Potatoes", "Vegetables", 35, "1 kg", 100, "🥔"),
            ("Onions", "Vegetables", 40, "1 kg", 90, "🧅"),
            ("Carrots", "Vegetables", 60, "1 kg", 60, "🥕"),
            ("Milk", "Dairy", 32, "500 ml", 100, "🥛"),
            ("Curd", "Dairy", 45, "400 g", 70, "🥣"),
            ("Paneer", "Dairy", 110, "200 g", 40, "🧀"),
            ("Bread", "Bakery", 40, "400 g", 60, "🍞"),
            ("Eggs", "Eggs", 75, "6 pcs", 80, "🥚"),
            ("Basmati Rice", "Staples", 220, "5 kg", 35, "🍚"),
            ("Wheat Atta", "Staples", 240, "5 kg", 40, "🌾"),
            ("Cooking Oil", "Staples", 150, "1 L", 50, "🫗"),
            ("Tea", "Beverages", 180, "500 g", 30, "🍵"),
            ("Coffee", "Beverages", 260, "200 g", 25, "☕"),
            ("Biscuits", "Snacks", 30, "250 g", 90, "🍪"),
            ("Chips", "Snacks", 20, "1 pack", 100, "🥔"),
        ]
        products.insert_many(
            [
                {
                    "name": n,
                    "category": c,
                    "price": price,
                    "unit": u,
                    "stock": stock,
                    "image": img,
                    "description": f"Fresh {n.lower()} for your daily needs.",
                }
                for n, c, price, u, stock, img in data
            ]
        )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")


@app.route("/cart")
def cart_page():
    return render_template("cart.html")


@app.route("/checkout")
def checkout_page():
    return render_template("checkout.html")


@app.route("/invoice/<order_id>")
def invoice_page(order_id):
    return render_template("invoice.html", order_id=order_id)


@app.route("/admin")
def admin_page():
    if session.get("role") != "admin":
        return redirect(url_for("login_page"))
    return render_template("admin.html")


@app.get("/api/me")
def me():
    u = current_user()
    if not u:
        session.clear()
        return jsonify({"logged_in": False})
    return jsonify(
        {
            "logged_in": True,
            "user": {
                "id": str(u["_id"]),
                "name": u["name"],
                "email": u["email"],
                "phone": u.get("phone", ""),
                "role": u["role"],
            },
        }
    )


@app.get("/api/products")
def get_products():
    category = request.args.get("category", "").strip()
    q = request.args.get("q", "").strip()
    query = {}
    if category and category != "All":
        query["category"] = category
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
        ]
    return jsonify([json_product(p) for p in products.find(query).sort("name", 1)])


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone = re.sub(r"\s+", "", str(data.get("phone", "")))
    password = data.get("password", "")

    if not 2 <= len(name) <= 50:
        return jsonify({"success": False, "message": "Name must be 2-50 characters"}), 400
    if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"success": False, "message": "Enter a valid email"}), 400
    if not re.fullmatch(r"[6-9]\d{9}", phone):
        return jsonify({"success": False, "message": "Enter a valid 10-digit Indian mobile number"}), 400
    if (
        len(password) < 8
        or not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"\d", password)
    ):
        return jsonify(
            {
                "success": False,
                "message": "Password must be 8+ characters with uppercase, lowercase and number",
            }
        ), 400

    try:
        r = users.insert_one(
            {
                "name": name,
                "email": email,
                "phone": phone,
                "password": generate_password_hash(password),
                "role": "customer",
                "created_at": datetime.utcnow(),
            }
        )
    except DuplicateKeyError:
        return jsonify({"success": False, "message": "Email is already registered"}), 409

    session["user_id"] = str(r.inserted_id)
    session["role"] = "customer"
    return jsonify({"success": True, "message": "Registration successful"})


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    u = users.find_one({"email": email})
    if not u or not check_password_hash(u["password"], password):
        return jsonify({"success": False, "message": "Invalid email or password"}), 401
    session["user_id"] = str(u["_id"])
    session["role"] = u["role"]
    return jsonify({"success": True, "role": u["role"], "message": "Login successful"})


def send_reset_otp(recipient, otp):
    if not (MAIL_USERNAME and MAIL_PASSWORD and MAIL_FROM):
        raise RuntimeError("Email is not configured. Add MAIL_USERNAME and MAIL_PASSWORD in .env.")
    msg = EmailMessage()
    msg["Subject"] = "Mini Fresh Basket password reset code"
    msg["From"] = MAIL_FROM
    msg["To"] = recipient
    msg.set_content(
        f"Your Mini Fresh Basket password reset OTP is: {otp}\n\n"
        "It expires in 10 minutes. If you did not request this, ignore this email. "
        "Never share this code with anyone."
    )
    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
        smtp.send_message(msg)


@app.post("/api/forgot-password/request")
def forgot_password_request():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"success": False, "message": "Enter a valid email address."}), 400
    user = users.find_one({"email": email})
    # Same response whether or not the account exists, to avoid exposing registered emails.
    if user:
        otp = f"{secrets.randbelow(1_000_000):06d}"
        users.update_one({"_id": user["_id"]}, {"$set": {
            "reset_otp_hash": generate_password_hash(otp),
            "reset_otp_expires": datetime.utcnow() + timedelta(minutes=10),
            "reset_otp_attempts": 0,
        }})
        try:
            send_reset_otp(email, otp)
        except Exception:
            app.logger.exception("Password reset email could not be sent")
            users.update_one({"_id": user["_id"]}, {"$unset": {"reset_otp_hash": "", "reset_otp_expires": ""}})
            return jsonify({"success": False, "message": "Email could not be sent. Check Gmail SMTP settings in .env."}), 503
    return jsonify({"success": True, "message": "If this email is registered, a 6-digit OTP has been sent. Check your inbox and spam folder."})


@app.post("/api/forgot-password/reset")
def forgot_password_reset():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    password = str(data.get("password", ""))
    if not re.fullmatch(r"\d{6}", otp):
        return jsonify({"success": False, "message": "Enter the 6-digit OTP."}), 400
    if (len(password) < 8 or not re.search(r"[A-Z]", password) or
            not re.search(r"[a-z]", password) or not re.search(r"\d", password)):
        return jsonify({"success": False, "message": "Password needs 8+ characters, uppercase, lowercase and a number."}), 400
    user = users.find_one({"email": email, "reset_otp_hash": {"$exists": True}})
    if not user or user.get("reset_otp_expires", datetime.min) < datetime.utcnow():
        return jsonify({"success": False, "message": "OTP is invalid or expired. Request a new one."}), 400
    if int(user.get("reset_otp_attempts", 0)) >= 5:
        return jsonify({"success": False, "message": "Too many attempts. Request a new OTP."}), 429
    if not check_password_hash(user["reset_otp_hash"], otp):
        users.update_one({"_id": user["_id"]}, {"$inc": {"reset_otp_attempts": 1}})
        return jsonify({"success": False, "message": "Incorrect OTP. Please try again."}), 400
    users.update_one({"_id": user["_id"]}, {"$set": {"password": generate_password_hash(password)},
        "$unset": {"reset_otp_hash": "", "reset_otp_expires": "", "reset_otp_attempts": ""}})
    return jsonify({"success": True, "message": "Password reset successfully. You can now log in."})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"success": True})


@app.get("/api/checkout/profile")
@login_required
def checkout_profile():
    u = current_user()
    return jsonify(
        {
            "success": True,
            "customer": {
                "name": u.get("name", ""),
                "email": u.get("email", ""),
                "phone": u.get("phone", ""),
                "address": u.get("address", ""),
                "city": u.get("city", ""),
                "pincode": u.get("pincode", ""),
            },
        }
    )


@app.post("/api/payment/create-order")
@login_required
def create_payment_order():
    if not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET):
        return jsonify({"success": False, "message": "Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env."}), 503
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        return jsonify({"success": False, "message": "Your cart is empty."}), 400
    customer, error = validate_customer_details(data)
    if error:
        return jsonify({"success": False, "message": error}), 400
    subtotal = 0.0
    for item in items:
        try:
            pid, qty = ObjectId(item.get("id")), int(item.get("qty", 0))
        except Exception:
            return jsonify({"success": False, "message": "Invalid product in cart."}), 400
        product = products.find_one({"_id": pid})
        if not product or qty < 1 or qty > int(product.get("stock", 0)):
            return jsonify({"success": False, "message": f"Stock changed for {product['name'] if product else 'a product'}. Please update your cart."}), 400
        subtotal += money(product["price"]) * qty
    total = money(subtotal + (0 if subtotal >= 499 else 30))
    try:
        import razorpay  # pyright: ignore[reportMissingImports]
    except ImportError:
        app.logger.exception("Razorpay SDK is not installed")
        return jsonify({"success": False, "message": "Payment service is unavailable. Install the Razorpay SDK and try again."}), 503
    try:
        gateway = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = gateway.order.create({"amount": int(round(total * 100)), "currency": "INR", "receipt": f"mfb_{uuid.uuid4().hex[:18]}", "notes": {"customer_email": customer["email"]}})
    except Exception:
        app.logger.exception("Razorpay order creation failed")
        return jsonify({"success": False, "message": "Could not start payment. Check Razorpay keys and try again."}), 502
    session["razorpay_order_id"] = order["id"]
    session["razorpay_amount"] = int(order["amount"])
    return jsonify({"success": True, "key_id": RAZORPAY_KEY_ID, "razorpay_order_id": order["id"], "amount": order["amount"], "currency": order["currency"], "name": customer["name"], "email": customer["email"], "phone": customer["phone"]})


@app.post("/api/orders")
@login_required
def create_order():
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])
    payment_method = str(data.get("payment_method", "COD")).upper().strip()

    if payment_method not in PAYMENT_METHODS:
        return jsonify({"success": False, "message": "Choose a valid payment method"}), 400
    if not items or not isinstance(items, list):
        return jsonify({"success": False, "message": "Your cart is empty"}), 400

    customer, error = validate_customer_details(data)
    if error:
        return jsonify({"success": False, "message": error}), 400

    # Save the latest delivery profile for the next checkout.
    users.update_one(
        {"_id": ObjectId(session["user_id"])},
        {"$set": {"phone": customer["phone"], "address": customer["address"], "city": customer["city"], "pincode": customer["pincode"]}},
    )

    order_items = []
    subtotal = 0.0

    for item in items:
        try:
            pid = ObjectId(item.get("id"))
            qty = int(item.get("qty", 0))
        except Exception:
            return jsonify({"success": False, "message": "Invalid product in cart"}), 400

        if qty < 1:
            return jsonify({"success": False, "message": "Quantity must be at least 1"}), 400

        p = products.find_one({"_id": pid})
        if not p:
            return jsonify({"success": False, "message": "Product not found"}), 400
        if int(p.get("stock", 0)) < qty:
            return jsonify({"success": False, "message": f"Insufficient stock for {p['name']}"}), 400

        line_total = money(p["price"]) * qty
        subtotal += line_total
        order_items.append(
            {
                "product_id": str(pid),
                "name": p["name"],
                "price": money(p["price"]),
                "unit": p.get("unit", "1 pc"),
                "qty": qty,
                "line_total": money(line_total),
            }
        )

    subtotal = money(subtotal)
    delivery_charge = 0.0 if subtotal >= 499 else 30.0
    tax = money(subtotal * 0.0)  # Grocery demo: no tax added to this student-project bill.
    discount = 0.0
    grand_total = money(subtotal + delivery_charge + tax - discount)

    # Online orders are accepted only after the Razorpay checkout signature is verified.
    transaction_id = ""
    payment_status = "Pending"
    if payment_method in {"UPI", "CARD"}:
        if not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET):
            return jsonify({"success": False, "message": "Real online payment is not configured yet. Add Razorpay test/live keys to .env."}), 503
        payment_data = data.get("payment", {}) or {}
        rp_order_id = str(payment_data.get("razorpay_order_id", ""))
        rp_payment_id = str(payment_data.get("razorpay_payment_id", ""))
        rp_signature = str(payment_data.get("razorpay_signature", ""))
        expected_order_id = session.get("razorpay_order_id")
        expected_amount = session.get("razorpay_amount")
        if int(round(grand_total * 100)) != int(expected_amount or 0):
            return jsonify({"success": False, "message": "Cart total changed after payment was started. Please retry checkout."}), 400
        if not rp_order_id or not rp_payment_id or not rp_signature or rp_order_id != expected_order_id:
            return jsonify({"success": False, "message": "Payment verification details are missing. Please retry payment."}), 400
        expected_signature = hmac.new(RAZORPAY_KEY_SECRET.encode(), f"{rp_order_id}|{rp_payment_id}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_signature, rp_signature):
            return jsonify({"success": False, "message": "Payment verification failed. No order was placed."}), 400
        transaction_id = rp_payment_id
        payment_status = "Paid"
        session.pop("razorpay_order_id", None)
        session.pop("razorpay_amount", None)

    now = datetime.utcnow()
    order = {
        "user_id": session["user_id"],
        "customer": customer,
        "items": order_items,
        "subtotal": subtotal,
        "delivery_charge": delivery_charge,
        "tax": tax,
        "discount": discount,
        "total": grand_total,
        "payment_method": payment_method,
        "payment_status": payment_status,
        "transaction_id": transaction_id,
        "status": "Placed",
        "created_at": now,
    }

    result = orders.insert_one(order)
    order_id = str(result.inserted_id)

    for item in order_items:
        products.update_one(
            {"_id": ObjectId(item["product_id"])},
            {"$inc": {"stock": -item["qty"]}},
        )

    return jsonify(
        {
            "success": True,
            "message": "Order placed successfully",
            "order_id": order_id,
            "invoice_url": f"/invoice/{order_id}",
            "payment_status": payment_status,
            "transaction_id": transaction_id,
        }
    )


def serialize_order(o):
    customer = o.get("customer", {})
    return {
        "id": str(o["_id"]),
        "user_id": o.get("user_id", ""),
        "customer": customer,
        "items": o.get("items", []),
        "subtotal": money(o.get("subtotal", 0)),
        "delivery_charge": money(o.get("delivery_charge", 0)),
        "tax": money(o.get("tax", 0)),
        "discount": money(o.get("discount", 0)),
        "total": money(o.get("total", 0)),
        "payment_method": o.get("payment_method", "COD"),
        "payment_status": o.get("payment_status", "Pending"),
        "transaction_id": o.get("transaction_id", ""),
        "address": customer.get("address", o.get("address", "")),
        "status": o.get("status", "Placed"),
        "created_at": serialize_datetime(o.get("created_at", "")),
    }


@app.get("/api/orders/<order_id>")
@login_required
def get_order(order_id):
    try:
        oid = ObjectId(order_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid order ID"}), 400

    o = orders.find_one({"_id": oid})
    if not o:
        return jsonify({"success": False, "message": "Order not found"}), 404

    if session.get("role") != "admin" and o.get("user_id") != session.get("user_id"):
        return jsonify({"success": False, "message": "You cannot view this order"}), 403

    return jsonify({"success": True, "order": serialize_order(o)})


@app.get("/api/my-orders")
@login_required
def my_orders():
    return jsonify([serialize_order(o) for o in orders.find({"user_id": session["user_id"]}).sort("created_at", -1)])


@app.get("/api/admin/users")
@admin_required
def admin_users():
    return jsonify(
        [
            {
                "id": str(u["_id"]),
                "name": u["name"],
                "email": u["email"],
                "phone": u.get("phone", ""),
                "address": u.get("address", ""),
                "city": u.get("city", ""),
                "pincode": u.get("pincode", ""),
                "role": u["role"],
                "created_at": serialize_datetime(u.get("created_at", "")),
            }
            for u in users.find({}, {"password": 0}).sort("created_at", -1)
        ]
    )


@app.get("/api/admin/orders")
@admin_required
def admin_orders():
    return jsonify([serialize_order(o) for o in orders.find().sort("created_at", -1)])


@app.put("/api/admin/orders/<order_id>")
@admin_required
def admin_update_order(order_id):
    try:
        oid = ObjectId(order_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid order ID"}), 400
    status = str((request.get_json(silent=True) or {}).get("status", "")).strip()
    if status not in ORDER_STATUSES:
        return jsonify({"success": False, "message": "Invalid order status"}), 400
    result = orders.update_one({"_id": oid}, {"$set": {"status": status}})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Order not found"}), 404
    return jsonify({"success": True, "message": "Order status updated"})



@app.post("/api/admin/products")
@admin_required
def admin_add_product():
    # Accept both JSON and FormData requests from the frontend.
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form

    name = str(data.get("name", "")).strip()
    category = str(data.get("category", "")).strip()
    unit = str(data.get("unit", "1 pc")).strip() or "1 pc"
    description = str(data.get("description", "")).strip()
    image = str(data.get("image", "")).strip()
    uploaded = request.files.get("image_file") if not request.is_json else None
    if uploaded and uploaded.filename:
        allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        ext = Path(uploaded.filename).suffix.lower()
        if ext not in allowed:
            return jsonify({"success": False, "message": "Use JPG, PNG, WEBP or GIF for product images."}), 400
        uploaded.seek(0, 2)
        if uploaded.tell() > 5 * 1024 * 1024:
            return jsonify({"success": False, "message": "Image must be 5 MB or smaller."}), 400
        uploaded.seek(0)
        filename = f"{uuid.uuid4().hex}{ext}"
        uploaded.save(UPLOAD_DIR / filename)
        image = f"/static/uploads/{filename}"
    if image and not (image.startswith("https://") or image.startswith("http://") or image.startswith("/static/")):
        return jsonify({"success": False, "message": "Image must be a valid http(s) URL or uploaded image."}), 400

    # Convert price and stock safely.
    try:
        price_text = str(data.get("price", "")).strip()
        stock_text = str(data.get("stock", "")).strip()

        if not price_text or not stock_text:
            raise ValueError

        price = float(price_text)
        stock = int(stock_text)

        if not __import__("math").isfinite(price):
            raise ValueError

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Enter a valid price and whole-number stock."
        }), 400

    # Validate the submitted fields.
    if len(name) < 2 or not category or price < 0 or stock < 0:
        return jsonify({
            "success": False,
            "message": "Enter valid product details."
        }), 400

    # Save product to MongoDB.
    product = {
        "name": name,
        "category": category,
        "price": price,
        "unit": unit,
        "stock": stock,
        "image": image ,
        "description": description,
        "created_at": datetime.utcnow()
    }

    try:
        result = products.insert_one(product)
    except Exception as e:
        app.logger.exception("Could not save product")
        return jsonify({
            "success": False,
            "message": "Could not save the product to the database."
        }), 500

    return jsonify({
        "success": True,
        "id": str(result.inserted_id),
        "message": "Product added successfully."
    }), 201



@app.put("/api/admin/products/<pid>")
@admin_required
def admin_update_product(pid):
    try:
        oid = ObjectId(pid)
    except Exception:
        return jsonify({"success": False, "message": "Invalid product id"}), 400
    data = request.get_json(silent=True) or {}
    update = {k: str(data[k]).strip() for k in ["name", "category", "unit", "image", "description"] if k in data}
    try:
        if "price" in data:
            update["price"] = float(data["price"])
        if "stock" in data:
            update["stock"] = int(data["stock"])
    except Exception:
        return jsonify({"success": False, "message": "Price must be numeric and stock must be a whole number."}), 400
    if "price" in update and (update["price"] < 0 or not __import__("math").isfinite(update["price"])):
        return jsonify({"success": False, "message": "Price cannot be negative or invalid."}), 400
    if "stock" in update and update["stock"] < 0:
        return jsonify({"success": False, "message": "Stock cannot be negative."}), 400
    if "name" in update and len(update["name"]) < 2:
        return jsonify({"success": False, "message": "Product name must have at least 2 characters."}), 400
    if "image" in update and update["image"] and not (update["image"].startswith("https://") or update["image"].startswith("http://") or update["image"].startswith("/static/")):
        return jsonify({"success": False, "message": "Image must be a valid http(s) URL or uploaded image."}), 400
    result = products.update_one({"_id": oid}, {"$set": update})
    if not result.matched_count:
        return jsonify({"success": False, "message": "Product not found."}), 404
    return jsonify({"success": True, "message": "Product updated successfully."})


@app.delete("/api/admin/products/<pid>")
@admin_required
def admin_delete_product(pid):
    try:
        oid = ObjectId(pid)
    except Exception:
        return jsonify({"success": False, "message": "Invalid product id"}), 400
    products.delete_one({"_id": oid})
    return jsonify({"success": True})


if __name__ == "__main__":
    try:
        client.admin.command("ping")
        seed_data()
        print("MongoDB connected. Mini Fresh Basket is ready.")
    except Exception as e:
        print("MongoDB connection error:", e)
        print("Start MongoDB and run the app again.")
    app.run(debug=True, host="127.0.0.1", port=5000)
