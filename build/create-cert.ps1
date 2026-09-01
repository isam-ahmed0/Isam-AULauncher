# create-cert.ps1 — Generate a self-signed code signing certificate for Isam AULauncher
# Run this ONCE from PowerShell. Outputs signing-cert.pfx to ..\release\

$ErrorActionPreference = "Stop"

$subject = "CN=Isam Ahmed"
$validYears = 5
$outDir = Join-Path $PSScriptRoot "..\release"
$outFile = Join-Path $outDir "signing-cert.pfx"

if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

Write-Host ""
Write-Host "=== Isam AULauncher — Self-Signed Code Signing Certificate ===" -ForegroundColor Cyan
Write-Host ""

# Prompt for password
$password = Read-Host -Prompt "Enter a password for the certificate" -AsSecureString
$confirm  = Read-Host -Prompt "Confirm password" -AsSecureString

# Compare passwords
$pwd1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password))
$pwd2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($confirm))

if ($pwd1 -ne $pwd2) {
    Write-Error "Passwords do not match."
    exit 1
}

# Create certificate
Write-Host ""
Write-Host "Creating certificate..." -ForegroundColor Yellow
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject $subject `
    -CertStoreLocation Cert:\CurrentUser\My `
    -NotAfter (Get-Date).AddYears($validYears)

# Export to PFX
Write-Host "Exporting to $outFile ..." -ForegroundColor Yellow
Export-PfxCertificate `
    -Cert "Cert:\CurrentUser\My\$($cert.Thumbprint)" `
    -FilePath $outFile `
    -Password $password | Out-Null

Write-Host ""
Write-Host "Certificate created successfully!" -ForegroundColor Green
Write-Host "  File:      $outFile"
Write-Host "  Thumbprint: $($cert.Thumbprint)"
Write-Host "  Expires:    $($cert.NotAfter)"
Write-Host ""
Write-Host "Next step: run build\sign-installer.bat to sign your installer." -ForegroundColor Cyan
Write-Host ""
