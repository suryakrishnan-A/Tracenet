# TraceNest PowerShell Restore Script
# Usage: .\scripts\restore.ps1 -BackupFile <path> [-TargetDatabase <dbname>] [-Force]

param (
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [string]$TargetDatabase = "tracenest_restore_test",
    [string]$HostName = "localhost",
    [int]$Port = 5432,
    [string]$Username = "postgres",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
    Write-Host "[ERROR] Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

# Safeguard against accidental production overwrite
if ($TargetDatabase -eq "tracenest" -and -not $Force) {
    Write-Host "[CAUTION] Overwriting production database 'tracenest' requires -Force flag." -ForegroundColor Yellow
    exit 1
}

# Detect psql executable
$PsqlPath = "psql"
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    $CommonPaths = @(
        "C:\Program Files\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\16\bin\psql.exe",
        "C:\Program Files\PostgreSQL\15\bin\psql.exe"
    )
    foreach ($Path in $CommonPaths) {
        if (Test-Path $Path) {
            $PsqlPath = $Path
            break
        }
    }
}

Write-Host "[INFO] Restoring backup to database '$TargetDatabase'..." -ForegroundColor Cyan
Write-Host "[INFO] Source file: $BackupFile"

try {
    # Ensure target database exists; if not, create it
    $CheckDbCmd = "SELECT 1 FROM pg_database WHERE datname='$TargetDatabase'"
    $DbExists = & $PsqlPath -h $HostName -p $Port -U $Username -d postgres -t -c $CheckDbCmd 2>$null
    if (-not ($DbExists -match "1")) {
        Write-Host "[INFO] Creating database '$TargetDatabase'..." -ForegroundColor Cyan
        & $PsqlPath -h $HostName -p $Port -U $Username -d postgres -c "CREATE DATABASE $TargetDatabase;" 2>$null
    }

    # Execute restore using -f parameter
    & $PsqlPath -h $HostName -p $Port -U $Username -d $TargetDatabase -f $BackupFile -q
    if ($LASTEXITCODE -ne 0) {
        throw "psql process returned non-zero exit code: $LASTEXITCODE"
    }

    Write-Host "[SUCCESS] Restore to '$TargetDatabase' completed successfully." -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Restore failed: $_" -ForegroundColor Red
    exit 1
}
