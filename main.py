import os
from fastapi import FastAPI, Request, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import json
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Vulnerable Shop", debug=True)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def execute_query(query: str, params: tuple = None):
    """Execute a query and return results as a list of dicts"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        
        # Check if this is a SELECT query
        if query.strip().upper().startswith('SELECT'):
            result = cur.fetchall()
        else:
            conn.commit()
            result = None
        
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"Database error: {e}")
        return None

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

sessions = {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, search: str = Query(None), category: str = Query(None)):
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    if search:
        query = "SELECT * FROM products WHERE name ILIKE %s OR description ILIKE %s AND is_active = true"
        products_data = execute_query(query, (f"%{search}%", f"%{search}%"))
    elif category:
        query = "SELECT * FROM products WHERE category = %s AND is_active = true"
        products_data = execute_query(query, (category,))
    else:
        query = "SELECT * FROM products WHERE is_active = true"
        products_data = execute_query(query)
    
    categories_query = "SELECT DISTINCT category FROM products WHERE category IS NOT NULL"
    categories_result = execute_query(categories_query)
    categories = [c['category'] for c in categories_result] if categories_result else []
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products_data or [],
        "categories": categories,
        "search": search or '',
        "category": category or '',
        "session": session_data
    })

@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int):
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    product_query = "SELECT * FROM products WHERE id = %s"
    product = execute_query(product_query, (product_id,))
    
    reviews_query = "SELECT * FROM reviews WHERE product_id = %s"
    reviews = execute_query(reviews_query, (product_id,))
    
    return templates.TemplateResponse("product.html", {
        "request": request,
        "product": product[0] if product else None,
        "reviews": reviews or [],
        "session": session_data
    })

@app.post("/add_review/{product_id}")
async def add_review(request: Request, product_id: int, comment: str = Form(...), rating: int = Form(...)):
    user_id = request.cookies.get('user_id', 1)
    query = """
        INSERT INTO reviews (product_id, user_id, rating, comment, created_at) 
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(query, (product_id, int(user_id), rating, comment, datetime.now().isoformat()))
    return RedirectResponse(f"/product/{product_id}", status_code=303)

@app.get("/cart", response_class=HTMLResponse)
async def cart(request: Request):
    session_id = request.cookies.get('session_id', '')
    user_id = request.cookies.get('user_id', '')
    session_data = sessions.get(session_id, {})
    
    if user_id:
        query = """
            SELECT c.*, p.* 
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = %s
        """
        cart_items = execute_query(query, (int(user_id),))
    else:
        query = """
            SELECT c.*, p.* 
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.session_id = %s
        """
        cart_items = execute_query(query, (session_id,))
    
    total = sum([item.get('price', 0) * item.get('quantity', 1) for item in (cart_items or [])])
    
    return templates.TemplateResponse("cart.html", {
        "request": request,
        "items": cart_items or [],
        "total": total,
        "session": session_data
    })

@app.post("/add_to_cart")
async def add_to_cart(request: Request, product_id: int = Form(...), quantity: int = Form(...)):
    session_id = request.cookies.get('session_id', '')
    user_id = request.cookies.get('user_id', '')
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if user_id:
        query = "INSERT INTO cart (user_id, product_id, quantity, added_at) VALUES (%s, %s, %s, %s)"
        execute_query(query, (int(user_id), product_id, quantity, datetime.now().isoformat()))
    else:
        query = "INSERT INTO cart (session_id, product_id, quantity, added_at) VALUES (%s, %s, %s, %s)"
        execute_query(query, (session_id, product_id, quantity, datetime.now().isoformat()))
    
    response = RedirectResponse("/cart", status_code=303)
    response.set_cookie("session_id", session_id)
    return response

@app.get("/checkout", response_class=HTMLResponse)
async def checkout(request: Request):
    user_id = request.cookies.get('user_id', '')
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    if not user_id:
        return RedirectResponse("/login?redirect=/checkout")
    
    query = """
        SELECT c.*, p.* 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = %s
    """
    cart_items = execute_query(query, (int(user_id),))
    
    user_query = "SELECT * FROM users WHERE id = %s"
    user = execute_query(user_query, (int(user_id),))
    
    total = sum([item.get('price', 0) * item.get('quantity', 1) for item in (cart_items or [])])
    
    return templates.TemplateResponse("checkout.html", {
        "request": request,
        "items": cart_items or [],
        "total": total,
        "user": user[0] if user else None,
        "session": session_data
    })

@app.post("/place_order")
async def place_order(
    request: Request,
    shipping_address: str = Form(...),
    payment_method: str = Form(...),
    card_number: str = Form(None),
    card_expiry: str = Form(None),
    card_cvv: str = Form(None),
    paypal_email: str = Form(None)
):
    user_id = request.cookies.get('user_id', '')
    if not user_id:
        return JSONResponse({"error": "Please login first"}, status_code=401)
    
    cart_query = """
        SELECT c.*, p.* 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = %s
    """
    cart_items = execute_query(cart_query, (int(user_id),))
    
    if not cart_items:
        return JSONResponse({"error": "Cart is empty"}, status_code=400)
    
    total = sum([item['price'] * item['quantity'] for item in cart_items])
    
    order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{user_id}-{uuid.uuid4().hex[:4].upper()}"
    
    payment_details = {
        'method': payment_method,
        'card_number': card_number,
        'card_expiry': card_expiry,
        'card_cvv': card_cvv,
        'paypal_email': paypal_email
    }
    
    order_query = """
        INSERT INTO orders (order_number, user_id, total_amount, payment_status, payment_method, payment_details, shipping_address, order_date, delivery_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    order_id = execute_query(order_query, (
        order_number, int(user_id), total, 'pending', payment_method, 
        json.dumps(payment_details), shipping_address, datetime.now().isoformat(), 'processing'
    ))
    
    if order_id:
        order_id_val = order_id[0]['id']
        for item in cart_items:
            item_query = """
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price_at_time, total)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            execute_query(item_query, (
                order_id_val, item['product_id'], item['name'], 
                item['quantity'], item['price'], item['price'] * item['quantity']
            ))
        
        execute_query("DELETE FROM cart WHERE user_id = %s", (int(user_id),))
        
        for item in cart_items:
            stock_query = "UPDATE products SET stock_quantity = stock_quantity - %s WHERE id = %s"
            execute_query(stock_query, (item['quantity'], item['product_id']))
    
    return RedirectResponse(f"/order_confirmation/{order_id_val}", status_code=303)

@app.get("/order_confirmation/{order_id}", response_class=HTMLResponse)
async def order_confirmation(request: Request, order_id: int):
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    query = """
        SELECT o.*, oi.*, p.* 
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE o.id = %s
    """
    order_data = execute_query(query, (order_id,))
    
    return templates.TemplateResponse("order_confirmation.html", {
        "request": request,
        "order": order_data[0] if order_data else None,
        "session": session_data
    })

@app.get("/orders", response_class=HTMLResponse)
async def user_orders(request: Request):
    user_id = request.cookies.get('user_id', '')
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    if not user_id:
        return RedirectResponse("/login")
    
    query = "SELECT * FROM orders WHERE user_id = %s ORDER BY order_date DESC"
    orders_data = execute_query(query, (int(user_id),))
    
    return templates.TemplateResponse("orders.html", {
        "request": request,
        "orders": orders_data or [],
        "session": session_data
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    products = execute_query("SELECT * FROM products")
    orders = execute_query("SELECT o.*, u.username FROM orders o JOIN users u ON o.user_id = u.id")
    users = execute_query("SELECT * FROM users")
    stock = execute_query("SELECT id, name, stock_quantity, price FROM products")
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "products": products or [],
        "orders": orders or [],
        "users": users or [],
        "stock": stock or [],
        "session": session_data,
        "session_count": len(sessions)
    })

@app.post("/admin/product")
async def admin_add_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    stock_quantity: int = Form(...)
):
    query = """
        INSERT INTO products (name, description, price, category, stock_quantity, created_at, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    execute_query(query, (name, description, price, category, stock_quantity, datetime.now().isoformat(), True))
    return RedirectResponse("/admin", status_code=303)

@app.delete("/admin/product/{product_id}")
async def admin_delete_product(product_id: int):
    query = "DELETE FROM products WHERE id = %s"
    execute_query(query, (product_id,))
    return JSONResponse({"success": True})

@app.post("/admin/order/{order_id}/status")
async def admin_update_order_status(order_id: int, status: str = Form(...)):
    query = "UPDATE orders SET delivery_status = %s WHERE id = %s"
    execute_query(query, (status, order_id))
    
    if status == 'delivered':
        stock_query = """
            UPDATE products 
            SET stock_quantity = stock_quantity - (
                SELECT quantity FROM order_items WHERE order_id = %s
            )
            WHERE id IN (
                SELECT product_id FROM order_items WHERE order_id = %s
            )
        """
        execute_query(stock_query, (order_id, order_id))
    
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/stock/add")
async def admin_add_stock(product_id: int = Form(...), quantity: int = Form(...)):
    query = "UPDATE products SET stock_quantity = stock_quantity + %s WHERE id = %s"
    execute_query(query, (quantity, product_id))
    return RedirectResponse("/admin#stock", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, redirect: str = Query(None)):
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    return templates.TemplateResponse("login.html", {
        "request": request,
        "session": session_data,
        "redirect": redirect
    })

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), redirect: str = Form(None)):
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    result = execute_query(query, (username, password))
    
    if result:
        user = result[0]
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            'user_id': user['id'],
            'username': user['username'],
            'is_admin': user.get('is_admin', False)
        }
        response = RedirectResponse(redirect or "/", status_code=303)
        response.set_cookie("session_id", session_id)
        response.set_cookie("user_id", str(user['id']))
        response.set_cookie("username", user['username'])
        response.set_cookie("is_admin", str(user.get('is_admin', False)))
        return response
    else:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials",
            "session": {}
        })

@app.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("session_id")
    response.delete_cookie("user_id")
    response.delete_cookie("username")
    response.delete_cookie("is_admin")
    return response

@app.get("/debug")
async def debug_info(request: Request):
    users = execute_query("SELECT id, username, password, email FROM users")
    return JSONResponse({
        "database_url": "Set in environment",
        "sessions": sessions,
        "users": users or [],
        "cookies": dict(request.cookies)
    })

@app.get("/proxy")
async def proxy(url: str = Query(...)):
    import requests
    try:
        response = requests.get(url, timeout=5)
        return response.text
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = f"static/uploads/{file.filename}"
    os.makedirs("static/uploads", exist_ok=True)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return JSONResponse({"message": f"File uploaded: {file.filename}", "path": file_path})

@app.get("/api/products")
async def api_products():
    products = execute_query("SELECT * FROM products")
    return products or []

@app.get("/api/search")
async def api_search(q: str = Query(...)):
    query = "SELECT * FROM products WHERE name ILIKE %s"
    result = execute_query(query, (f"%{q}%",))
    return result or []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)