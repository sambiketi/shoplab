Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Vulnerable Shop - Starting..." -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access: http://localhost:5000" -ForegroundColor Green
Write-Host "Test credentials: admin / admin123" -ForegroundColor Yellow
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt
Write-Host ""
Write-Host "Starting application..." -ForegroundColor Cyan
python main.py
