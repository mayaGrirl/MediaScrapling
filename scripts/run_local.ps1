$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    python -m pip install -U uv
}

uv sync --extra dev
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

uv run crawler ui
