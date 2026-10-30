"""Shop Inventory and Low-Stock Alerts - Hack Day Haldia x GRID community
Full-featured Flask backend implementing all core tasks and bonus requirements.
"""
import os
import sqlite3
import csv
import io
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory, Response

app = Flask(__name__, static_folder=None)
DB_PATH = os.path.join(app.root_path, "data.db")


def db():
    """SQLite connection whose rows behave like dicts. Use: with db() as conn: ..."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL DEFAULT 'General',
                cost REAL NOT NULL DEFAULT 0.0,
                price REAL NOT NULL DEFAULT 0.0,
                stock INTEGER NOT NULL DEFAULT 0,
                reorder_level INTEGER NOT NULL DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                customer_name TEXT DEFAULT 'Walk-in Customer',
                payment_method TEXT DEFAULT 'Cash',
                total_amount REAL NOT NULL,
                total_cost REAL NOT NULL,
                total_profit REAL NOT NULL,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                sku TEXT,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                unit_cost REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL, -- 'initial', 'restock', 'sale', 'adjustment'
                quantity INTEGER NOT NULL,   -- positive for in, negative for out
                prev_stock INTEGER NOT NULL,
                new_stock INTEGER NOT NULL,
                reference_id TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            );
        """)

        # Auto-seed sample store data if database is empty so demo is ready out-of-the-box
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM products")
        if cursor.fetchone()["count"] == 0:
            seed_initial_data(conn)


def seed_initial_data(conn):
    """Seed sample data suitable for small local shop demo"""
    sample_products = [
        ("Fortune Sunflower Oil 1L", "OIL-001", "Groceries", 110.0, 145.0, 18, 5),
        ("Aashirvaad Atta 5kg", "ATTA-002", "Groceries", 210.0, 260.0, 12, 4),
        ("Parle-G Gold Biscuits 250g", "BIS-003", "Snacks", 22.0, 30.0, 4, 10),      # Low stock!
        ("Maggi 2-Minute Noodles 4-Pack", "NOOD-004", "Snacks", 48.0, 60.0, 0, 8),     # Out of stock!
        ("Amul Butter 100g", "DAIRY-005", "Dairy", 46.0, 56.0, 3, 5),                 # Low stock!
        ("Tata Tea Premium 500g", "TEA-006", "Beverages", 195.0, 240.0, 15, 5),
        ("Cadbury Dairy Milk Silk 60g", "CHOC-007", "Snacks", 65.0, 85.0, 9, 6),
        ("Colgate MaxFresh Toothpaste 150g", "COL-008", "Personal Care", 85.0, 115.0, 22, 6),
        ("Dettol Original Soap 125g", "SOAP-009", "Personal Care", 42.0, 55.0, 2, 8), # Low stock!
        ("Nescafe Classic Coffee 50g", "COF-010", "Beverages", 130.0, 170.0, 14, 4),
        ("Duracell AAA Batteries 2-Pack", "BAT-011", "Household", 70.0, 99.0, 16, 5),
        ("Lays Classic Salted Chips 50g", "CHIP-012", "Snacks", 15.0, 20.0, 25, 10),
    ]

    for name, sku, cat, cost, price, stock, reorder in sample_products:
        conn.execute("""
            INSERT INTO products (name, sku, category, cost, price, stock, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, sku, cat, cost, price, stock, reorder))
        pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if stock > 0:
            conn.execute("""
                INSERT INTO stock_movements (product_id, movement_type, quantity, prev_stock, new_stock, reference_id, notes)
                VALUES (?, 'initial', ?, 0, ?, 'INITIAL_SETUP', 'Initial store inventory')
            """, (pid, stock, stock))

    # Add realistic past sales history over recent days
    now = datetime.now()
    sales_seed = [
        (now - timedelta(days=2), "INV-1001", "Ramesh Kumar", "UPI", [
            ("OIL-001", 2),
            ("ATTA-002", 1),
            ("TEA-006", 1),
        ], "Regular customer"),
        (now - timedelta(days=1), "INV-1002", "Priya Sharma", "Cash", [
            ("BIS-003", 4),
            ("COL-008", 1),
            ("CHOC-007", 2),
        ], "Evening shopping"),
        (now - timedelta(hours=3), "INV-1003", "Anil Sen", "Card", [
            ("DAIRY-005", 2),
            ("COF-010", 1),
            ("CHIP-012", 3),
        ], "Quick counter sale"),
    ]

    for sale_date, inv, customer, payment, items, notes in sales_seed:
        total_amt = 0.0
        total_cst = 0.0
        sale_items_data = []

        for sku, qty in items:
            p = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
            if p:
                sub = p["price"] * qty
                cst = p["cost"] * qty
                total_amt += sub
                total_cst += cst
                sale_items_data.append((p["id"], p["name"], p["sku"], qty, p["price"], p["cost"], sub))

        profit = total_amt - total_cst
        conn.execute("""
            INSERT INTO sales (invoice_no, customer_name, payment_method, total_amount, total_cost, total_profit, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (inv, customer, payment, total_amt, total_cst, profit, notes, sale_date.strftime("%Y-%m-%d %H:%M:%S")))
        sale_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for pid, pname, psku, qty, uprice, ucost, sub in sale_items_data:
            conn.execute("""
                INSERT INTO sale_items (sale_id, product_id, product_name, sku, quantity, unit_price, unit_cost, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sale_id, pid, pname, psku, qty, uprice, ucost, sub))
            # Note: seed sales don't need double deduction as initial stock was set directly


init_db()


@app.get("/")
def home():
    return send_from_directory(app.root_path, "index.html")


@app.get("/api/health")
def health():
    return jsonify(ok=True)


# ---- CORE TASK: Product CRUD, Search, Sort & Filter ---------------------
@app.route("/api/products", methods=['GET', 'POST'])
def ep1_api_products(**kwargs):
    if request.method == 'GET':
        query = request.args.get('q', '').strip().lower()
        category = request.args.get('category', '').strip()
        low_stock_only = request.args.get('low_stock', '').lower() in ('true', '1', 'yes')
        sort_by = request.args.get('sort', 'name_asc')

        sql = "SELECT * FROM products WHERE 1=1"
        params = []

        if query:
            sql += " AND (LOWER(name) LIKE ? OR LOWER(sku) LIKE ? OR LOWER(category) LIKE ?)"
            q_param = f"%{query}%"
            params.extend([q_param, q_param, q_param])

        if category and category != 'All':
            sql += " AND category = ?"
            params.append(category)

        if low_stock_only:
            sql += " AND stock <= reorder_level"

        sort_map = {
            'name_asc': 'name ASC',
            'name_desc': 'name DESC',
            'stock_asc': 'stock ASC',
            'stock_desc': 'stock DESC',
            'price_asc': 'price ASC',
            'price_desc': 'price DESC',
            'newest': 'id DESC'
        }
        order_clause = sort_map.get(sort_by, 'name ASC')
        sql += f" ORDER BY {order_clause}"

        with db() as conn:
            rows = conn.execute(sql, params).fetchall()
            products = []
            for r in rows:
                item = dict(r)
                item['is_low_stock'] = item['stock'] <= item['reorder_level']
                item['is_out_of_stock'] = item['stock'] == 0
                item['margin_pct'] = round(((item['price'] - item['cost']) / item['price'] * 100), 1) if item['price'] > 0 else 0
                products.append(item)

            # Also fetch distinct categories for easy UI filtering
            categories_rows = conn.execute("SELECT DISTINCT category FROM products WHERE category != '' ORDER BY category").fetchall()
            categories = [c['category'] for c in categories_rows]

            # Overall stats
            total_items = len(products)
            low_stock_count = sum(1 for p in products if p['is_low_stock'])
            out_of_stock_count = sum(1 for p in products if p['is_out_of_stock'])

            return jsonify(
                ok=True,
                products=products,
                categories=categories,
                total_count=total_items,
                low_stock_count=low_stock_count,
                out_of_stock_count=out_of_stock_count
            )

    # POST - Create product
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    sku = (data.get('sku') or '').strip().upper()
    category = (data.get('category') or 'General').strip()

    try:
        cost = float(data.get('cost', 0.0))
        price = float(data.get('price', 0.0))
        stock = int(data.get('stock', 0))
        reorder_level = int(data.get('reorder_level', 5))
    except (ValueError, TypeError):
        return jsonify(error="Cost, price, stock, and reorder level must be valid numbers"), 400

    if not name:
        return jsonify(error="Product name is required"), 400
    if not sku:
        return jsonify(error="SKU is required"), 400
    if cost < 0 or price < 0 or stock < 0 or reorder_level < 0:
        return jsonify(error="Values cannot be negative"), 400

    with db() as conn:
        # Check SKU uniqueness
        existing = conn.execute("SELECT id FROM products WHERE sku = ?", (sku,)).fetchone()
        if existing:
            return jsonify(error=f"A product with SKU '{sku}' already exists"), 400

        cursor = conn.execute("""
            INSERT INTO products (name, sku, category, cost, price, stock, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, sku, category, cost, price, stock, reorder_level))
        pid = cursor.lastrowid

        if stock > 0:
            conn.execute("""
                INSERT INTO stock_movements (product_id, movement_type, quantity, prev_stock, new_stock, reference_id, notes)
                VALUES (?, 'initial', ?, 0, ?, 'INITIAL_STOCK', 'Added with initial stock')
            """, (pid, stock, stock))

        new_product = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        p_dict = dict(new_product)
        p_dict['is_low_stock'] = p_dict['stock'] <= p_dict['reorder_level']
        return jsonify(ok=True, product=p_dict), 201


@app.route("/api/products/<int:pid>", methods=['GET', 'PUT', 'DELETE'])
def ep2_api_products_int_pid(pid, **kwargs):
    if request.method == 'GET':
        with db() as conn:
            product = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
            if not product:
                return jsonify(error="Product not found"), 404
            p_dict = dict(product)
            p_dict['is_low_stock'] = p_dict['stock'] <= p_dict['reorder_level']
            return jsonify(ok=True, product=p_dict)

    if request.method == 'PUT':
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        sku = (data.get('sku') or '').strip().upper()
        category = (data.get('category') or 'General').strip()

        try:
            cost = float(data.get('cost', 0.0))
            price = float(data.get('price', 0.0))
            reorder_level = int(data.get('reorder_level', 5))
            new_stock = int(data.get('stock')) if 'stock' in data else None
        except (ValueError, TypeError):
            return jsonify(error="Invalid numeric input"), 400

        if not name or not sku:
            return jsonify(error="Name and SKU are required"), 400

        with db() as conn:
            current = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
            if not current:
                return jsonify(error="Product not found"), 404

            # Check if SKU was changed and conflicts with another product
            sku_check = conn.execute("SELECT id FROM products WHERE sku = ? AND id != ?", (sku, pid)).fetchone()
            if sku_check:
                return jsonify(error=f"SKU '{sku}' is already taken by another product"), 400

            prev_stock = current['stock']
            stock_to_set = prev_stock if new_stock is None else new_stock

            conn.execute("""
                UPDATE products
                SET name = ?, sku = ?, category = ?, cost = ?, price = ?, stock = ?, reorder_level = ?
                WHERE id = ?
            """, (name, sku, category, cost, price, stock_to_set, reorder_level, pid))

            if new_stock is not None and new_stock != prev_stock:
                diff = new_stock - prev_stock
                conn.execute("""
                    INSERT INTO stock_movements (product_id, movement_type, quantity, prev_stock, new_stock, reference_id, notes)
                    VALUES (?, 'adjustment', ?, ?, ?, 'MANUAL_EDIT', 'Stock manually adjusted in product edit')
                """, (pid, diff, prev_stock, new_stock))

            updated = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
            u_dict = dict(updated)
            u_dict['is_low_stock'] = u_dict['stock'] <= u_dict['reorder_level']
            return jsonify(ok=True, product=u_dict)

    if request.method == 'DELETE':
        with db() as conn:
            current = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
            if not current:
                return jsonify(error="Product not found"), 404

            conn.execute("DELETE FROM products WHERE id = ?", (pid,))
            return jsonify(ok=True, message=f"Product '{current['name']}' deleted successfully")


# ---- CORE TASK: Restock Entries & Stock Movement Log --------------------
@app.route("/api/restock", methods=['POST'])
def ep3_api_restock(**kwargs):
    data = request.get_json() or {}
    try:
        pid = int(data.get('product_id'))
        quantity = int(data.get('quantity', 0))
    except (ValueError, TypeError):
        return jsonify(error="product_id and quantity must be valid integers"), 400

    if quantity <= 0:
        return jsonify(error="Restock quantity must be greater than 0"), 400

    notes = (data.get('notes') or '').strip()
    unit_cost = data.get('unit_cost')

    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if not product:
            return jsonify(error="Product not found"), 404

        prev_stock = product['stock']
        new_stock = prev_stock + quantity

        # If restock includes an updated unit cost, update product cost
        if unit_cost is not None:
            try:
                new_cost = float(unit_cost)
                if new_cost >= 0:
                    conn.execute("UPDATE products SET cost = ?, stock = ? WHERE id = ?", (new_cost, new_stock, pid))
                else:
                    conn.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, pid))
            except ValueError:
                conn.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, pid))
        else:
            conn.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, pid))

        ref = f"RESTOCK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        conn.execute("""
            INSERT INTO stock_movements (product_id, movement_type, quantity, prev_stock, new_stock, reference_id, notes)
            VALUES (?, 'restock', ?, ?, ?, ?, ?)
        """, (pid, quantity, prev_stock, new_stock, ref, notes or 'Stock replenishment'))

        updated = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        u_dict = dict(updated)
        u_dict['is_low_stock'] = u_dict['stock'] <= u_dict['reorder_level']
        return jsonify(ok=True, product=u_dict, new_stock=new_stock, added=quantity)


@app.route("/api/products/<int:pid>/movements", methods=['GET'])
def get_product_movements(pid):
    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if not product:
            return jsonify(error="Product not found"), 404

        movements = conn.execute("""
            SELECT * FROM stock_movements
            WHERE product_id = ?
            ORDER BY created_at DESC, id DESC
        """, (pid,)).fetchall()

        return jsonify(
            ok=True,
            product=dict(product),
            movements=[dict(m) for m in movements]
        )


# ---- CORE TASK: Record Sale with Line Items & Stock Validation ----------
@app.route("/api/sales", methods=['GET', 'POST'])
def ep4_api_sales(**kwargs):
    if request.method == 'GET':
        limit = int(request.args.get('limit', 50))
        with db() as conn:
            sales_rows = conn.execute("""
                SELECT * FROM sales ORDER BY created_at DESC, id DESC LIMIT ?
            """, (limit,)).fetchall()
            sales = []
            for s in sales_rows:
                s_dict = dict(s)
                items_rows = conn.execute("SELECT * FROM sale_items WHERE sale_id = ?", (s['id'],)).fetchall()
                s_dict['items'] = [dict(it) for it in items_rows]
                sales.append(s_dict)
            return jsonify(ok=True, sales=sales)

    # POST - Record Sale
    data = request.get_json() or {}
    items = data.get('items', [])
    if not items or not isinstance(items, list):
        return jsonify(error="Sale must have at least one line item in 'items' list"), 400

    customer_name = (data.get('customer_name') or 'Walk-in Customer').strip()
    payment_method = (data.get('payment_method') or 'Cash').strip()
    notes = (data.get('notes') or '').strip()

    with db() as conn:
        # Step 1: Pre-validation of all line items and stock sufficiency
        validated_items = []
        for index, item in enumerate(items):
            pid = item.get('product_id')
            sku = item.get('sku')
            try:
                qty = int(item.get('quantity', 0))
            except (ValueError, TypeError):
                return jsonify(error=f"Item #{index+1}: Quantity must be a valid positive integer"), 400

            if qty <= 0:
                return jsonify(error=f"Item #{index+1}: Quantity must be at least 1"), 400

            if pid:
                product = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
            elif sku:
                product = conn.execute("SELECT * FROM products WHERE sku = ?", (sku.strip().upper(),)).fetchone()
            else:
                return jsonify(error=f"Item #{index+1}: product_id or sku is required"), 400

            if not product:
                return jsonify(error=f"Item #{index+1}: Product not found"), 404

            # CRITICAL REQUIREMENT: "rejected if stock is insufficient"
            if product['stock'] < qty:
                return jsonify(
                    error=f"Insufficient stock for '{product['name']}'. Requested: {qty}, Available: {product['stock']}"
                ), 400

            unit_price = float(item.get('unit_price', product['price']))
            unit_cost = float(product['cost'])
            subtotal = round(unit_price * qty, 2)
            subtotal_cost = round(unit_cost * qty, 2)

            validated_items.append({
                'product': product,
                'quantity': qty,
                'unit_price': unit_price,
                'unit_cost': unit_cost,
                'subtotal': subtotal,
                'subtotal_cost': subtotal_cost
            })

        # Step 2: Generate unique Invoice Number
        inv_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        cursor = conn.execute("SELECT COUNT(*) as count FROM sales")
        seq = cursor.fetchone()['count'] + 1
        invoice_no = f"INV-{inv_timestamp}-{seq:04d}"

        total_amount = round(sum(it['subtotal'] for it in validated_items), 2)
        total_cost = round(sum(it['subtotal_cost'] for it in validated_items), 2)
        total_profit = round(total_amount - total_cost, 2)

        # Step 3: Atomic execution inside transaction
        cursor = conn.execute("""
            INSERT INTO sales (invoice_no, customer_name, payment_method, total_amount, total_cost, total_profit, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (invoice_no, customer_name, payment_method, total_amount, total_cost, total_profit, notes))
        sale_id = cursor.lastrowid

        # Deduct stock and insert records
        for it in validated_items:
            p = it['product']
            qty = it['quantity']
            prev_stock = p['stock']
            new_stock = prev_stock - qty

            # Deduct stock
            conn.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, p['id']))

            # Record sale item
            conn.execute("""
                INSERT INTO sale_items (sale_id, product_id, product_name, sku, quantity, unit_price, unit_cost, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sale_id, p['id'], p['name'], p['sku'], qty, it['unit_price'], it['unit_cost'], it['subtotal']))

            # Record stock movement log
            conn.execute("""
                INSERT INTO stock_movements (product_id, movement_type, quantity, prev_stock, new_stock, reference_id, notes)
                VALUES (?, 'sale', ?, ?, ?, ?, ?)
            """, (p['id'], -qty, prev_stock, new_stock, invoice_no, f"Sale to {customer_name}"))

        # Fetch full sale record for invoice
        sale_row = conn.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
        sale_dict = dict(sale_row)
        sale_items_rows = conn.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,)).fetchall()
        sale_dict['items'] = [dict(r) for r in sale_items_rows]

        return jsonify(
            ok=True,
            sale=sale_dict,
            invoice_no=invoice_no,
            total_amount=total_amount,
            total_profit=total_profit,
            message="Sale recorded successfully and stock updated"
        ), 201


@app.route("/api/sales/<int:sid>", methods=['GET'])
def get_sale_invoice(sid):
    with db() as conn:
        sale = conn.execute("SELECT * FROM sales WHERE id = ?", (sid,)).fetchone()
        if not sale:
            return jsonify(error="Sale not found"), 404
        s_dict = dict(sale)
        items = conn.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sid,)).fetchall()
        s_dict['items'] = [dict(it) for it in items]
        return jsonify(ok=True, sale=s_dict)


# ---- CORE TASK: Sales Report (Daily / Weekly / Monthly) -----------------
@app.route("/api/reports/sales", methods=['GET'])
def ep5_api_reports_sales(**kwargs):
    period = request.args.get('period', 'daily').lower()  # 'daily', 'weekly', 'monthly', 'all'
    now = datetime.now()

    if period == 'daily':
        # Today
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'weekly':
        # Last 7 days
        start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'monthly':
        # Last 30 days
        start_date = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # All time
        start_date = datetime(2000, 1, 1)

    start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")

    with db() as conn:
        # Aggregate totals
        summary_row = conn.execute("""
            SELECT
                COALESCE(SUM(total_amount), 0.0) as revenue,
                COALESCE(SUM(total_cost), 0.0) as cost,
                COALESCE(SUM(total_profit), 0.0) as profit,
                COUNT(id) as total_sales
            FROM sales
            WHERE created_at >= ?
        """, (start_str,)).fetchone()

        revenue = round(summary_row['revenue'], 2)
        cost = round(summary_row['cost'], 2)
        profit = round(summary_row['profit'], 2)
        margin = round((profit / revenue * 100), 1) if revenue > 0 else 0.0

        # Top 5 items in this period
        top_items_rows = conn.execute("""
            SELECT
                si.product_id,
                si.product_name,
                si.sku,
                SUM(si.quantity) as total_qty,
                ROUND(SUM(si.subtotal), 2) as total_revenue,
                ROUND(SUM(si.subtotal - (si.unit_cost * si.quantity)), 2) as total_profit
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            WHERE s.created_at >= ?
            GROUP BY si.product_id
            ORDER BY total_qty DESC, total_revenue DESC
            LIMIT 5
        """, (start_str,)).fetchall()
        top_items = [dict(t) for t in top_items_rows]

        # Daily sales trend for charts
        trend_rows = conn.execute("""
            SELECT
                DATE(created_at) as sale_date,
                ROUND(SUM(total_amount), 2) as daily_revenue,
                ROUND(SUM(total_profit), 2) as daily_profit,
                COUNT(id) as count
            FROM sales
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY sale_date ASC
        """, (start_str,)).fetchall()
        trend = [dict(t) for t in trend_rows]

        # Recent sales in period
        recent_sales_rows = conn.execute("""
            SELECT * FROM sales
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (start_str,)).fetchall()
        recent_sales = []
        for s in recent_sales_rows:
            s_dict = dict(s)
            items = conn.execute("SELECT * FROM sale_items WHERE sale_id = ?", (s['id'],)).fetchall()
            s_dict['items'] = [dict(it) for it in items]
            recent_sales.append(s_dict)

        return jsonify(
            ok=True,
            period=period,
            summary={
                'revenue': revenue,
                'cost': cost,
                'profit': profit,
                'profit_margin_pct': margin,
                'total_sales_count': summary_row['total_sales']
            },
            top_5_items=top_items,
            daily_trend=trend,
            recent_sales=recent_sales
        )


# ---- BONUS TASK: Low-Stock Alerts & Demand Forecast ---------------------
@app.route("/api/alerts", methods=['GET'])
def get_alerts():
    with db() as conn:
        rows = conn.execute("""
            SELECT * FROM products
            WHERE stock <= reorder_level
            ORDER BY stock ASC, (stock - reorder_level) ASC
        """).fetchall()

        alerts = []
        for r in rows:
            item = dict(r)
            item['deficit'] = max(0, item['reorder_level'] - item['stock'])
            item['urgency'] = 'critical' if item['stock'] == 0 else 'warning'
            alerts.append(item)

        return jsonify(
            ok=True,
            alerts=alerts,
            count=len(alerts),
            critical_count=sum(1 for a in alerts if a['urgency'] == 'critical')
        )


@app.route("/api/forecast", methods=['GET'])
def get_demand_forecast():
    """Moving-average demand forecast: 'reorder in N days'"""
    days_window = int(request.args.get('days', 14))
    since = (datetime.now() - timedelta(days=days_window)).strftime("%Y-%m-%d %H:%M:%S")

    with db() as conn:
        products = conn.execute("SELECT * FROM products ORDER BY name ASC").fetchall()
        forecasts = []

        for p in products:
            p_dict = dict(p)
            # Count units sold in last N days
            sold_row = conn.execute("""
                SELECT COALESCE(SUM(si.quantity), 0) as units_sold
                FROM sale_items si
                JOIN sales s ON si.sale_id = s.id
                WHERE si.product_id = ? AND s.created_at >= ?
            """, (p['id'], since)).fetchone()

            units_sold = sold_row['units_sold']
            daily_velocity = units_sold / float(days_window)

            current_stock = p['stock']
            reorder_level = p['reorder_level']

            if daily_velocity > 0:
                days_left = round(current_stock / daily_velocity, 1)
                # Reorder in days until stock reaches reorder level
                reorder_in_days = max(0.0, round((current_stock - reorder_level) / daily_velocity, 1))
            else:
                days_left = None
                reorder_in_days = None

            forecasts.append({
                'id': p['id'],
                'name': p['name'],
                'sku': p['sku'],
                'stock': current_stock,
                'reorder_level': reorder_level,
                'units_sold_recent': units_sold,
                'avg_daily_sales': round(daily_velocity, 2),
                'days_until_stockout': days_left,
                'reorder_in_days': reorder_in_days,
                'status': 'urgent' if (days_left is not None and days_left <= 3) or current_stock == 0 else ('watch' if (days_left is not None and days_left <= 7) else 'healthy')
            })

        # Sort by urgency
        forecasts.sort(key=lambda x: (
            0 if x['stock'] == 0 else (1 if x['days_until_stockout'] is not None and x['days_until_stockout'] <= 3 else (2 if x['days_until_stockout'] is not None else 3)),
            x['days_until_stockout'] if x['days_until_stockout'] is not None else 999
        ))

        return jsonify(ok=True, forecasts=forecasts, window_days=days_window)


# ---- BONUS TASK: CSV Import / Export ------------------------------------
@app.route("/api/export/csv", methods=['GET'])
def export_csv():
    with db() as conn:
        products = conn.execute("SELECT * FROM products ORDER BY id ASC").fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "sku", "category", "cost", "price", "stock", "reorder_level"])

    for p in products:
        writer.writerow([
            p['id'], p['name'], p['sku'], p['category'],
            p['cost'], p['price'], p['stock'], p['reorder_level']
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=products_inventory.csv"}
    )


@app.route("/api/import/csv", methods=['POST'])
def import_csv():
    csv_text = ""
    if 'file' in request.files:
        file = request.files['file']
        csv_text = file.read().decode('utf-8', errors='ignore')
    elif request.is_json:
        csv_text = request.json.get('csv_text', '')
    else:
        csv_text = request.get_data(as_text=True)

    if not csv_text.strip():
        return jsonify(error="Empty CSV data provided"), 400

    reader = csv.DictReader(io.StringIO(csv_text))
    created = 0
    updated = 0
    errors = []

    with db() as conn:
        for idx, row in enumerate(reader, start=2):
            sku = (row.get('sku') or row.get('SKU') or '').strip().upper()
            name = (row.get('name') or row.get('Name') or '').strip()
            category = (row.get('category') or row.get('Category') or 'General').strip()

            if not sku or not name:
                errors.append(f"Row {idx}: Missing name or SKU")
                continue

            try:
                cost = float(row.get('cost') or row.get('Cost') or 0.0)
                price = float(row.get('price') or row.get('Price') or 0.0)
                stock = int(row.get('stock') or row.get('Stock') or 0)
                reorder = int(row.get('reorder_level') or row.get('reorder') or 5)
            except ValueError:
                errors.append(f"Row {idx} ({sku}): Invalid numeric values")
                continue

            existing = conn.execute("SELECT id, stock FROM products WHERE sku = ?", (sku,)).fetchone()
            if existing:
                prev_stock = existing['stock']
                conn.execute("""
                    UPDATE products
                    SET name = ?, category = ?, cost = ?, price = ?, stock = ?, reorder_level = ?
                    WHERE id = ?
                """, (name, category, cost, price, stock, reorder, existing['id']))
                if stock != prev_stock:
                    conn.execute("""
                        INSERT INTO stock_movements (product_id, movement_type, quantity, prev_stock, new_stock, reference_id, notes)
                        VALUES (?, 'adjustment', ?, ?, ?, 'CSV_IMPORT', 'Updated via CSV import')
                    """, (existing['id'], stock - prev_stock, prev_stock, stock))
                updated += 1
            else:
                cursor = conn.execute("""
                    INSERT INTO products (name, sku, category, cost, price, stock, reorder_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, sku, category, cost, price, stock, reorder))
                pid = cursor.lastrowid
                if stock > 0:
                    conn.execute("""
                        INSERT INTO stock_movements (product_id, movement_type, quantity, prev_stock, new_stock, reference_id, notes)
                        VALUES (?, 'initial', ?, 0, ?, 'CSV_IMPORT', 'Imported initial stock')
                    """, (pid, stock, stock))
                created += 1

    return jsonify(
        ok=True,
        created=created,
        updated=updated,
        errors=errors,
        message=f"CSV Import complete: {created} added, {updated} updated."
    )


# ---- UTILITY: Reset / Seed demo data ------------------------------------
@app.route("/api/seed", methods=['POST'])
def reset_seed():
    with db() as conn:
        conn.execute("DELETE FROM sale_items")
        conn.execute("DELETE FROM sales")
        conn.execute("DELETE FROM stock_movements")
        conn.execute("DELETE FROM products")
        seed_initial_data(conn)
    return jsonify(ok=True, message="Database re-seeded with realistic demo store data!")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=int(os.environ.get("PORT", 5000)))
