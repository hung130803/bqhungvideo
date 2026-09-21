"""Helper PowerShell: stage + xác minh trước, giữ rollback cho mọi thành phần."""
SWAP_SCRIPT = r'''
param([Parameter(Mandatory=$true)][string]$PlanFile)
$ErrorActionPreference = 'Stop'
$plan = Get-Content -LiteralPath $PlanFile -Raw -Encoding UTF8 | ConvertFrom-Json
$destination = [IO.Path]::GetFullPath($plan.destination).TrimEnd('\')
$source = [IO.Path]::GetFullPath($plan.source).TrimEnd('\')
if (!(Test-Path -LiteralPath $destination -PathType Container)) { throw 'Missing application directory' }
if ($source -eq $destination) { throw 'Source equals destination' }
if ($plan.token -notmatch '^[a-f0-9]{32}$') { throw 'Invalid update token' }
$stage = Join-Path $destination ('.update-stage-' + $plan.token)
$backup = Join-Path $destination ('.update-backup-' + $plan.token)
$log = $PlanFile + '.log'
$journal = @()
$appExited = $false
function Log([string]$message) { Add-Content -LiteralPath $log -Value $message -Encoding UTF8 }
function Under([string]$root, [string]$relative) {
    $full = [IO.Path]::GetFullPath((Join-Path $root $relative))
    if (!$full.StartsWith($root.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escaped application directory' }
    return $full
}
try {
    New-Item -ItemType Directory -Path $stage | Out-Null
    foreach ($child in Get-ChildItem -LiteralPath $source -Force) {
        Copy-Item -LiteralPath $child.FullName -Destination $stage -Recurse
    }
    foreach ($entry in $plan.files.PSObject.Properties) {
        $file = Under $stage $entry.Name
        $stream = [IO.File]::OpenRead($file)
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $actual = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
        finally { $stream.Dispose(); $sha.Dispose() }
        if ($actual -ne $entry.Value) { throw 'Staging checksum mismatch' }
    }
    if (!(Test-Path -LiteralPath (Under $stage $plan.exe) -PathType Leaf)) { throw 'Missing executable' }
    $until = (Get-Date).AddSeconds(240)
    while ($plan.processId -gt 0 -and (Get-Process -Id $plan.processId -ErrorAction SilentlyContinue)) {
        if ((Get-Date) -gt $until) { throw 'Application did not exit' }
        Start-Sleep -Milliseconds 500
    }
    $appExited = $true
    New-Item -ItemType Directory -Path $backup | Out-Null
    foreach ($child in Get-ChildItem -LiteralPath $stage -Force) {
        $target = Under $destination $child.Name
        $old = Under $backup $child.Name
        $item = [pscustomobject]@{target=$target; old=$old; staged=$child.FullName; saved=$false; installed=$false}
        $journal += $item
        if (Test-Path -LiteralPath $target) {
            Move-Item -LiteralPath $target -Destination $old
            $item.saved = $true
        }
        Move-Item -LiteralPath $child.FullName -Destination $target
        $item.installed = $true
        $journal | ConvertTo-Json | Set-Content -LiteralPath ($PlanFile + '.journal') -Encoding UTF8
    }
    Log 'Update complete; previous executable and libraries retained in backup.'
    if ($plan.relaunch) { Start-Process -FilePath (Under $destination $plan.exe) -WorkingDirectory $destination -WindowStyle Hidden }
    exit 0
} catch {
    Log $_.Exception.Message
    $rollbackOk = $true
    [array]::Reverse($journal)
    foreach ($item in $journal) {
        try {
            if ($item.installed -and (Test-Path -LiteralPath $item.target)) {
                Move-Item -LiteralPath $item.target -Destination $item.staged
            }
            if ($item.saved) { Move-Item -LiteralPath $item.old -Destination $item.target }
        } catch { $rollbackOk = $false; Log ('Rollback failed: ' + $_.Exception.Message) }
    }
    if ($appExited -and $rollbackOk -and $plan.relaunch) {
        Start-Process -FilePath (Under $destination $plan.exe) -WorkingDirectory $destination -WindowStyle Hidden
    }
    exit 1
}
'''
