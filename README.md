# Vulnerable Shopping Application

âš ï¸ WARNING: This application contains deliberate security vulnerabilities!
âš ï¸ DO NOT deploy to production!
âš ï¸ For educational purposes only!

## Setup

1. Create Supabase account at https://supabase.com
2. Create a new project
3. Run schema.sql in Supabase SQL editor
4. Update .env with your credentials

## Run

Windows: run.bat
PowerShell: .\run.ps1

## Test Credentials
Username: admin
Password: admin123

## Try These Exploits

SQL Injection: admin' OR '1'='1 --
XSS: <script>alert('XSS')</script>
Path Traversal: /admin?file=../../main.py

## Vulnerabilities Included

- SQL Injection
- XSS (Reflected, Stored, DOM)
- No Authentication
- Plaintext Passwords
- Credit Card Storage
- IDOR
- SSRF
- Command Injection
- Path Traversal
- CSRF
- Information Disclosure
- Unrestricted File Upload
