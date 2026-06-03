$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$appName = "lan-sleep-panel"
$distDir = Join-Path $root "dist"
$buildDir = Join-Path $distDir $appName
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipFile = Join-Path $distDir "$appName-$stamp.zip"

if (Test-Path $buildDir) {
    Remove-Item -LiteralPath $buildDir -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $distDir | Out-Null
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $buildDir "static") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $buildDir "templates") | Out-Null

$files = @(
    ".env.example",
    "LICENSE",
    "NOTICE",
    "README.md",
    "app.py",
    "config.py",
    "requirements.txt",
    "tray_app.py"
)

foreach ($file in $files) {
    Copy-Item -LiteralPath (Join-Path $root $file) -Destination (Join-Path $buildDir $file) -Force
}

Get-ChildItem -LiteralPath $root -Filter "*.bat" -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $buildDir $_.Name) -Force
}

$staticFiles = @(
    "app.js",
    "icon.svg",
    "manifest.webmanifest",
    "service-worker.js"
)

foreach ($file in $staticFiles) {
    Copy-Item -LiteralPath (Join-Path $root "static\$file") -Destination (Join-Path $buildDir "static\$file") -Force
}

$templateFiles = @(
    "dashboard.html",
    "login.html"
)

foreach ($file in $templateFiles) {
    Copy-Item -LiteralPath (Join-Path $root "templates\$file") -Destination (Join-Path $buildDir "templates\$file") -Force
}

if (Test-Path $zipFile) {
    Remove-Item -LiteralPath $zipFile -Force
}

Compress-Archive -Path (Join-Path $buildDir "*") -DestinationPath $zipFile -Force

Write-Host ""
Write-Host "Release package created:"
Write-Host $zipFile
Write-Host ""
Write-Host "You can upload this ZIP file to GitHub Releases."
