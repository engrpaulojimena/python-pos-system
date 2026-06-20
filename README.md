# 🏪 POS System — Flask + SQLite

A full-featured Point of Sale system built with Python Flask.

## Features
- ✅ POS / Checkout with cart, discounts, tax, multiple payment methods
- ✅ Inventory management (add, edit, restock, delete)
- ✅ Product categories with color coding
- ✅ Multi-user system (Admin vs Cashier roles)
- ✅ Sales dashboard with charts
- ✅ Reports with date range filtering
- ✅ Printable receipts
- ✅ Low stock alerts
- ✅ SQLite database (no setup needed)
- ✅ Modern dark UI

## Setup

### 1. Install Flask
```
pip install flask
```

### 2. Run the app
```
python app.py
```

### 3. Open browser
```
http://127.0.0.1:5000
```

## Default Accounts
| Role    | Username  | Password    |
|---------|-----------|-------------|
| Admin   | admin     | admin123    |
| Cashier | cashier1  | cashier123  |

## File Structure
```
pos_system/
├── app.py              # Main Flask application
├── requirements.txt    # Dependencies
├── pos.db              # SQLite database (auto-created)
└── templates/
    ├── base.html       # Layout with sidebar
    ├── login.html
    ├── dashboard.html  # Admin dashboard
    ├── pos.html        # POS checkout
    ├── receipt.html    # Printable receipt
    ├── inventory.html  # Product management
    ├── categories.html # Category management
    ├── users.html      # User management
    └── reports.html    # Sales reports
```

## Role Permissions
| Feature     | Admin | Cashier |
|-------------|-------|---------|
| POS         | ✅    | ✅      |
| Dashboard   | ✅    | ❌      |
| Inventory   | ✅    | ❌      |
| Users       | ✅    | ❌      |
| Reports     | ✅    | ❌      |
