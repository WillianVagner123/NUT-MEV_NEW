param(
    [string]$Repository = "",
    [string]$ConfigPath = "",
    [switch]$ValidateOnly,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

if (-not $ConfigPath) {
    $ConfigPath = Join-Path $PSScriptRoot "..\.github\rulesets\main.json"
}
$ConfigPath = (Resolve-Path $ConfigPath).Path
$raw = Get-Content -Raw -Encoding UTF8 $ConfigPath
$config = $raw | ConvertFrom-Json

function Assert-Config {
    param($Ruleset)

    if ($Ruleset.name -ne "Protect main") { throw "Unexpected ruleset name: $($Ruleset.name)" }
    if ($Ruleset.target -ne "branch") { throw "Ruleset target must be branch" }
    if ($Ruleset.enforcement -ne "active") { throw "Ruleset enforcement must be active" }
    if (-not ($Ruleset.conditions.ref_name.include -contains "refs/heads/main")) {
        throw "Ruleset must include refs/heads/main"
    }

    $types = @($Ruleset.rules | ForEach-Object { $_.type })
    foreach ($requiredType in @("deletion", "non_fast_forward", "pull_request", "required_status_checks")) {
        if (-not ($types -contains $requiredType)) {
            throw "Missing required rule type: $requiredType"
        }
    }

    $statusRule = $Ruleset.rules | Where-Object { $_.type -eq "required_status_checks" } | Select-Object -First 1
    if (-not $statusRule.parameters.strict_required_status_checks_policy) {
        throw "strict_required_status_checks_policy must be true"
    }
    if (@($statusRule.parameters.required_status_checks).Count -lt 1) {
        throw "At least one required status check is required"
    }
}

Assert-Config $config
Write-Host "Ruleset config validated: $ConfigPath"

if ($ValidateOnly) {
    exit 0
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required. Install it and run gh auth login first."
}

& gh auth status 1>$null
if ($LASTEXITCODE -ne 0) {
    throw "gh is not authenticated. Run: gh auth login"
}

if (-not $Repository) {
    $Repository = (& gh repo view --json nameWithOwner --jq '.nameWithOwner').Trim()
}
if (-not $Repository -or $Repository -notmatch '^[^/]+/[^/]+$') {
    throw "Could not resolve repository owner/name. Pass -Repository owner/name explicitly."
}

$headers = @(
    "Accept: application/vnd.github+json",
    "X-GitHub-Api-Version: 2026-03-10"
)

function Invoke-GhJson {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Endpoint,
        [string]$InputPath = ""
    )

    $args = @("api", "--method", $Method)
    foreach ($header in $headers) {
        $args += @("-H", $header)
    }
    $args += $Endpoint
    if ($InputPath) {
        $args += @("--input", $InputPath)
    }
    $output = & gh @args
    if ($LASTEXITCODE -ne 0) {
        throw "gh api failed: $Method $Endpoint"
    }
    if (-not $output) { return $null }
    return ($output | Out-String | ConvertFrom-Json)
}

$existing = Invoke-GhJson -Method GET -Endpoint "repos/$Repository/rulesets?per_page=100"
$match = @($existing) | Where-Object { $_.name -eq $config.name -and $_.target -eq "branch" } | Select-Object -First 1

if (-not $VerifyOnly) {
    if ($match) {
        Write-Host "Updating existing ruleset '$($config.name)' (id=$($match.id))..."
        $null = Invoke-GhJson -Method PUT -Endpoint "repos/$Repository/rulesets/$($match.id)" -InputPath $ConfigPath
    }
    else {
        Write-Host "Creating ruleset '$($config.name)'..."
        $null = Invoke-GhJson -Method POST -Endpoint "repos/$Repository/rulesets" -InputPath $ConfigPath
    }
}

$effective = Invoke-GhJson -Method GET -Endpoint "repos/$Repository/rules/branches/main"
if (@($effective).Count -eq 0) {
    throw "No effective rules are reported for main. The protection was not applied."
}

$rulesetsAfter = Invoke-GhJson -Method GET -Endpoint "repos/$Repository/rulesets?per_page=100"
$active = @($rulesetsAfter) | Where-Object { $_.name -eq $config.name -and $_.target -eq "branch" -and $_.enforcement -eq "active" } | Select-Object -First 1
if (-not $active) {
    throw "The canonical main ruleset is not active."
}

Write-Host "main protection is ACTIVE. Ruleset id=$($active.id)"
Write-Host "Effective rule count: $(@($effective).Count)"
