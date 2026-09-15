<#
.SYNOPSIS
    Reproducible build of EndpointToolbox.exe (Windows portable, Phase 7 packaging).

.DESCRIPTION
    Creates/reuses a local virtual environment, installs runtime + build
    dependencies, runs the test suite, then invokes PyInstaller against
    packaging/windows/EndpointToolbox.spec. Fails fast and loudly at the first
    problem - never runs pytest or PyInstaller with continue-on-error.

    Must be run on Windows: PyInstaller does not cross-compile a Windows .exe
    from macOS/Linux. Running this script anywhere else is refused early.

    Contains no credential, Tenant ID or Client ID of any kind, and never talks
    to Microsoft Graph - Test Connection and Support Bundle use existing
    application code, unrelated to this script.

    Optional code signing (Phase 7.2): if the environment variable
    CODESIGN_THUMBPRINT is set, this script signs dist\EndpointToolbox.exe
    with scripts\sign_windows.ps1 as the LAST step, strictly after
    PyInstaller and after nothing else can touch the file - see
    docs/CODE_SIGNING.md. If CODESIGN_THUMBPRINT is not set (the default),
    the build produces an unsigned executable exactly as before; a
    certificate is never required to build EndpointToolbox.exe.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1

.EXAMPLE
    $env:CODESIGN_THUMBPRINT = "<YOUR-CERTIFICATE-THUMBPRINT>"
    $env:CODESIGN_TIMESTAMP_URL = "<YOUR-CHOSEN-RFC3161-TIMESTAMP-URL>"   # optional
    powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
#>

$ErrorActionPreference = "Stop"

function Fail($message) {
    Write-Error $message
    exit 1
}

if (-not $IsWindows -and $PSVersionTable.PSVersion.Major -ge 6) {
    Fail "build_windows.ps1 must run on Windows: PyInstaller does not cross-compile a Windows .exe from another OS."
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "==> Repository root: $RepoRoot"

$VenvDir = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "==> Creating virtual environment at $VenvDir"
    py -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Fail "Failed to create the virtual environment." }
}

Write-Host "==> Installing runtime and build dependencies"
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Fail "pip upgrade failed." }
& $VenvPython -m pip install -r requirements.txt -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { Fail "Dependency installation failed." }

Write-Host "==> Running the test suite (must be green before packaging)"
& $VenvPython -m pytest -q
if ($LASTEXITCODE -ne 0) { Fail "Tests failed - aborting build. Fix the failing tests before packaging." }

Write-Host "==> Byte-compiling the source tree"
& $VenvPython -m compileall main.py app -q
if ($LASTEXITCODE -ne 0) { Fail "compileall reported an error - aborting build." }

Write-Host "==> Running PyInstaller"
& $VenvPython -m PyInstaller --noconfirm --clean packaging\windows\EndpointToolbox.spec
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller build failed." }

$ExePath = Join-Path $RepoRoot "dist\EndpointToolbox.exe"
if (-not (Test-Path $ExePath)) {
    Fail "Build reported success but dist\EndpointToolbox.exe is missing."
}

$SizeMb = [Math]::Round((Get-Item $ExePath).Length / 1MB, 1)
Write-Host "==> Build succeeded: $ExePath ($SizeMb MB)"

if ($env:CODESIGN_THUMBPRINT) {
    Write-Host "==> CODESIGN_THUMBPRINT is set: signing $ExePath (last step, after PyInstaller)"
    $signArgs = @{
        Path                  = $ExePath
        CertificateThumbprint = $env:CODESIGN_THUMBPRINT
    }
    if ($env:CODESIGN_TIMESTAMP_URL) {
        $signArgs["TimestampUrl"] = $env:CODESIGN_TIMESTAMP_URL
    }
    & (Join-Path $PSScriptRoot "sign_windows.ps1") @signArgs
    if ($LASTEXITCODE -ne 0) {
        Fail "Signing failed - see scripts\sign_windows.ps1 output above. The unsigned $ExePath from PyInstaller is unaffected on disk only if signing never partially wrote to it; re-run the build to get a clean unsigned artifact if needed."
    }
    Write-Host "==> Signed and verified: $ExePath"
} else {
    Write-Host "==> CODESIGN_THUMBPRINT not set: $ExePath is UNSIGNED (this is the default and always a valid way to build)."
}

Write-Host "==> Next: follow the manual Windows 11 checklist in docs/PACKAGING.md before distributing this file."
