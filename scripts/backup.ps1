# TraceNest PowerShell Backup Script
# Usage: .\scripts\backup.ps1 [-Database <dbname>] [-OutputDir <path>] [-RetentionDays <days>]

param (
    [string]$Database = "tracenest",
    [string]$HostName = "localhost",
    [int]$Port = 5432,
    [string]$Username = "postgres",
    [string]$OutputDir = "$PSScriptRoot\..\backups",
    [int]$RetentionDays = 14
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$Timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
$BackupFile = Join-Path $OutputDir "tracenest_${Database}_${Timestamp}.sql"

# Detect pg_dump executable
$PgDumpPath = "pg_dump"
if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
    $CommonPaths = @(
        "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe"
    )
    foreach ($Path in $CommonPaths) {
        if (Test-Path $Path) {
            $PgDumpPath = $Path
            break
        }
    }
}

Write-Host "[INFO] Starting backup of database '$Database'..." -ForegroundColor Cyan
Write-Host "[INFO] Output target: $BackupFile"

try {
    # Execute pg_dump (Password handled via PGPASSWORD environment variable or .pgpass)
    & $PgDumpPath -h $HostName -p $Port -U $Username -F p -b -f $BackupFile $Database
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump process returned non-zero exit code: $LASTEXITCODE"
    }

    if ((Test-Path $BackupFile) -and ((Get-Item $BackupFile).Length -gt 0)) {
        $FileSizeKb = [math]::Round((Get-Item $BackupFile).Length / 1KB, 2)
        Write-Host "[SUCCESS] Backup completed successfully ($FileSizeKb KB): $BackupFile" -ForegroundColor Green
    } else {
        throw "Backup file was not created or is 0 bytes."
    }

    # Enforce retention policy
    $LimitDate = (Get-Date).AddDays(-$RetentionDays)
    Get-ChildItem -Path $OutputDir -Filter "tracenest_${Database}_*.sql" | Where-Object { $_.LastWriteTime -lt $LimitDate } | ForEach-Object {
        Remove-Item $_.FullName -Force
        Write-Host "[INFO] Purged expired backup: $($_.Name)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Backup failed: $_" -ForegroundColor Red
    exit 1
}
