from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

THUMBPRINT_LIKE = re.compile(r"\b[0-9A-Fa-f]{40}\b")


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8")


def test_build_script_signing_is_optional_and_env_gated():
    content = _read("scripts/build_windows.ps1")
    assert "CODESIGN_THUMBPRINT" in content
    assert "if ($env:CODESIGN_THUMBPRINT)" in content
    assert "UNSIGNED" in content


def test_build_script_never_hardcodes_a_thumbprint_or_a_real_url():
    content = _read("scripts/build_windows.ps1")
    assert not THUMBPRINT_LIKE.search(content), "a 40-hex-char string looks like a hardcoded thumbprint"
    assert "http://" not in content and "https://" not in content


def test_sign_script_refuses_missing_file():
    content = _read("scripts/sign_windows.ps1")
    assert "Resolve-Path" in content
    assert "File not found" in content


def test_sign_script_uses_sha256_never_sha1_for_the_file_digest():
    content = _read("scripts/sign_windows.ps1")
    assert '"/fd", "sha256"' in content
    assert '"/fd", "sha1"' not in content
    assert "/fd sha1" not in content.lower()


def test_sign_script_never_hardcodes_thumbprint_or_timestamp_url():
    content = _read("scripts/sign_windows.ps1")
    assert "[string]$CertificateThumbprint" in content
    assert not THUMBPRINT_LIKE.search(content), "a 40-hex-char string looks like a hardcoded thumbprint"
    assert '$TimestampUrl = ""' in content
    assert "http://" not in content and "https://" not in content


def test_sign_script_verifies_immediately_and_can_fail_non_zero():
    content = _read("scripts/sign_windows.ps1")
    assert "Get-AuthenticodeSignature" in content
    assert "signtool" in content.lower()
    assert "exit 1" in content


def test_verify_script_exists_and_classifies_status_unambiguously():
    content = _read("scripts/verify_windows_signature.ps1")
    for keyword in ("UNSIGNED", "VALID", "INVALID", "UNTRUSTED"):
        assert keyword in content


def test_create_test_cert_script_never_impersonates_microsoft_or_a_third_party():
    content = _read("scripts/create_test_codesigning_cert.ps1")
    assert "TEST" in content
    assert "DO NOT TRUST" in content
    lowered = content.lower()
    assert "microsoft corporation" not in lowered
    assert "o=microsoft" not in lowered


def test_create_test_cert_script_does_not_export_the_private_key():
    content = _read("scripts/create_test_codesigning_cert.ps1")
    assert "Export-PfxCertificate" not in content
    assert "-Type CodeSigningCert" in content
    assert "SHA256" in content


def test_codesigning_scripts_never_touch_trusted_root_or_publisher_stores():
    for relpath in (
        "scripts/create_test_codesigning_cert.ps1",
        "scripts/sign_windows.ps1",
        "scripts/verify_windows_signature.ps1",
    ):
        content = _read(relpath)
        assert "Cert:\\CurrentUser\\Root" not in content
        assert "Cert:\\LocalMachine\\Root" not in content
        assert "TrustedPublisher" not in content
        assert "Import-Certificate" not in content


def test_github_workflow_signing_step_is_gated_by_a_variable_not_a_secret():
    content = _read(".github/workflows/windows-build.yml")
    assert "vars.CODESIGN_THUMBPRINT" in content
    assert "secrets.CODESIGN" not in content
    assert ".pfx" not in content.lower()
    assert "base64" not in content.lower()


def test_github_workflow_still_builds_and_uploads_unsigned_by_default():
    content = _read(".github/workflows/windows-build.yml")
    assert "Build with PyInstaller" in content
    assert "Upload EndpointToolbox.exe artifact" in content
    assert "if: ${{ vars.CODESIGN_THUMBPRINT != '' }}" in content


def test_gitignore_excludes_private_key_material_but_not_public_certs():
    content = _read(".gitignore")
    assert "*.pfx" in content
    assert "*.p12" in content
    assert "*.key" in content
    assert "*.cer" not in content
    assert "*.crt" not in content


def test_no_private_key_material_is_tracked_by_git():
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = result.stdout.splitlines()
    forbidden_suffixes = (".pfx", ".p12", ".key")
    offenders = [f for f in tracked if f.lower().endswith(forbidden_suffixes)]
    assert offenders == []


def test_no_tracked_file_contains_a_pem_private_key_marker():
    # Markers built at runtime (never written literally in this source file)
    # so this very test - and any prose mentioning the marker by name, e.g.
    # docs/TESTING.md, docs/CODE_SIGNING.md - never false-positives itself.
    # The literal dashed PEM header only ever appears in an actual key block.
    dashes = "-" * 5
    key_types = ("", "RSA ", "ENCRYPTED ")
    for key_type in key_types:
        marker = f"{dashes}BEGIN {key_type}PRIVATE KEY{dashes}"
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "grep", "-l", "-e", marker],
            capture_output=True,
            text=True,
        )
        assert result.returncode in (0, 1)  # 1 = no matches found, the expected/passing case
        assert result.stdout.strip() == "", f"found tracked file(s) containing a private key marker: {result.stdout}"


def test_code_signing_documentation_exists_and_covers_key_topics():
    content = _read("docs/CODE_SIGNING.md")
    for heading in ("Timestamp", "SmartScreen", "GitHub Actions", "auto-signe"):
        assert heading in content
