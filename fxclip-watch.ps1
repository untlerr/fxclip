$ErrorActionPreference = "Continue"

# Optional override from environment.
# Example: setx FXCLIP_CORE "/path/to/fxclip_core.py"
#
# If override is not set, default to fxclip_core.py next to this script.
$scriptDir = Split-Path -Parent $PSCommandPath
$scriptDirUnix = $scriptDir -replace '\\', '/'
$defaultCore = (& wsl.exe wslpath -a "$scriptDirUnix/fxclip_core.py" | Out-String).Trim()
$candidateCores = @($defaultCore)

function Resolve-CorePath {
  param([string[]]$Candidates)

  foreach ($candidate in $Candidates) {
    try {
      wsl.exe -e test -f $candidate | Out-Null
      if ($LASTEXITCODE -eq 0) { return $candidate }
    } catch {}
  }

  return $Candidates[0]
}

$corePath = if ($env:FXCLIP_CORE) { $env:FXCLIP_CORE } else { Resolve-CorePath -Candidates $candidateCores }
$pollMs = 200
$lastHash = ""
$logPath = Join-Path $env:USERPROFILE "fxclip-watch.log"

function Log-Line([string]$msg) {
  try {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    Add-Content -LiteralPath $logPath -Value "[$ts] $msg"
  } catch {}
}

function Get-TextHash([string]$s) {
  if ($null -eq $s) { return "" }
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $hash = $sha.ComputeHash($bytes)
    return [Convert]::ToBase64String($hash)
  } finally {
    $sha.Dispose()
  }
}

try { New-Item -ItemType File -Path $logPath -Force | Out-Null } catch {}
Log-Line "watcher start pid=$PID core=$corePath"

while ($true) {
  try {
    $clip = Get-Clipboard -Raw -TextFormatType Text
  } catch {
    Log-Line "clipboard read failed: $($_.Exception.Message)"
    Start-Sleep -Milliseconds $pollMs
    continue
  }

  if ([string]::IsNullOrWhiteSpace($clip)) {
    Start-Sleep -Milliseconds $pollMs
    continue
  }

  $curHash = Get-TextHash $clip
  if ($curHash -eq $lastHash) {
    Start-Sleep -Milliseconds $pollMs
    continue
  }

  Log-Line "clipboard-change len=$($clip.Length)"

  try {
    $norm = $clip | wsl.exe -e python3 $corePath 2>&1
    $wslExit = $LASTEXITCODE
  } catch {
    Log-Line "wsl exec threw: $($_.Exception.Message)"
    $lastHash = $curHash
    Start-Sleep -Milliseconds $pollMs
    continue
  }

  if ($wslExit -ne 0) {
    $preview = ($norm | Out-String).Trim()
    if ($preview.Length -gt 180) { $preview = $preview.Substring(0, 180) + '...' }
    Log-Line "wsl exit=$wslExit out=$preview"
    $lastHash = $curHash
    Start-Sleep -Milliseconds $pollMs
    continue
  }

  $normText = ($norm | Out-String) -replace "`r`n", "`n"

  if (-not [string]::IsNullOrWhiteSpace($normText) -and $normText -ne $clip) {
    Set-Clipboard -Value $normText
    $lastHash = Get-TextHash $normText
    Log-Line "normalized in_len=$($clip.Length) out_len=$($normText.Length)"
  } else {
    $lastHash = $curHash
    Log-Line "no-change len=$($clip.Length)"
  }

  Start-Sleep -Milliseconds $pollMs
}
