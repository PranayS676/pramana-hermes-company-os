# Hermes Company OS local messaging credential loader
# Prompts for secrets locally, writes real Hermes profile .env files, and never
# prints token values. Do not commit populated profile .env files.

param(
  [string]$HermesHome = $(if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA "hermes" }),
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002",
  [switch]$PostDashboardStatus
)

$ErrorActionPreference = "Stop"

$Profiles = @(
  "chief-of-staff",
  "product-manager",
  "research-agent",
  "engineering-manager",
  "backend-engineer",
  "frontend-engineer",
  "cloud-infra-agent",
  "test-automation-agent",
  "marketing-agent",
  "qa-critic"
)

function Read-SecretValue {
  param([string]$Prompt)
  $secure = Read-Host $Prompt -AsSecureString
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
  }
}

function Assert-TokenShape {
  param(
    [string]$Name,
    [string]$Value,
    [string]$Pattern,
    [string]$Hint
  )
  if ([string]::IsNullOrWhiteSpace($Value) -or $Value -notmatch $Pattern) {
    throw "$Name does not look right. Expected $Hint."
  }
}

function Set-EnvValue {
  param(
    [string]$Path,
    [string]$Key,
    [string]$Value
  )
  $directory = Split-Path -Parent $Path
  New-Item -ItemType Directory -Path $directory -Force | Out-Null

  $lines = @()
  if (Test-Path -LiteralPath $Path) {
    $lines = @(Get-Content -LiteralPath $Path)
  }

  $updated = $false
  $escapedKey = [regex]::Escape($Key)
  $next = foreach ($line in $lines) {
    if ($line -match "^\s*$escapedKey\s*=") {
      $updated = $true
      "$Key=$Value"
    } else {
      $line
    }
  }
  if (-not $updated) {
    $next += "$Key=$Value"
  }
  Set-Content -LiteralPath $Path -Value $next -Encoding UTF8
}

Write-Host "This writes Slack tokens to all Hermes profile .env files."
Write-Host "It writes the Telegram bot token only to chief-of-staff."
Write-Host "Token values will not be printed."
Write-Host ""

$slackBotToken = Read-SecretValue "Paste Slack bot token (xoxb...)"
$slackAppToken = Read-SecretValue "Paste Slack app-level token (xapp...)"
$telegramBotToken = Read-SecretValue "Paste Telegram bot token"

Assert-TokenShape `
  -Name "Slack bot token" `
  -Value $slackBotToken `
  -Pattern "^xoxb-.+" `
  -Hint "a value starting with xoxb-"
Assert-TokenShape `
  -Name "Slack app-level token" `
  -Value $slackAppToken `
  -Pattern "^xapp-.+" `
  -Hint "a value starting with xapp-"
Assert-TokenShape `
  -Name "Telegram bot token" `
  -Value $telegramBotToken `
  -Pattern "^\d{6,14}:[A-Za-z0-9_-]{20,}$" `
  -Hint "the numeric BotFather token format"

$profileRoot = Join-Path $HermesHome "profiles"
foreach ($profile in $Profiles) {
  $envPath = Join-Path (Join-Path $profileRoot $profile) ".env"
  Set-EnvValue -Path $envPath -Key "SLACK_BOT_TOKEN" -Value $slackBotToken
  Set-EnvValue -Path $envPath -Key "SLACK_APP_TOKEN" -Value $slackAppToken
  Write-Host "UPDATED $profile Slack credential keys"
}

$chiefEnvPath = Join-Path (Join-Path $profileRoot "chief-of-staff") ".env"
Set-EnvValue -Path $chiefEnvPath -Key "TELEGRAM_BOT_TOKEN" -Value $telegramBotToken
Write-Host "UPDATED chief-of-staff Telegram credential key"

$slackBotToken = $null
$slackAppToken = $null
$telegramBotToken = $null

if ($PostDashboardStatus) {
  Write-Host ""
  Write-Host "Running no-secret dashboard audit and status update..."
  Invoke-WebRequest `
    -UseBasicParsing `
    -Uri "$DashboardBaseUrl/setup/secret-audit.ps1" `
    -OutFile ".\secret-audit.ps1"
  & ".\secret-audit.ps1" -DashboardBaseUrl $DashboardBaseUrl -PostDashboardStatus
}

Write-Host ""
Write-Host "Messaging credentials loaded locally. Values were not printed."
