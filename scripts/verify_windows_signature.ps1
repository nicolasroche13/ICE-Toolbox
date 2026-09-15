<#
.SYNOPSIS
    Verifies the Authenticode signature of a Windows executable and reports
    an unambiguous classification.

.DESCRIPTION
    Standalone check, independent of sign_windows.ps1 (which already
    verifies immediately after signing) - use this to re-check a binary
    later, e.g. a downloaded EndpointToolbox.exe or a CI artifact. Runs both
    Get-AuthenticodeSignature and, when signtool.exe is available,
    `signtool verify /pa /v`, and classifies the result as one of:
    UNSIGNED, VALID, INVALID, UNKNOWN/UNTRUSTED CERTIFICATE, or a
    timestamp-related note when the certificate has expired without one.

    Exits 0 only when the signature is genuinely Valid; exits 1 otherwise
    (including "unsigned" - callers that only want to warn, not fail,
    should inspect the printed classification instead of relying solely on
    the exit code).

.PARAMETER Path
    Path to the executable to verify.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\verify_windows_signature.ps1 -Path dist\EndpointToolbox.exe
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows -and $PSVersionTable.PSVersion.Major -ge 6) {
    Write-Error "verify_windows_signature.ps1 must run on Windows."
    exit 1
}

$ResolvedPath = Resolve-Path -Path $Path -ErrorAction SilentlyContinue
if (-not $ResolvedPath) {
    Write-Error "File not found: $Path"
    exit 1
}
$TargetFile = $ResolvedPath.Path

$sig = Get-AuthenticodeSignature -FilePath $TargetFile
Write-Host "==> Get-AuthenticodeSignature status: $($sig.Status) - $($sig.StatusMessage)"

$classification = switch ($sig.Status) {
    "NotSigned"   { "UNSIGNED" }
    "Valid"       { "VALID" }
    "HashMismatch" { "INVALID (file was modified after signing)" }
    "NotTrusted"  { "UNKNOWN/UNTRUSTED CERTIFICATE" }
    "UnknownError" { "INVALID/UNKNOWN" }
    default       { "UNKNOWN ($($sig.Status))" }
}
Write-Host "==> Classification: $classification"

if ($sig.SignerCertificate) {
    $expired = (Get-Date) -gt $sig.SignerCertificate.NotAfter
    if ($expired -and -not $sig.TimeStamperCertificate) {
        Write-Host "==> Certificate has expired and no timestamp is present: this signature is treated as EXPIRED, not valid, per Authenticode rules."
    } elseif ($expired -and $sig.TimeStamperCertificate) {
        Write-Host "==> Certificate has expired, but a timestamp is present: the signature can still be considered valid for the timestamped signing time."
    }
}

$signToolCmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
if ($signToolCmd) {
    Write-Host "==> Running signtool verify /pa /v ..."
    & $signToolCmd.Source verify /pa /v $TargetFile
    Write-Host "==> signtool exit code: $LASTEXITCODE (0 = verified)"
} else {
    Write-Host "==> signtool.exe not found on PATH - skipping the signtool cross-check (Get-AuthenticodeSignature result above still applies)."
}

if ($sig.Status -ne "Valid") {
    exit 1
}
exit 0
