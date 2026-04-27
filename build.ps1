$ErrorActionPreference = "Stop"

$PluginName = "krita_ai_metadata"
$DesktopFile = "$PluginName.desktop"
$OutZip = "$PluginName.zip"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

if (-not (Test-Path -Path $PluginName -PathType Container)) {
	throw "Missing plugin folder: $PluginName/"
}

if (-not (Test-Path -Path $DesktopFile -PathType Leaf)) {
	throw "Missing desktop file: $DesktopFile"
}

if (Test-Path $OutZip) {
	Remove-Item $OutZip -Force
}

$TempDir = Join-Path $RootDir ".build_krita_ai_metadata_zip"

if (Test-Path $TempDir) {
	Remove-Item $TempDir -Recurse -Force
}

New-Item -ItemType Directory -Path $TempDir | Out-Null

Copy-Item $DesktopFile -Destination $TempDir
Copy-Item $PluginName -Destination $TempDir -Recurse

$ExcludedDirs = @(
	"__pycache__",
	".pytest_cache",
	".mypy_cache",
	".ruff_cache"
)

Get-ChildItem $TempDir -Recurse -Force -Directory |
	Where-Object { $ExcludedDirs -contains $_.Name } |
	Remove-Item -Recurse -Force

Get-ChildItem $TempDir -Recurse -Force -File |
	Where-Object {
		$_.Extension -in @(".pyc", ".pyo", ".pyd", ".log", ".tmp", ".bak")
	} |
	Remove-Item -Force

Compress-Archive -Path (Join-Path $TempDir "*") -DestinationPath $OutZip -Force

Remove-Item $TempDir -Recurse -Force

Write-Host "Built $OutZip"
Write-Host "ZIP root contains:"
Write-Host "- $PluginName/"
Write-Host "- $DesktopFile"