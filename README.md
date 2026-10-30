# Shop Inventory and Low-Stock Alerts

> Inventory, sales and low-stock alerts for a small local shop.

Hack Day Haldia x GRID community - 6-hour build challenge

**Repo:** `team-spark` | **Stack:** Python / Flask | **Difficulty:** Medium-Hard | **Time:** 6 hours

## Brief
Small shops track stock in notebooks. Build a simple system that keeps stock accurate, records sales and warns before items run out.

## Core tasks (must-do)
- [x] Product CRUD: name, SKU, category, cost, price, stock, reorder level
- [x] Record a sale with several line items; it reduces stock and is rejected if stock is insufficient
- [x] Restock entries and a stock-movement log per product
- [x] Low-stock alert badge and list
- [x] Sales report (daily / weekly): revenue, profit, top 5 items
- [x] Search, sort and filter the product table
- [x] Persist everything in SQLite (helper already in app.py)

## Bonus tasks (only after the core works)
- [x] CSV import / export
- [x] Moving-average demand forecast: 'reorder in N days'
- [x] Printable invoice with invoice numbers
- [x] Barcode scanning with the phone camera

## What is already here
- `index.html` - base page that pings `/api/health`
- `app.py` - Flask app with a SQLite helper (`db()`, `init_db()`), `/api/health` and TODO endpoint stubs (they return 501 until you implement them)
- `requirements.txt` - `flask`, `gunicorn`

## Run locally
```bash
pip install -r requirements.txt
python app.py   # then open http://127.0.0.1:5000
```

## Deploy
Any Python host works (for example Render or PythonAnywhere). Start command: `gunicorn app:app`. Free hosts may reset the filesystem on restart, so the SQLite file can reset - fine for a demo.

## Suggested pacing
- Hour 1: read this README, agree on a plan and split the work
- Hours 2-4: build the core tasks
- Hour 5: integrate, polish, then bonus tasks if time allows
- Hour 6: deploy, open the Pull Request, submit on the MLH platform (OrganizerHQ)

## Submission checklist
- [ ] All core tasks work end to end
- [ ] Project is deployed and the live link opens
- [ ] Pull Request created on the Voyage GitHub repository assigned to your team
- [ ] Project submitted on the MLH platform (OrganizerHQ) - instructions are shared at the start of the event

## Rules
- Build new features on top of this starter project and integrate them.
- Teams of 3-4; every member must be present.
- AI tools and open-source / open-weight models are fully allowed.
