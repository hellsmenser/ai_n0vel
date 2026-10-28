param(
    [string]$RenPySdk = 'F:\renpy\renpy-8.3.4-sdk'
)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $RenPySdk 'lib\py3-windows-x86_64\python.exe'
$renpy = Join-Path $RenPySdk 'renpy.py'
$savedir = Join-Path $project 'test-artifacts\gui-small-touch-saves'
$previousVariant = $env:RENPY_VARIANT

try {
    $env:RENPY_VARIANT = 'small touch'
    & $python $renpy --savedir $savedir $project test gui_small_touch_visual
    if ($LASTEXITCODE -ne 0) {
        throw "Small/touch GUI visual testcase failed with exit code $LASTEXITCODE."
    }
}
finally {
    $env:RENPY_VARIANT = $previousVariant
}

Write-Output 'Small/touch GUI visual testcase: PASS'
