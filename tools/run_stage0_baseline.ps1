[CmdletBinding()]
param(
    [string]$SdkRoot = 'F:\renpy\renpy-8.3.4-sdk',
    [ValidateRange(45, 600)]
    [int]$CaseTimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sdkRoot = (Resolve-Path $SdkRoot).Path
$pythonExe = Join-Path $sdkRoot 'lib\py3-windows-x86_64\python.exe'
$renpyPy = Join-Path $sdkRoot 'renpy.py'

foreach ($requiredPath in @($pythonExe, $renpyPy)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required Ren'Py SDK file was not found: $requiredPath"
    }
}

$artifactRoot = Join-Path $repoRoot 'test-artifacts\stage0'
$saveRoot = Join-Path $repoRoot 'test-artifacts\saves'
New-Item -ItemType Directory -Force -Path $artifactRoot, $saveRoot | Out-Null

function Quote-ProcessArgument([string]$Value) {
    return '"' + ($Value -replace '"', '\"') + '"'
}

function Get-RelativeArtifactPath([string]$Path) {
    return $Path.Substring($repoRoot.Length).TrimStart('\')
}

function Copy-FreshDiagnostics([datetime]$CaseStartUtc, [string]$CaseArtifactDirectory) {
    $copied = @()
    foreach ($name in @('traceback.txt', 'errors.txt', 'log.txt')) {
        $source = Join-Path $repoRoot $name
        if ((Test-Path -LiteralPath $source -PathType Leaf) -and ((Get-Item -LiteralPath $source).LastWriteTimeUtc -ge $CaseStartUtc)) {
            $target = Join-Path $CaseArtifactDirectory $name
            Copy-Item -LiteralPath $source -Destination $target -Force
            $copied += $target
        }
    }
    return $copied
}

function Invoke-RenPyProcess([string]$Name, [string[]]$RenpyArguments, [int]$TimeoutSeconds = 0, [string]$ExecutablePath = $pythonExe) {
    if ($TimeoutSeconds -le 0) {
        $TimeoutSeconds = $CaseTimeoutSeconds
    }
    $caseDirectory = Join-Path $artifactRoot $Name
    $artifactPrefix = [System.IO.Path]::GetFullPath($artifactRoot).TrimEnd('\') + '\'
    $resolvedCaseDirectory = [System.IO.Path]::GetFullPath($caseDirectory)
    if (-not $resolvedCaseDirectory.StartsWith($artifactPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean artifact directory outside the runner root: $resolvedCaseDirectory"
    }
    if (Test-Path -LiteralPath $resolvedCaseDirectory -PathType Container) {
        # Clear only this named case's artifacts, never the shared artifact root.
        Get-ChildItem -LiteralPath $resolvedCaseDirectory -Force | Remove-Item -Recurse -Force
    }
    else {
        New-Item -ItemType Directory -Path $resolvedCaseDirectory | Out-Null
    }
    $caseDirectory = $resolvedCaseDirectory

    $stdoutPath = Join-Path $caseDirectory 'stdout.txt'
    $stderrPath = Join-Path $caseDirectory 'stderr.txt'
    $startedUtc = (Get-Date).ToUniversalTime()
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $argumentLine = (($RenpyArguments | ForEach-Object { Quote-ProcessArgument $_ }) -join ' ')
    $process = Start-Process -FilePath $ExecutablePath -ArgumentList $argumentLine -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

    $finished = $process.WaitForExit($TimeoutSeconds * 1000)
    if (-not $finished) {
        # This is the exact child process started above; do not touch unrelated Ren'Py processes.
        Stop-Process -Id $process.Id -Force
        $process.WaitForExit()
    }
    else {
        # Flush redirected output and refresh the Process object before reading ExitCode.
        $process.WaitForExit()
        $process.Refresh()
    }
    $timer.Stop()

    $diagnostics = Copy-FreshDiagnostics -CaseStartUtc $startedUtc -CaseArtifactDirectory $caseDirectory
    return [pscustomobject]@{
        Name = $Name
        ExitCode = if ($finished) { [int]$process.ExitCode } else { $null }
        TimedOut = -not $finished
        DurationSeconds = [Math]::Round($timer.Elapsed.TotalSeconds, 3)
        StartedUtc = $startedUtc.ToString('o')
        StdoutPath = Get-RelativeArtifactPath $stdoutPath
        StderrPath = Get-RelativeArtifactPath $stderrPath
        DiagnosticPaths = @($diagnostics | ForEach-Object { Get-RelativeArtifactPath $_ })
        ArtifactDirectory = Get-RelativeArtifactPath $caseDirectory
    }
}

function Test-LocalMongoPort {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect('127.0.0.1', 27017, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(500)) { return $false }
        $client.EndConnect($async)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Get-TracebackText([object]$ProcessResult) {
    $traceRelativePath = $ProcessResult.DiagnosticPaths | Where-Object { $_ -match '(^|\\)traceback\.txt$' } | Select-Object -First 1
    if (-not $traceRelativePath) {
        return ''
    }
    $tracePath = Join-Path $repoRoot $traceRelativePath
    if (Test-Path -LiteralPath $tracePath) {
        return Get-Content -LiteralPath $tracePath -Raw
    }
    return ''
}

function Get-FreshErrorDiagnostics([object]$ProcessResult) {
    return @($ProcessResult.DiagnosticPaths | Where-Object { $_ -match '(^|\\)(traceback|errors)\.txt$' })
}

$summary = [ordered]@{
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    repo_root = $repoRoot
    sdk_root = $sdkRoot
    savedir_root = Get-RelativeArtifactPath $saveRoot
    case_timeout_seconds = $CaseTimeoutSeconds
    mongo_port_open = $false
    json_validation = @()
    theme_asset_unittest = $null
    lint = $null
    cases = @()
    overall_passed = $false
}

$allPassed = $true
$fixtureFiles = @(Get-ChildItem -LiteralPath (Join-Path $repoRoot 'game\test_fixtures') -Filter '*.json' -File)
foreach ($fixture in $fixtureFiles) {
    $fixtureResult = [ordered]@{ path = Get-RelativeArtifactPath $fixture.FullName; passed = $true; error = $null }
    try {
        Get-Content -LiteralPath $fixture.FullName -Raw | ConvertFrom-Json | Out-Null
    }
    catch {
        $fixtureResult.passed = $false
        $fixtureResult.error = $_.Exception.Message
        $allPassed = $false
    }
    $summary.json_validation += [pscustomobject]$fixtureResult
}

$themeAssetTestPath = Join-Path $repoRoot 'tools\test_generate_theme_assets.py'
$systemPythonCommand = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $systemPythonCommand) {
    $themeAssetTestPassed = $false
    $summary.theme_asset_unittest = [ordered]@{
        expected = 'exit 0'
        exit_code = $null
        duration_seconds = 0
        classification = 'FAIL'
        fresh_error_diagnostics = @()
        artifact_paths = @()
        error = 'A standard Python interpreter with unittest was not found on PATH.'
    }
}
else {
    $themeAssetTestProcess = Invoke-RenPyProcess -Name 'theme_asset_generator_unittest' -RenpyArguments @($themeAssetTestPath) -ExecutablePath $systemPythonCommand.Source
    $themeAssetErrorDiagnostics = @(Get-FreshErrorDiagnostics $themeAssetTestProcess)
    $themeAssetTestPassed = (-not $themeAssetTestProcess.TimedOut) -and ($themeAssetTestProcess.ExitCode -eq 0) -and ($themeAssetErrorDiagnostics.Count -eq 0)
    $summary.theme_asset_unittest = [ordered]@{
        expected = 'exit 0'
        exit_code = $themeAssetTestProcess.ExitCode
        duration_seconds = $themeAssetTestProcess.DurationSeconds
        classification = if ($themeAssetTestPassed) { 'PASS' } else { 'FAIL' }
        fresh_error_diagnostics = $themeAssetErrorDiagnostics
        artifact_paths = @($themeAssetTestProcess.StdoutPath, $themeAssetTestProcess.StderrPath) + $themeAssetTestProcess.DiagnosticPaths
        error = $null
    }
}
if (-not $themeAssetTestPassed) { $allPassed = $false }

$lintSaveDir = Join-Path $saveRoot 'lint'
$lintProcess = Invoke-RenPyProcess -Name 'lint' -RenpyArguments @($renpyPy, '--savedir', $lintSaveDir, $repoRoot, 'lint', '--error-code')
$lintErrorDiagnostics = @(Get-FreshErrorDiagnostics $lintProcess)
$lintPassed = (-not $lintProcess.TimedOut) -and ($lintProcess.ExitCode -eq 0) -and ($lintErrorDiagnostics.Count -eq 0)
$summary.lint = [ordered]@{
    expected = 'exit 0'
    exit_code = $lintProcess.ExitCode
    duration_seconds = $lintProcess.DurationSeconds
    classification = if ($lintPassed) { 'PASS' } else { 'FAIL' }
    matched_signature = $null
    fresh_error_diagnostics = $lintErrorDiagnostics
    artifact_paths = @($lintProcess.StdoutPath, $lintProcess.StderrPath) + $lintProcess.DiagnosticPaths
}
if (-not $lintPassed) { $allPassed = $false }

$mongoPortOpen = Test-LocalMongoPort
$summary.mongo_port_open = $mongoPortOpen

$cases = @(
    [pscustomobject]@{ Name = 'gui_story_draft_basic_contract'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_draft_advanced_contract'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_draft_bounds_and_launch_seam'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_draft_excludes_disabled_cast'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_catalog_contract'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_catalog_preferences_and_export'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_catalog_rejects_invalid_preferences'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_constructor_contract'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_constructor_preferences_and_legacy_compatibility'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_main_menu_visual'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_builder_basic_visual'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_builder_advanced_visual'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_library_visual'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_disable_click_keeps_library_open'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_enable_click_keeps_library_open'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_variant_click_keeps_library_open'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_reset_click_keeps_library_open'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_save_click_keeps_library_open'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_asset_constructor_clicks_keep_library_open'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_mode_click_keeps_builder_open'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_genre_click_keeps_builder_open'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_create_starts_gracefully'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_create_rejects_invalid_draft'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_multifield_focus_survives_restart'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_multiline_input_navigation_contract'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_multiline_input_blank_line_contract'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_navigation_flow'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_story_payload_reaches_root_task'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'gui_controller_has_no_system_history_dialogue'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_registry_contract'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_resolution_default_and_invalid'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_resolution_auto_scene_recommendation'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_resolution_explicit_override'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_main_menu_submenu_neutral_variants'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_asset_and_font_fallback'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_pause_screen'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_runtime_status_screens'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_game_menu_surfaces'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_semantic_foreground_contrast'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_speaker_name_colors_are_distinct_and_readable'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_namebox_stable_size'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_main_menu_hover_text_contrast'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_game_menu_navigation_card_alignment'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_pause_main_menu_confirm_layer'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'theme_palette_chrome_and_compact_controls'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'ui_contract_optional_unknown_and_hash'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'ui_contract_malformed_rejected'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'ui_contract_legacy_migration'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_metadata_first'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_provider_does_not_leak_to_new_story'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_resources_and_contract'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_first_scene_visual'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_second_scene_visual'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_third_scene_visual'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_history_visual'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_save_load_resume'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_save_title_legacy_and_untrusted_fallbacks'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'demo_story_save_title_visual'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_playback_offline'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_return'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_jump'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_scene_boundary'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_history_ui'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_skip'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_auto'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_save_load_mid_scene'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_rollback_mid_scene'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_known_issue_unknown_action'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_known_issue_animate_object'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_missing_background'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_handlers_return'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_transition_fade'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_contract_valid_state'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_contract_hash_canonical'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_contract_rejects_before_handlers'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_contract_duplicate_key'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_contract_malformed_inputs'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_contract_untrusted_limits'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_contract_legacy_migration'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_state_save_load_roundtrip'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_state_integrity_tampering'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_player_valid_v1'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_player_rejects_before_handler'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_queue_consumes_once'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_contract_handler_registry'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage1_queue_rejects_invalid_once'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_cursor_progression'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_save_load_repeats_current_only'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_rollback_one_line'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_rollback_three_lines'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_rollback_ten_lines'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_rollback_across_scene_boundary'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_return_explicit_completed'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_natural_end_completed'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_jump_returns_control_and_dispatches'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_handler_exception_preserves_cursor'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage2_pause_hard_checkpoint'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_history_annotations'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_history_save_load_no_earlier_duplicates'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_save_slot_json_metadata'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_save_slot_json_omits_untrusted_state'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_after_load_rejects_invalid_state'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_fileload_rejects_invalid_state'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_history_rollback_identifier'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_history_screen_rolls_back_to_entry'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_line_middleware_exception_is_visible'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_post_line_middleware_exception_is_visible'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_untrusted_text_is_literal'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_unapproved_jump_rejected'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage3_consumption_is_idempotent_ack'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage4_scene_provider_contract'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage4_task_errors_are_visible'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage4_poll_work_is_bounded'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage4_offline_timeout_is_bounded'; Expected = 'exit 0 within 12 seconds and visible provider_offline'; Signature = $null; RequiresOfflineMongo = $true; TimeoutSeconds = 12 },
    [pscustomobject]@{ Name = 'stage4_structured_error_main_menu'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage4_retry_ack_without_replay_and_boundary_autosave'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage4_retry_playback_from_current_action'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage4_real_autosave_restores_boundary'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage4_fileload_rejects_invalid_session'; Expected = 'exit 0'; Signature = $null; RequiresOfflineMongo = $false },
    [pscustomobject]@{ Name = 'stage0_start_without_mongo'; Expected = 'exit 0 with controlled provider_offline UI'; Signature = $null; RequiresOfflineMongo = $true; TimeoutSeconds = 8 }
)

foreach ($case in $cases) {
    $caseMongoPortOpenBefore = $null
    $caseMongoPortOpenAfter = $null

    if ($case.RequiresOfflineMongo) {
        # The initial probe can become stale while earlier cases run. Verify the
        # precondition again immediately before the offline-only testcase.
        $caseMongoPortOpenBefore = Test-LocalMongoPort
    }

    if ($caseMongoPortOpenBefore) {
        $summary.cases += [ordered]@{
            name = $case.Name; expected = $case.Expected; exit_code = $null; duration_seconds = 0
            classification = 'BLOCKED/SKIP'; matched_signature = $null; artifact_paths = @()
            mongo_port_open_before = $caseMongoPortOpenBefore
            mongo_port_open_after = $null
        }
        $allPassed = $false
        continue
    }

    $caseSaveDir = Join-Path $saveRoot $case.Name
    $resolvedSaveRoot = [System.IO.Path]::GetFullPath($saveRoot).TrimEnd('\') + '\'
    $resolvedCaseSaveDir = [System.IO.Path]::GetFullPath($caseSaveDir)
    if (-not $resolvedCaseSaveDir.StartsWith($resolvedSaveRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean save directory outside the runner save root: $resolvedCaseSaveDir"
    }
    if (Test-Path -LiteralPath $resolvedCaseSaveDir -PathType Container) {
        Get-ChildItem -LiteralPath $resolvedCaseSaveDir -Force | Remove-Item -Recurse -Force
    }
    else {
        New-Item -ItemType Directory -Path $resolvedCaseSaveDir | Out-Null
    }
    $caseTimeout = if ($case.PSObject.Properties.Name -contains 'TimeoutSeconds') { [int]$case.TimeoutSeconds } else { $CaseTimeoutSeconds }
    $result = Invoke-RenPyProcess -Name $case.Name -RenpyArguments @($renpyPy, '--savedir', $caseSaveDir, $repoRoot, 'test', $case.Name) -TimeoutSeconds $caseTimeout
    $matchedSignature = $null
    $freshErrorDiagnostics = @(Get-FreshErrorDiagnostics $result)
    if ($case.ExpectedTimeout) {
        # Recheck after the owned process was stopped. A Mongo server that is
        # now reachable invalidates the offline-timeout characterization.
        $caseMongoPortOpenAfter = Test-LocalMongoPort
        $matchedSignature = if ($result.TimedOut) { "owned process timeout after $caseTimeout seconds" } else { $null }
        $passed = $result.TimedOut -and (-not $caseMongoPortOpenAfter)
    }
    elseif ($case.Signature) {
        $traceback = Get-TracebackText $result
        if ($traceback -match $case.Signature) { $matchedSignature = $case.Signature }
        # Ren'Py 8.3.4's `test` command exits 0 after an uncaught game exception.
        # A traceback copied only when it is fresh for this case is therefore authoritative.
        $passed = (-not $result.TimedOut) -and ($null -ne $matchedSignature)
    }
    else {
        # Ren'Py's native test command may return 0 after an uncaught script
        # exception. A fresh traceback/errors file therefore vetoes PASS.
        $passed = (-not $result.TimedOut) -and ($result.ExitCode -eq 0) -and ($freshErrorDiagnostics.Count -eq 0)
    }

    $summary.cases += [ordered]@{
        name = $case.Name
        expected = $case.Expected
        exit_code = $result.ExitCode
        duration_seconds = $result.DurationSeconds
        classification = if ($passed) { 'PASS' } elseif ($result.TimedOut) { 'TIMEOUT' } else { 'FAIL' }
        matched_signature = $matchedSignature
        fresh_error_diagnostics = $freshErrorDiagnostics
        artifact_paths = @($result.StdoutPath, $result.StderrPath) + $result.DiagnosticPaths
        mongo_port_open_before = $caseMongoPortOpenBefore
        mongo_port_open_after = $caseMongoPortOpenAfter
    }
    if (-not $passed) { $allPassed = $false }
}

$summary.overall_passed = $allPassed
$resultsPath = Join-Path $artifactRoot 'stage0-results.json'
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultsPath -Encoding utf8

Write-Host ("Stage 0: JSON={0}/{1}; theme-assets={2}; lint={3}; cases={4}; overall={5}; results={6}" -f `
    (@($summary.json_validation | Where-Object passed).Count), $summary.json_validation.Count, $summary.theme_asset_unittest.classification, `
    $summary.lint.classification, (($summary.cases | ForEach-Object classification) -join ','), `
    $summary.overall_passed, (Get-RelativeArtifactPath $resultsPath))

if (-not $allPassed) { exit 1 }
