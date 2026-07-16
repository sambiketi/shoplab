import os
from fastapi import FastAPI, Request, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from datetime import datetime
import json
import uuid
import requests

app = FastAPI(title="Vulnerable Shop", debug=True)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-supabase-anon-key-here")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

sessions = {}

def execute_raw_sql(query: str):
    try:
        return supabase.rpc('exec_sql', {'query': query}).execute()
    except Exception as e:
        return None

def search_products_vulnerable(search_term: str):
    query = f"SELECT * FROM products WHERE name LIKE '%{search_term}%' OR description LIKE '%{search_term}%'"
    return execute_raw_sql(query)

def get_user_by_credentials(username: str, password: str):
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    result = execute_raw_sql(query)
    return result.data if result and hasattr(result, 'data') else []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, search: str = Query(None), category: str = Query(None)):
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    if search:
        products = search_products_vulnerable(search)
        products_data = products if isinstance(products, list) else []
    else:
        if category:
            query = f"SELECT * FROM products WHERE category = '{category}' AND is_active = true"
            result = execute_raw_sql(query)
            products_data = result.data if result and hasattr(result, 'data') else []
        else:
            result = supabase.table('products').select('*').eq('is_active', True).execute()
            products_data = result.data if hasattr(result, 'data') else []
    
    categories_result = supabase.table('products').select('category').execute()
    categories = list(set([c.get('category') for c in categories_result.data if c.get('category')]))
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products_data,
        "categories": categories,
        "search": search or '',
        "category": category or '',
        "session": session_data
    })

@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int):
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    product = supabase.table('products').select('*').eq('id', product_id).execute()
    reviews = supabase.table('reviews').select('*').eq('product_id', product_id).execute()
    
    return templates.TemplateResponse("product.html", {
        "request": request,
        "product": product.data[0] if product.data else None,
        "reviews": reviews.data if hasattr(reviews, 'data') else [],
        "session": session_data
    })

@app.post("/add_review/{product_id}")
async def add_review(request: Request, product_id: int, comment: str = Form(...), rating: int = Form(...)):
    user_id = request.cookies.get('user_id', 1)
    review_data = {
        "product_id": product_id,
        "user_id": int(user_id),
        "rating": rating,
        "comment": comment,
        "created_at": datetime.now().isoformat()
    }
    supabase.table('reviews').insert(review_data).execute()
    return RedirectResponse(f"/product/{product_id}", status_code=303)

@app.get("/cart", response_class=HTMLResponse)
async def cart(request: Request):
    session_id = request.cookies.get('session_id', '')
    user_id = request.cookies.get('user_id', '')
    session_data = sessions.get(session_id, {})
    
    if user_id:
        query = f"SELECT * FROM cart WHERE user_id = {user_id}"
        result = execute_raw_sql(query)
        cart_items = result.data if result and hasattr(result, 'data') else []
        for item in cart_items:
            product = supabase.table('products').select('*').eq('id', item['product_id']).execute()
            if product.data:
                item['product'] = product.data[0]
    else:
        query = f"SELECT * FROM cart WHERE session_id = '{session_id}'"
        result = execute_raw_sql(query)
        cart_items = result.data if result and hasattr(result, 'data') else []
    
    total = sum([item.get('product', {}).get('price', 0) * item.get('quantity', 1) for item in cart_items])
    
    return templates.TemplateResponse("cart.html", {
        "request": request,
        "items": cart_items,
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
        cart_data = {"user_id": int(user_id), "product_id": product_id, "quantity": quantity, "added_at": datetime.now().isoformat()}
    else:
        cart_data = {"session_id": session_id, "product_id": product_id, "quantity": quantity, "added_at": datetime.now().isoformat()}
    
    supabase.table('cart').insert(cart_data).execute()
    
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
    
    query = f"SELECT * FROM cart WHERE user_id = {user_id}"
    result = execute_raw_sql(query)
    cart_items = result.data if result and hasattr(result, 'data') else []
    
    for item in cart_items:
        product = supabase.table('products').select('*').eq('id', item['product_id']).execute()
        if product.data:
            item['product'] = product.data[0]
    
    user_query = f"SELECT * FROM users WHERE id = {user_id}"
    user_result = execute_raw_sql(user_query)
    user = user_result.data[0] if user_result and hasattr(user_result, 'data') and user_result.data else None
    
    total = sum([item.get('product', {}).get('price', 0) * item.get('quantity', 1) for item in cart_items])
    
    return templates.TemplateResponse("checkout.html", {
        "request": request,
        "items": cart_items,
        "total": total,
        "user": user,
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
    
    cart_query = f"SELECT * FROM cart WHERE user_id = {user_id}"
    cart_result = execute_raw_sql(cart_query)
    cart_items = cart_result.data if cart_result and hasattr(cart_result, 'data') else []
    
    if not cart_items:
        return JSONResponse({"error": "Cart is empty"}, status_code=400)
    
    total = 0
    order_items = []
    for item in cart_items:
        product = supabase.table('products').select('*').eq('id', item['product_id']).execute()
        if product.data:
            price = product.data[0]['price']
            total += price * item['quantity']
            order_items.append({
                'product_id': item['product_id'],
                'product_name': product.data[0]['name'],
                'quantity': item['quantity'],
                'price_at_time': price
            })
    
    payment_details = {
        'method': payment_method,
        'card_number': card_number,
        'card_expiry': card_expiry,
        'card_cvv': card_cvv,
        'paypal_email': paypal_email
    }
    
    order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{user_id}-{uuid.uuid4().hex[:4].upper()}"
    
    order_data = {
        'order_number': order_number,
        'user_id': int(user_id),
        'total_amount': total,
        'payment_status': 'pending',
        'payment_method': payment_method,
        'payment_details': json.dumps(payment_details),
        'shipping_address': shipping_address,
        'order_date': datetime.now().isoformat(),
        'delivery_status': 'processing'
    }
    
    order = supabase.table('orders').insert(order_data).execute()
    order_id = order.data[0]['id'] if order.data else None
    
    if order_id:
        for item in order_items:
            item_data = {
                'order_id': order_id,
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'quantity': item['quantity'],
                'price_at_time': item['price_at_time'],
                'total': item['quantity'] * item['price_at_time']
            }
            supabase.table('order_items').insert(item_data).execute()
        
        supabase.table('cart').delete().eq('user_id', int(user_id)).execute()
        
        for item in order_items:
            stock_query = f"UPDATE products SET stock_quantity = stock_quantity - {item['quantity']} WHERE id = {item['product_id']}"
            execute_raw_sql(stock_query)
    
    return RedirectResponse(f"/order_confirmation/{order_id}", status_code=303)

@app.get("/order_confirmation/{order_id}", response_class=HTMLResponse)
async def order_confirmation(request: Request, order_id: int):
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    order = supabase.table('orders').select('*, order_items(*, products(*))').eq('id', order_id).execute()
    return templates.TemplateResponse("order_confirmation.html", {
        "request": request,
        "order": order.data[0] if order.data else None,
        "session": session_data
    })

@app.get("/orders", response_class=HTMLResponse)
async def user_orders(request: Request):
    user_id = request.cookies.get('user_id', '')
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    if not user_id:
        return RedirectResponse("/login")
    
    query = f"SELECT * FROM orders WHERE user_id = {user_id} ORDER BY order_date DESC"
    result = execute_raw_sql(query)
    orders_data = result.data if result and hasattr(result, 'data') else []
    
    return templates.TemplateResponse("orders.html", {
        "request": request,
        "orders": orders_data,
        "session": session_data
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    session_id = request.cookies.get('session_id', '')
    session_data = sessions.get(session_id, {})
    
    products = supabase.table('products').select('*').execute()
    orders = supabase.table('orders').select('*, users(username)').execute()
    users = supabase.table('users').select('*').execute()
    stock = supabase.table('products').select('id,name,stock_quantity,price').execute()
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "products": products.data if hasattr(products, 'data') else [],
        "orders": orders.data if hasattr(orders, 'data') else [],
        "users": users.data if hasattr(users, 'data') else [],
        "stock": stock.data if hasattr(stock, 'data') else [],
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
    product_data = {
        'name': name,
        'description': description,
        'price': price,
        'category': category,
        'stock_quantity': stock_quantity,
        'created_at': datetime.now().isoformat(),
        'is_active': True
    }
    supabase.table('products').insert(product_data).execute()
    return RedirectResponse("/admin", status_code=303)

@app.delete("/admin/product/{product_id}")
async def admin_delete_product(product_id: int):
    query = f"DELETE FROM products WHERE id = {product_id}"
    execute_raw_sql(query)
    return JSONResponse({"success": True})

@app.post("/admin/order/{order_id}/status")
async def admin_update_order_status(order_id: int, status: str = Form(...)):
    query = f"UPDATE orders SET delivery_status = '{status}' WHERE id = {order_id}"
    execute_raw_sql(query)
    if status == 'delivered':
        stock_query = f"""
            UPDATE products 
            SET stock_quantity = stock_quantity - (
                SELECT quantity FROM order_items WHERE order_id = {order_id}
            )
            WHERE id IN (
                SELECT product_id FROM order_items WHERE order_id = {order_id}
            )
        """
        execute_raw_sql(stock_query)
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/stock/add")
async def admin_add_stock(product_id: int = Form(...), quantity: int = Form(...)):
    query = f"UPDATE products SET stock_quantity = stock_quantity + {quantity} WHERE id = {product_id}"
    execute_raw_sql(query)
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
    result = get_user_by_credentials(username, password)
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
    users = supabase.table('users').select('id,username,password,email,credit_card_number,credit_card_cvv').execute()
    return JSONResponse({
        "supabase_url": SUPABASE_URL,
        "sessions": sessions,
        "users": users.data if hasattr(users, 'data') else [],
        "cookies": dict(request.cookies)
    })

@app.get("/proxy")
async def proxy(url: str = Query(...)):
    try:
        response = requests.get(url, timeout=5)
        return response.text
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = f"static/uploads/{file.filename}"
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return JSONResponse({"message": f"File uploaded: {file.filename}", "path": file_path})

@app.get("/api/products")
async def api_products():
    products = supabase.table('products').select('*').execute()
    return products.data if hasattr(products, 'data') else []

@app.get("/api/search")
async def api_search(q: str = Query(...)):
    query = f"SELECT * FROM products WHERE name LIKE '%{q}%'"
    result = execute_raw_sql(query)
    return result.data if result and hasattr(result, 'data') else []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
