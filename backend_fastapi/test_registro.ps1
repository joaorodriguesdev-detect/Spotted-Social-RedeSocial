#!/usr/bin/env powershell
"""Test registration endpoint with detailed logging."""

$apiUrl = "http://127.0.0.1:8000"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$testUsername = "testuser_$timestamp"

Write-Host "`n════════════════════════════════════════════════════"
Write-Host "🧪 TESTE DE REGISTRO - DIAGNOSTIC" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "📝 Dados de teste:" -ForegroundColor Yellow
Write-Host "   Username: $testUsername"
Write-Host "   URL: $apiUrl/auth/registro"
Write-Host ""

$body = @{
    username = $testUsername
    password = "Test@1234"
    name = "Test User"
    university = "Test University"
} | ConvertTo-Json

Write-Host "📤 Enviando requisição POST..." -ForegroundColor Green

try {
    $response = Invoke-WebRequest `
        -Uri "$apiUrl/auth/registro" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -UseBasicParsing

    Write-Host "✅ Sucesso! Status Code:" $response.StatusCode -ForegroundColor Green
    Write-Host "`n📋 Resposta:"
    $response.Content | ConvertFrom-Json | ConvertTo-Json | Write-Host -ForegroundColor Green
} catch {
    Write-Host "❌ Erro na requisição!" -ForegroundColor Red
    Write-Host "   Status Code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    Write-Host "   Mensagem: $($_.Exception.Message)" -ForegroundColor Red

    if ($_.ErrorDetails) {
        Write-Host "`n📋 Detalhes de Erro:"
        $_.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json | Write-Host -ForegroundColor Red
    }
}

Write-Host "`n════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "💡 Verifique o terminal do FastAPI para os logs:" -ForegroundColor Yellow
Write-Host "   - [REGISTRO] Mensagens de debug" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════`n" -ForegroundColor Cyan

