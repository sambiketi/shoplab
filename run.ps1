Write-Host "Starting Vulnerable Shop..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Access: http://localhost:5000" -ForegroundColor Green
Write-Host "Test credentials: admin / admin123" -ForegroundColor Yellow
Write-Host ""
pip install -r requirements.txt
python main.py
