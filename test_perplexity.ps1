# Test PowerShell Script - Clean Version
param(
    [Parameter(Mandatory=$true)]
    [string]$Query,
    [string]$Mode = "browser",
    [string]$Profile = "fresh",
    [switch]$Research,
    [switch]$DebugMode,
    [switch]$KeepBrowserOpen
)

Write-Host "Test script working!" -ForegroundColor Green
Write-Host "Query: $Query" -ForegroundColor Cyan
Write-Host "Mode: $Mode" -ForegroundColor Cyan
Write-Host "Profile: $Profile" -ForegroundColor Cyan
Write-Host "Research: $Research" -ForegroundColor Cyan
Write-Host "DebugMode: $DebugMode" -ForegroundColor Cyan
Write-Host "KeepBrowserOpen: $KeepBrowserOpen" -ForegroundColor Cyan
