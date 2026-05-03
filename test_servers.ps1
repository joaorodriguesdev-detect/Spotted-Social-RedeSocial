#!/usr/bin/env powershell

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  TESTE DE FRONTEND - SPOTTED SOCIAL" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Teste 1: Backend API
Write-Host "[1/3] Testando Backend API..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Backend API respondendo em http://127.0.0.1:8000" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Backend não respondendo" -ForegroundColor Red
}

Write-Host ""

# Teste 2: Frontend
Write-Host "[2/3] Testando Frontend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:3000/" -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Frontend respondendo em http://127.0.0.1:3000" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Frontend não respondendo" -ForegroundColor Red
}

Write-Host ""

# Teste 3: Porta listening
Write-Host "[3/3] Verificando portas..." -ForegroundColor Yellow
$ports = netstat -an | Select-String -Pattern "3000|8000" | Measure-Object
if ($ports.Count -gt 0) {
    Write-Host "✅ Portas 3000 e 8000 estão ativas" -ForegroundColor Green
    Write-Host ""
    Write-Host "Abra o navegador e acesse: http://localhost:3000" -ForegroundColor Cyan
} else {
    Write-Host "❌ Portas não estão respondendo" -ForegroundColor Red
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  VERIFICAÇÃO CONCLUÍDA" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

