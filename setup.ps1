#Requires -Version 5.1
<#
.SYNOPSIS
    One-click setup for linux_board_mcp on Windows.

.DESCRIPTION
    Steps:
      1. Ensure `uv` is installed (auto-install via official script if missing)
      2. Run `uv sync` to create .venv and install dependencies + the project itself
      3. Generate mcp.json from mcp.template.json with absolute paths filled in
      4. Verify the server can be imported

    Run from PowerShell:
        .\setup.ps1
    Or double-click setup.bat.

.PARAMETER SkipUvInstall
    Don't try to auto-install uv. Fail if it's missing.

.PARAMETER NoVerify
    Skip the final import-verification step.
#>

[CmdletBinding()]
param(
    [switch]$SkipUvInstall,
    [switch]$NoVerify
)

$ErrorActionPreference = 'Stop'

# Resolve project directory (the folder this script lives in).
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

function Write-Step($num, $msg) {
    Write-Host ""
    Write-Host "[$num] $msg" -ForegroundColor Cyan
}

function Write-Ok($msg) {
    Write-Host "    OK: $msg" -ForegroundColor Green
}

function Write-Warn2($msg) {
    Write-Host "    WARN: $msg" -ForegroundColor Yellow
}

function Test-UvAvailable {
    try {
        $null = & uv --version 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

# ----- 1. Ensure uv is available -----

Write-Step "1/4" "checking for uv"

if (Test-UvAvailable) {
    Write-Ok "uv already installed ($(& uv --version))"
} elseif ($SkipUvInstall) {
    Write-Error "uv not found and -SkipUvInstall passed. Install from https://docs.astral.sh/uv/"
    exit 1
} else {
    Write-Host "    uv not found, installing via https://astral.sh/uv/install.ps1 ..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    } catch {
        Write-Error "uv installer failed: $_"
        Write-Error "Manual install: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
    # The installer adds uv to PATH for new sessions; surface it for this one too.
    $uvBin = Join-Path $env:USERPROFILE ".local\bin"
    if (Test-Path $uvBin) {
        $env:Path = "$uvBin;$env:Path"
    }
    if (-not (Test-UvAvailable)) {
        Write-Error "uv installation finished but `uv` still isn't on PATH. Open a new terminal and re-run setup.ps1."
        exit 1
    }
    Write-Ok "uv installed ($(& uv --version))"
}

# ----- 2. Sync dependencies into .venv -----

Write-Step "2/4" "running 'uv sync' (creates .venv, installs deps + project)"

& uv sync
if ($LASTEXITCODE -ne 0) {
    Write-Error "uv sync failed (exit $LASTEXITCODE). Re-run with -Verbose to see what broke."
    exit 1
}
Write-Ok ".venv ready, dependencies installed"

# ----- 3. Generate mcp.json from template -----

Write-Step "3/4" "generating mcp.json with absolute project path"

$templatePath = Join-Path $projectDir "mcp.template.json"
$outPath      = Join-Path $projectDir "mcp.json"

if (-not (Test-Path $templatePath)) {
    Write-Error "mcp.template.json missing — repo is incomplete"
    exit 1
}

# JSON requires backslashes to be escaped, so emit \\ separators.
$absForJson = $projectDir.Replace('\', '\\')
$content = Get-Content -Raw -Path $templatePath
$content = $content.Replace('{{PROJECT_DIR}}', $absForJson)

# Write UTF-8 without BOM (PowerShell 5.1's `Set-Content -Encoding UTF8` adds BOM
# which trips some JSON parsers).
[System.IO.File]::WriteAllText($outPath, $content, [System.Text.UTF8Encoding]::new($false))
Write-Ok "wrote $outPath"

# ----- 4. Verify imports -----

if ($NoVerify) {
    Write-Step "4/4" "skipping verify (-NoVerify)"
} else {
    Write-Step "4/4" "verifying the server can be imported"
    & uv run python -c "import linux_board_mcp; from linux_board_mcp.server import build_server; from linux_board_mcp.config import Config; print('linux_board_mcp', linux_board_mcp.__version__, 'OK')"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "import check failed"
        exit 1
    }
}

# ----- Done -----

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " linux_board_mcp setup complete" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project dir: $projectDir"
Write-Host "Config file: $outPath"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Open mcp.json and edit BOARD_HOST / BOARD_KEY / ADB_WIFI_HOST etc"
Write-Host "     for the transport you want (ssh / adb-usb / adb-wifi)."
Write-Host ""
Write-Host "  2. Hook it into Claude Code, one of these ways:"
Write-Host "       a) Copy mcp.json into your embedded project root as `".mcp.json`":"
Write-Host "          copy `"$outPath`" <your_project>\.mcp.json"
Write-Host "       b) Or launch claude with --mcp-config:"
Write-Host "          claude --mcp-config `"$outPath`""
Write-Host ""
Write-Host "  3. Smoke test without Claude:"
Write-Host "       cd `"$projectDir`""
Write-Host "       uv run python -m linux_board_mcp"
Write-Host "     (it should print a 'ready' line to stderr and wait on stdin)"
Write-Host ""
