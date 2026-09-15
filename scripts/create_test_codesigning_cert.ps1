<#
.SYNOPSIS
    Creates a local, clearly-marked TEST Code Signing certificate for Endpoint
    Toolbox development (Phase 7.2).

.DESCRIPTION
    Development / personal-machine / explicitly-trusted-internal-environment
    use ONLY. This is a self-signed certificate: Windows does NOT
    automatically trust it as a publisher on any machine other than one
    where this specific certificate (or an issuing root you control) has
    been explicitly added to the Trusted Root/Trusted Publishers stores -
    see docs/CODE_SIGNING.md, "Certificat auto-signe et postes geres". Never
    present this certificate, or a binary signed with it, as coming from a
    publicly trusted publisher.

    - Uses SHA-256 (never SHA-1).
    - Subject clearly says TEST / DO NOT TRUST - never impersonates
      Microsoft or any third-party company.
    - Stored in Cert:\CurrentUser\My (no administrator rights required).
    - Does NOT export the private key anywhere - it stays in the Windows
      Certificate Store, protected by your Windows user profile. Use
      scripts\sign_windows.ps1 with the printed thumbprint to sign with it.
    - Does NOT touch the Trusted Root or Trusted Publishers stores. Trusting
      this certificate on any machine (including this one) is a separate,
      deliberate step documented in docs/CODE_SIGNING.md - this script does
      not do it for you, silently or otherwise.

    Must run on Windows (New-SelfSignedCertificate is a Windows PKI cmdlet).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\create_test_codesigning_cert.ps1
#>

$ErrorActionPreference = "Stop"

function Fail($message) {
    Write-Error $message
    exit 1
}

if (-not $IsWindows -and $PSVersionTable.PSVersion.Major -ge 6) {
    Fail "create_test_codesigning_cert.ps1 must run on Windows (requires the PKI module's New-SelfSignedCertificate)."
}

$SubjectName = "CN=Endpoint Toolbox TEST Code Signing - DO NOT TRUST, O=Endpoint Toolbox development (not a real company), OU=TEST CERTIFICATE - NOT FOR PRODUCTION USE"

Write-Host "==> Creating a TEST-only, self-signed Code Signing certificate"
Write-Host "    Subject: $SubjectName"
Write-Host ""
Write-Host "    This certificate will NOT be trusted by Windows on this or any other"
Write-Host "    machine by default. It is for development/testing only. See"
Write-Host "    docs/CODE_SIGNING.md before using it for anything beyond your own testing."
Write-Host ""

$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject $SubjectName `
    -KeyAlgorithm RSA `
    -KeyLength 2048 `
    -HashAlgorithm SHA256 `
    -KeyUsage DigitalSignature `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(1)

if (-not $cert) {
    Fail "New-SelfSignedCertificate did not return a certificate."
}

Write-Host "==> Certificate created."
Write-Host "    Thumbprint: $($cert.Thumbprint)"
Write-Host "    Subject:    $($cert.Subject)"
Write-Host "    Stored at:  Cert:\CurrentUser\My\$($cert.Thumbprint)"
Write-Host "    Expires:    $($cert.NotAfter)"
Write-Host ""
Write-Host "The private key was NOT exported. It remains inside your Windows user"
Write-Host "profile's certificate store, protected by your Windows account credentials."
Write-Host ""
Write-Host "To sign a build with this certificate:"
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\sign_windows.ps1 ``"
Write-Host "    -Path dist\EndpointToolbox.exe ``"
Write-Host "    -CertificateThumbprint $($cert.Thumbprint)"
Write-Host ""
Write-Host "This certificate is not trusted anywhere by default. See docs/CODE_SIGNING.md,"
Write-Host "'Certificat auto-signe et postes geres', for how an administrator can choose to"
Write-Host "trust it on a specific test machine - this script deliberately does not do that."
