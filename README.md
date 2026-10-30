# 🛒 Shop Inventory & Low-Stock Alerts

> A simple inventory, sales and low-stock alert system for small local shops — replacing the notebook with something accurate and automatic.

Built for **Hack Day Haldia × GRID Community** (6-hour build challenge).

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-backend-black)
![SQLite](https://img.shields.io/badge/SQLite-database-003B57)

---

## 📌 Problem

Small shopkeepers usually track stock in notebooks. Counts drift, sales go unrecorded, and items run out without warning. This app keeps stock accurate, records every sale, and warns the owner **before** an item runs out.

## ✨ Features

### Core
- **Product management (CRUD)** — name, SKU, category, cost price, selling price, stock and reorder level
- **Record sales** — multiple line items in one sale; stock is reduced automatically and the sale is rejected if stock is insufficient
- **Restock entries** — add incoming stock and keep a **stock-movement log** for every product
- **Low-stock alerts** — alert badge plus a list of items at or below their reorder level
- **Sales reports** — daily / weekly revenue, profit and top 5 selling items
- **Search, sort & filter** — find products quickly in the product table
- **Persistent storage** — everything is saved in SQLite

### Bonus *(list only what you actually built)*
- [ ] CSV import / export
- [ ] Moving-average demand forecast ("reorder in N days")
- [ ] Printable invoices with invoice numbers
- [ ] Barcode scanning with the phone camera

## 🧰 Tech Stack

| Layer     | Technology                  |
|-----------|-----------------------------|
| Backend   | Python, Flask               |
| Database  | SQLite                      |
| Frontend  | HTML, CSS, JavaScript (`index.html`) |
| Server    | Gunicorn (production)       |

## 📁 Project Structure

```
.
├── app.py            # Flask app, database helpers and API endpoints
├── index.html        # Frontend UI
├── requirements.txt  # Python dependencies
├── data.db           # SQLite database
└── README.md
```

## 🚀 Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/rehanhussaink2-web/Shop-Inventory-Low-Stock-Alerts.git
cd Shop-Inventory-Low-Stock-Alerts

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## ☁️ Deployment

Deployed on **Render** (any Python host works).

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`

> Note: free hosts may reset the filesystem on restart, so the SQLite data can reset. This is fine for a demo.

## 🖼️ Screenshots

<!-- Add screenshots here, e.g. -->
<!-- ![Dashboard](screenshots/dashboard.png) -->

## 👥 Team

**Team Spark**

| Name | Role |
|------|------|
| _Your name_ | _e.g. Backend_ |
| _Teammate_ | _e.g. Frontend_ |
| _Teammate_ | _e.g. Reports & testing_ |

## 🔮 Future Improvements

- User login for shop owners and staff
- Supplier management and purchase orders
- SMS / WhatsApp notifications for low stock
- Switch to PostgreSQL for hosted deployments

## 📄 License

Created for a hackathon. Add a license of your choice (e.g. MIT) if you plan to share it publicly.
