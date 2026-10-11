# Mini Fresh Basket

Mini Fresh Basket is a full-stack grocery e-commerce web application built with Flask, MongoDB, HTML, CSS, and JavaScript. It allows customers to browse products, add items to the cart, place orders, and manage delivery details, while also giving administrators tools to monitor users, update order status, and manage the catalog.

The storefront supports COD and Razorpay-powered UPI/card checkout. Online payments require your own Razorpay API keys; without them, online payment is intentionally disabled rather than falsely marked as paid.

## Project overview

The application follows a lightweight server-rendered and API-driven architecture:

- Python Flask handles the backend logic, authentication, validation, and REST endpoints.
- MongoDB stores user data, product inventory, and order records.
- JavaScript in the frontend updates the UI, handles cart logic, and calls backend APIs.
- HTML templates render the customer and admin pages.

## Key features

- Product catalog with category and keyword search
- Grocery products displayed with photographic images
- Responsive shopping layout for desktop, tablet, and mobile
- User registration and login with password hashing
- Session-based authentication for customers and admins
- Shopping cart with quantity management
- Checkout flow with customer and delivery details
- Bill calculation with free delivery above ₹499 and ₹30 delivery below that threshold
- Payment options: COD, UPI, and Card
- Razorpay payment checkout and server-side signature verification for UPI/Card (requires API keys)
- Invoice generation and printable PDF output through browser print
- Customer order history and order retrieval
- Admin dashboard to view users and orders
- Admin ability to update order status
- Admin ability to add, edit, and delete products
- Admin product form supports image uploads and image URLs, with an image preview
- MongoDB indexing for users, products, and order lookups

## Tech stack

- Backend: Python 3.10+, Flask
- Database: MongoDB
- Frontend: HTML, CSS, JavaScript
- Libraries:
  - Flask
  - pymongo
  - Werkzeug
  - razorpay
  - python-dotenv

## Project structure

```text
Mini-Fresh-Basket/
├── .env.example
├── .gitignore
├── app.py
├── requirements.txt
├── README.md
├── static/
│   ├── css/
│   │   └── style.css
│   ├── images/
│   └── js/
│       ├── admin.js
│       ├── app.js
│       ├── auth.js
│       ├── cart.js
│       ├── checkout.js
│       └── invoice.js
└── templates/
    ├── admin.html
    ├── cart.html
    ├── checkout.html
    ├── index.html
    ├── invoice.html
    ├── login.html
    └── register.html
```

## Application architecture

### Backend

The backend is defined in `app.py` and contains:

- Flask app initialization and config
- MongoDB connection setup
- Seed data creation for admin and sample products
- Authentication decorators (`login_required`, `admin_required`)
- Input validation functions
- API routes for products, users, orders, and admin management

### Frontend

The frontend is split between templates and static JavaScript files:

- `templates/index.html` renders the storefront and product listings.
- `templates/cart.html` handles the cart page.
- `templates/checkout.html` collects customer and delivery information.
- `templates/invoice.html` shows the final generated invoice.
- `templates/admin.html` provides admin access to user and order data.
- `static/js/*.js` contains the client-side logic for product browsing, authentication, cart updates, checkout flow, and invoice display.

## Environment configuration

The app uses environment variables for important configuration. A sample file is included in `.env.example`:

```env
SECRET_KEY=change-this-secret
MONGO_URI=mongodb://127.0.0.1:27017/
DB_NAME=mini_fresh_basket
```

You can either:

- create a `.env` file locally, or
- use the default values already defined in the application.

## Prerequisites

Before running the project, install:

- Python 3.10 or newer
- MongoDB Community Server
- Optional: MongoDB Compass for easier database inspection

## Installation

1. Open a terminal in the project folder.
2. Create a virtual environment (optional but recommended):

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Ensure MongoDB is running locally at:

```text
mongodb://127.0.0.1:27017/
```

5. Start the app:

```bash
python app.py
```

6. Open the browser at:

```text
http://127.0.0.1:5000
```

## Default admin account

The app seeds an admin user automatically when the database is empty.

```text
Email: pratiksha12@gmail.com
Password: Pratiksha@123
```

Important: change this password before using the app in a non-demo environment.

## Database schema

The application uses a MongoDB database named `mini_fresh_basket`.

### Collections

#### users
Stores customer and admin account details.

Example fields:

- `_id`
- `name`
- `email`
- `phone`
- `password` (hashed using Werkzeug)
- `role` (`customer` or `admin`)
- `created_at`
- `address`, `city`, `pincode` (for customer delivery profile)

#### products
Stores the grocery inventory.

Example fields:

- `_id`
- `name`
- `category`
- `price`
- `unit`
- `stock`
- `image`
- `description`

#### orders
Stores each customer purchase.

Example fields:

- `_id`
- `user_id`
- `customer`
- `items`
- `subtotal`
- `delivery_charge`
- `tax`
- `discount`
- `total`
- `payment_method`
- `payment_status`
- `transaction_id`
- `status`
- `created_at`

## Core user flows

### Customer flow

1. User registers or logs in.
2. User views products and applies search or category filters.
3. User adds products to the cart.
4. User reviews the cart and clicks checkout.
5. User provides name, phone, address, city, and pincode.
6. User selects a payment method (COD, UPI, or Card).
7. Order is validated and stored in MongoDB.
8. Inventory is reduced based on purchased quantities.
9. User receives an invoice and can print or save it as PDF.

### Admin flow

1. Admin logs in with the seeded admin account or an admin role user.
2. Admin opens the dashboard to view registered users.
3. Admin views all orders and can update order statuses.
4. Admin can create, update, or delete product records.
5. When creating a product, the admin can upload a JPG, PNG, WEBP, or GIF image (up to 5 MB), provide an image URL, or use the category's default photo.

## API endpoints

The app exposes several endpoints for frontend interaction.

### Public/authentication routes

- `GET /` — Home page
- `GET /login` — Login page
- `GET /register` — Registration page
- `POST /api/register` — Register a customer
- `POST /api/login` — Login user
- `POST /api/logout` — Logout user
- `GET /api/me` — Get current authenticated user data

### Customer routes

- `GET /cart` — Cart page
- `GET /checkout` — Checkout page
- `GET /invoice/<order_id>` — Invoice page
- `GET /api/products` — Get all products or filtered results
- `GET /api/checkout/profile` — Get saved checkout profile
- `POST /api/orders` — Create a new order
- `GET /api/orders/<order_id>` — View a specific order
- `GET /api/my-orders` — Get all orders for the logged-in user

### Admin routes

- `GET /admin` — Admin dashboard
- `GET /api/admin/users` — List all users
- `GET /api/admin/orders` — List all orders
- `PUT /api/admin/orders/<order_id>` — Update order status
- `POST /api/admin/products` — Add a new product
- `PUT /api/admin/products/<pid>` — Update product record
- `DELETE /api/admin/products/<pid>` — Delete product record

## Business logic highlights

### Pricing and delivery rules

The order calculation logic is implemented in `create_order()`:

- `subtotal` is the sum of all item line totals.
- Delivery is free when subtotal is ₹499 or more.
- Otherwise, delivery charge is ₹30.
- Tax is currently set to `0` for this demo project.
- Discount is `0` by default.
- Grand total is calculated as:

```text
subtotal + delivery_charge + tax - discount
```

### Payment handling

This project includes a demo payment flow only:

- COD remains Pending
- UPI and Card are marked as Paid
- A transaction reference such as `MFB-...` is generated
- No real payment gateway integration is configured
- No sensitive card or UPI information is stored

This is appropriate for learning and demo purposes, but not for production commerce.

## Security notes

The project includes several basic protections:

- Password hashing with Werkzeug
- Session-based authentication
- Admin-only route protection via decorators
- Login guards for order access
- Input validation for email, phone, address, and order data

However, this is still a student project and should not be treated as a hardened production application.

## Troubleshooting

### MongoDB connection issue

If the app prints a MongoDB connection error:

- Make sure MongoDB is running
- Verify the URI in `.env` or the default value
- Check that the database service is accessible on port 27017

### Admin login does not work

- Confirm the database was initialized and the admin user was inserted
- Check whether the application has created a new empty database without the seeded account
- Delete the database and restart the app if needed for a clean seed

### Cart or checkout not working

- Ensure the browser has JavaScript enabled
- Confirm the product IDs are valid and the product stock is sufficient
- Check Flask server logs for request validation errors

## Recommended improvements

For a production-ready version, the following improvements would be valuable:

- Integrate a real payment gateway such as Razorpay or Stripe
- Add product image uploads and storage
- Add role-based access improvements and audit logging
- Add unit tests for authentication and order logic
- Add environment validation for production deployment
- Improve error handling and transaction safety

## License

This project is intended for educational and demonstration use. Its licensing terms depend on the repository or your local environment if you are using it as part of coursework or an assignment.

## Summary

Mini Fresh Basket is a practical demo of a grocery order management and storefront system using Flask and MongoDB. It covers the complete shopping journey from browsing products and placing orders to validating payments and managing the admin panel. It is well suited for learning full-stack web development and e-commerce workflows in a simple, manageable codebase.


## Latest changes (October 2026)

- Admin can edit product name, category, price, unit, image URL/path, description, and stock. Stock can be set to `0` to mark a product out of stock.
- Product images use the actual URL/uploaded image without placing the basket logo over the photo. If an image fails to load, the page displays an image-unavailable message.
- Add to Cart and cart quantity controls check the latest stock; customers cannot increase quantity above the available stock. The checkout API also validates stock on the server.
- Admin product uploads accept JPG, JPEG, PNG, WEBP and GIF up to 5 MB.
- UPI/card checkout is wired to Razorpay and verifies the payment signature on the server. **Real online payments will not work until you add your own Razorpay API keys** to a local `.env` file. Use Razorpay test keys first. Never share your Razorpay secret key. Cash on Delivery does not require gateway keys.
- Default admin login for a fresh database: `pratiksha3767@gmail.com` / `Pass@1234`. If the database already contains a different admin account, the new admin account is added at startup without deleting existing accounts. Change this password after your first login.

### Configure Razorpay

1. Copy `.env.example` to `.env` in the project root.
2. Put your Razorpay **test** Key ID and Key Secret into `.env`. Obtain them from your Razorpay Dashboard.
3. Install packages using `pip install -r requirements.txt`.
4. Start MongoDB, then run `python app.py`.
5. Test UPI/card payments using Razorpay test mode before switching to live keys. Live payments require an activated Razorpay account and live API keys.


## Admin login and email OTP password reset

1. Copy `.env.example` to `.env` and keep `.env` private (it is ignored by Git).
2. Admin login defaults for this local project: `pratiksha3767@gmail.com` / `Pratiksha@gmail123`. Change `ADMIN_PASSWORD` in `.env` before any public deployment. The app syncs this configured admin password when it starts.
3. To send real password-reset OTP emails, configure `MAIL_USERNAME`, `MAIL_PASSWORD`, and `MAIL_FROM` in `.env`. For Gmail, turn on 2-Step Verification and create a Google **App Password**; do not use your regular Gmail password. The sender Gmail can be different from the admin/customer account receiving the OTP.
4. Open **Forgot password?** on the Login page. A 6-digit OTP is emailed to the registered address, expires in 10 minutes, and is limited to five attempts. The app never emails a user's old password; it securely resets it after OTP verification.
5. Restart with `python app.py`. Real email delivery needs working internet access and valid SMTP credentials.
#   p r a t i k s h a 1 2 4  
 