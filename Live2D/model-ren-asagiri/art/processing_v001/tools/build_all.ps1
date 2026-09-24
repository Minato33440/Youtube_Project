param([switch]$Verify)
$ErrorActionPreference = 'Stop'
$taskOut = Split-Path $PSScriptRoot -Parent
$taskRepo = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
$taskShared = Join-Path $taskRepo 'output/live2d/risa_parts_v1/tools'
$taskNode = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$taskPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
# This rebuilds generated v001 files. Keep hand-edited PSD/model copies separately.
& python -X utf8 (Join-Path $PSScriptRoot 'prepare_ren.py')
if ($LASTEXITCODE -ne 0) { throw 'Part preparation failed' }
& python -X utf8 (Join-Path $PSScriptRoot 'validate_artifacts.py')
if ($LASTEXITCODE -ne 0) { throw 'Source/part verification failed' }
foreach ($taskView in @('front','back')) {
    $taskManifest = Join-Path $taskOut "$taskView/manifest.json"
    & $taskNode (Join-Path $taskShared 'build_psd.js') $taskManifest
    if ($LASTEXITCODE -ne 0) { throw "PSD build failed: $taskView" }
    if ($Verify) {
        & $taskPython (Join-Path $taskShared 'verify_with_psd_tools.py') $taskManifest (Join-Path $taskOut "$taskView/Ren_${taskView}_parts_v001.psd") (Join-Path $taskOut "$taskView/Ren_${taskView}_parts_v001.png") | Set-Content -Encoding UTF8 (Join-Path $taskOut "$taskView/psd_tools_verification.json")
        if ($LASTEXITCODE -ne 0) { throw "Independent PSD verification failed: $taskView" }
    }
}
