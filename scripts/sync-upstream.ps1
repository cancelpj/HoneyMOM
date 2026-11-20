<#
    sync-upstream.ps1 —— 同步上游 HoneyMOM 并把上游改动合并进主分支

    分支约定：
      main           你的开发 / 发布分支（改动提交在这里）
      sync/upstream  专用同步分支，始终快进到上游最新，只用来搬运上游改动

    流程：
      1. git fetch upstream --tags
      2. sync/upstream  ← --ff-only 快进到 upstream/main
      3. main           ← merge sync/upstream（无分叉时快进，有分叉时生成合并提交）

    退出码：0 成功（或因工作区脏而跳过）/ 1 出错 / 2 有冲突（需要人工解决）

    用法：
      pwsh scripts\sync-upstream.ps1                # 同步并合并到 main
      pwsh scripts\sync-upstream.ps1 -DryRun        # 只看会同步什么，不改任何东西
      pwsh scripts\sync-upstream.ps1 -NoMerge       # 只更新 sync/upstream，不动 main
      pwsh scripts\sync-upstream.ps1 -Push          # 同步后把两个分支推到 origin
      pwsh scripts\sync-upstream.ps1 -AllowDirty    # 允许工作区有改动（不推荐）
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$NoMerge,
    [switch]$Push,
    [switch]$AllowDirty,
    [string]$Remote = 'upstream',
    [string]$UpstreamBranch = 'main',
    [string]$SyncBranch = 'sync/upstream',
    [string]$MainBranch = 'main'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Say($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }

# 注意：函数名不能叫 Git —— PowerShell 命令名不区分大小写，函数体内的 `git` 会解析到
# 这个函数自己，形成无限递归（"调用深度溢出"）。这里用绝对路径调用真正的 git.exe。
$GIT = (Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $GIT) { throw '找不到 git.exe，请确认 Git 已安装并在 PATH 中' }

function Invoke-Git($argsList) {
    $out = & $GIT @argsList 2>&1
    if ($LASTEXITCODE -ne 0) { throw "git $($argsList -join ' ') 失败：`n$($out -join "`n")" }
    return $out
}

Say "仓库：$repo" 'DarkGray'

# ── 0. 前置检查 ───────────────────────────────────────────────
$dirty = & $GIT status --porcelain
if ($dirty -and -not $AllowDirty) {
    Say '工作区有未提交的改动，本次跳过同步（没有改动任何东西）。' 'Yellow'
    Say '  定时任务遇到这种情况会安静跳过；手动同步请先提交或 stash。' 'DarkGray'
    Say ($dirty | Select-Object -First 10) 'DarkGray'
    exit 0
}
if (-not (& $GIT remote | Where-Object { $_ -eq $Remote })) {
    Say "没有远程 $Remote，先执行：git remote add $Remote https://github.com/HoneyMeta/HoneyMOM.git" 'Red'
    exit 1
}

# ── 1. 拉取上游 ───────────────────────────────────────────────
$up = "refs/remotes/$Remote/$UpstreamBranch"
$before = ''
& $GIT show-ref --verify --quiet $up
if ($LASTEXITCODE -eq 0) { $before = (& $GIT rev-parse $up).Trim() }
Say "`n[1/4] 拉取 $Remote ..." 'Cyan'
Invoke-Git @('fetch', $Remote, '--tags')
$after = (& $GIT rev-parse $up).Trim()
Say "  $Remote/$UpstreamBranch = $($after.Substring(0,10))" 'DarkGray'
if ($before -and $before -eq $after) { Say '  上游没有新提交。' 'Green' }
elseif ($before) { Say "  上游有新提交：$($before.Substring(0,10)) → $($after.Substring(0,10))" 'Green' }

# ── 2. 更新 sync 分支（只快进）────────────────────────────────
# 用 update-ref 直接移动分支指针：不切换分支、不动工作区。
# （早前用 `git merge --ff-only` 的写法会在当前分支上执行，等于把上游合进了 main。）
Say "`n[2/4] 更新同步分支 $SyncBranch ..." 'Cyan'
& $GIT show-ref --verify --quiet "refs/heads/$SyncBranch"
$syncExists = ($LASTEXITCODE -eq 0)
if ($syncExists) {
    # 只允许快进：sync 分支不应该有自己的提交
    & $GIT merge-base --is-ancestor "refs/heads/$SyncBranch" $up
    if ($LASTEXITCODE -ne 0) {
        Say "  $SyncBranch 上有独立提交，无法快进到上游，请人工检查" 'Red'
        exit 2
    }
    $syncHead = (& $GIT rev-parse "refs/heads/$SyncBranch").Trim()
    Invoke-Git @('update-ref', "refs/heads/$SyncBranch", $up)
    Say "  $SyncBranch：$($syncHead.Substring(0,10)) → $($after.Substring(0,10))" 'DarkGray'
} else {
    Invoke-Git @('branch', '--track', $SyncBranch, $up)
    Say "  新建 $SyncBranch → $($after.Substring(0,10))" 'Green'
}
$newUp = (& $GIT rev-parse "refs/heads/$SyncBranch").Trim()

if ($DryRun) {
    Say "`n--dry-run：只报告不改动 --" 'Yellow'
    Say "  待合并到 $MainBranch 的提交：" 'Gray'
    & $GIT log --oneline "$MainBranch..$SyncBranch" | Select-Object -First 30 | ForEach-Object { Say "    $_" 'DarkGray' }
    Say "  受影响文件：" 'Gray'
    & $GIT diff --stat "$MainBranch...$SyncBranch" | Select-Object -First 30 | ForEach-Object { Say "    $_" 'DarkGray' }
    exit 0
}

if ($NoMerge) { Say "`n[跳过] 按要求只更新了 $SyncBranch，未合并到 $MainBranch" 'Yellow'; exit 0 }

# ── 3. 合并到主分支 ───────────────────────────────────────────
Say "`n[3/4] 合并到 $MainBranch ..." 'Cyan'
& $GIT checkout $MainBranch 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Say "  切换到 $MainBranch 失败" 'Red'; exit 1 }

& $GIT merge --no-edit $SyncBranch
if ($LASTEXITCODE -ne 0) {
    Say "  合并有冲突，已暂停（解决后 git add ... && git commit，或 git merge --abort 放弃）" 'Red'
    Say '  冲突文件：' 'Yellow'
    & $GIT diff --name-only --diff-filter=U | ForEach-Object { Say "    $_" 'Yellow' }
    exit 2
}
Say "  $MainBranch 现在位于 $((& $GIT rev-parse HEAD).Trim().Substring(0,10))" 'Green'

# ── 4. 推送 ───────────────────────────────────────────────────
if ($Push) {
    Say "`n[4/4] 推送到 origin ..." 'Cyan'
    & $GIT push origin $MainBranch
    if ($LASTEXITCODE -ne 0) { Say '  推送主分支失败' 'Red'; exit 1 }
    & $GIT push origin $SyncBranch
    if ($LASTEXITCODE -ne 0) { Say '  推送同步分支失败' 'Red'; exit 1 }
    Say '  已推送 main 和 sync/upstream' 'Green'
} else {
    Say "`n[4/4] 跳过推送（加 -Push 可自动推送）" 'DarkGray'
}

Say "`n同步完成。" 'Green'
Say "查看变更：git log --oneline $MainBranch..$SyncBranch" 'DarkGray'
