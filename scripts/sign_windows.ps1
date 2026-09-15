<#
.SYNOPSIS
    Signs a Windows executable (Authenticode, SHA-256) using a certificate
    already present in the local Windows Certificate Store, then verifies
    the result. Optional step - never required to build EndpointToolbox.exe.

.DESCRIPTION
    Phase 7.2 code signing. Must run strictly AFTER PyInstaller has produced
    the final binary, and nothing may modify the file afterward - any change
    to a signed file invalidates its signature (see docs/CODE_SIGNING.md).

    Steps, in order, any failure stops the script with a non-zero exit code:
      1. Verify the target file exists.
      2. Locate signtool.exe (PATH, then the Windows SDK install locations).
      3. Locate the certificate by thumbprint in the Windows Certificate
         Store (Cert:\CurrentUser\My, then Cert:\LocalMachine\My).
      4. Verify it has an accessible private key.
      5. Verify it carries the Code Signing Enhanced Key Usage
         (1.3.6.1.5.5.7.3.3).
      6. Sign with SHA-256 (never SHA-1).
      7. Apply an RFC 3161 timestamp if -TimestampUrl is supplied. No
         default URL is hardcoded anywhere in this repository - choose one
         from your certificate's issuing CA or an explicitly chosen
         timestamp authority. Signing without a timestamp is allowed, but
         the resulting signature stops being considered valid once the
         certificate expires (see docs/CODE_SIGNING.md, "Timestamp").
      8. Immediately verify the resulting signature (signtool verify /pa /v
         and Get-AuthenticodeSignature).
      9. Exit non-zero if that verification does not report a genuinely
         valid signature.

    Never logs a password or private key: this script only ever references
    a certificate already in the Certificate Store by its thumbprint (not
    secret), never a PFX file or a PFX password.

.PARAMETER Path
    Path to the executable to sign (e.g. dist\EndpointToolbox.exe).

.PARAMETER CertificateThumbprint
    Thumbprint of a Code Signing certificate already present in the local
    Windows Certificate Store. Never hardcoded in this script - always
    supplied by the caller.

.PARAMETER TimestampUrl
    Optional RFC 3161 timestamp server URL. No default: see "Timestamp"
    above and docs/CODE_SIGNING.md.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\sign_windows.ps1 `
        -Path dist\EndpointToolbox.exe `
        -CertificateThumbprint <YOUR-CERTIFICATE-THUMBPRINT> `
        -TimestampUrl <YOUR-CHOSEN-RFC3161-TIMESTAMP-URL>
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Path,

    [Parameter(Mandatory = $true)]
    [string]$CertificateThumbprint,

    [Parameter(Mandatory = $false)]
    [string]$TimestampUrl = ""
)

$ErrorActionPreference = "Stop"

function Fail($message) {
    Write-Error $message
    exit 1
}

if (-not $IsWindows -and $PSVersionTable.PSVersion.Major -ge 6) {
    Fail "sign_windows.ps1 must run on Windows (requires signtool.exe and the Windows Certificate Store)."
}

# 1. Target file exists
$ResolvedPath = Resolve-Path -Path $Path -ErrorAction SilentlyContinue
if (-not $ResolvedPath) {
    Fail "File not found: $Path"
}
$TargetFile = $ResolvedPath.Path
Write-Host "==> Target: $TargetFile"

# 2. Locate signtool.exe
function Find-SignTool {
    $fromPath = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($fromPath) { return $fromPath.Source }

    $sdkRoots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    )
    foreach ($root in $sdkRoots) {
        if ($root -and (Test-Path $root)) {
            $candidates = Get-ChildItem -Path $root -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -match "\\x64\\" } |
                Sort-Object FullName -Descending
            if ($candidates) { return $candidates[0].FullName }
        }
    }
    return $null
}

$SignTool = Find-SignTool
if (-not $SignTool) {
    Fail "signtool.exe not found. Install the Windows SDK (Windows 10/11 SDK, component 'Windows SDK Signing Tools') or add signtool.exe to PATH."
}
Write-Host "==> signtool: $SignTool"

# 3. Locate the certificate by thumbprint
$NormalizedThumbprint = ($CertificateThumbprint -replace '\s', '').ToUpperInvariant()
$cert = Get-ChildItem -Path "Cert:\CurrentUser\My\$NormalizedThumbprint" -ErrorAction SilentlyContinue
if (-not $cert) {
    $cert = Get-ChildItem -Path "Cert:\LocalMachine\My\$NormalizedThumbprint" -ErrorAction SilentlyContinue
}
if (-not $cert) {
    Fail "No certificate with thumbprint $NormalizedThumbprint found in Cert:\CurrentUser\My or Cert:\LocalMachine\My."
}
Write-Host "==> Certificate found: $($cert.Subject)"

# 4. Private key present
if (-not $cert.HasPrivateKey) {
    Fail "Certificate $NormalizedThumbprint has no accessible private key - cannot sign with it."
}

# 5. Code Signing Enhanced Key Usage
$CodeSigningOid = "1.3.6.1.5.5.7.3.3"
$hasCodeSigningEku = $false
foreach ($ext in $cert.Extensions) {
    if ($ext.Oid.Value -eq "2.5.29.37") {
        $eku = [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]$ext
        foreach ($usage in $eku.EnhancedKeyUsages) {
            if ($usage.Value -eq $CodeSigningOid) { $hasCodeSigningEku = $true }
        }
    }
}
if (-not $hasCodeSigningEku) {
    Fail "Certificate $NormalizedThumbprint does not carry the Code Signing Enhanced Key Usage ($CodeSigningOid)."
}

# 6/7. Sign - SHA-256, optional RFC 3161 timestamp
$signArgs = @("sign", "/fd", "sha256", "/sha1", $NormalizedThumbprint)
if ($TimestampUrl) {
    Write-Host "==> Timestamping via: $TimestampUrl"
    $signArgs += @("/tr", $TimestampUrl, "/td", "sha256")
} else {
    Write-Host "==> No -TimestampUrl supplied: signing WITHOUT a timestamp."
    Write-Host "    This signature will stop being considered valid once the certificate expires."
}
$signArgs += $TargetFile

Write-Host "==> Signing with signtool (SHA-256)..."
& $SignTool @signArgs
if ($LASTEXITCODE -ne 0) {
    Fail "signtool sign failed (exit code $LASTEXITCODE)."
}

# 8/9. Verify immediately, fail loudly if not genuinely valid
Write-Host "==> Verifying the resulting signature (signtool verify /pa /v)..."
& $SignTool verify /pa /v $TargetFile
if ($LASTEXITCODE -ne 0) {
    Fail "signtool verify failed after signing (exit code $LASTEXITCODE). The file is signed but signtool does not consider the signature valid - see docs/CODE_SIGNING.md for what this usually means (e.g. an untrusted self-signed certificate)."
}

$sig = Get-AuthenticodeSignature -FilePath $TargetFile
Write-Host "==> Get-AuthenticodeSignature status: $($sig.Status) - $($sig.StatusMessage)"
if ($sig.Status -ne "Valid") {
    Fail "Get-AuthenticodeSignature reports status '$($sig.Status)', not Valid - treating this as a failed signing run."
}

Write-Host ""
Write-Host "==> Signing and verification succeeded."
Write-Host "    Subject:    $($sig.SignerCertificate.Subject)"
Write-Host "    Thumbprint: $($sig.SignerCertificate.Thumbprint)"
if ($sig.TimeStamperCertificate) {
    Write-Host "    Timestamp:  present ($($sig.TimeStamperCertificate.Subject))"
} else {
    Write-Host "    Timestamp:  none"
}
