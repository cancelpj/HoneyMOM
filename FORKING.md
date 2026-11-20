# Fork 工作流说明

本仓库是 [HoneyMeta/HoneyMOM](https://github.com/HoneyMeta/HoneyMOM) 的 fork，用于在保留上游持续更新的前提下做自己的改动和发布。

## 分支模型

| 分支 | 角色 | 谁往里提交 |
|---|---|---|
| `main` | **你的开发 / 发布分支**：所有自有改动提交在这里，发布也从这里打 tag | 只有你 |
| `sync/upstream` | **同步专用分支**：始终快进到上游最新，只负责搬运上游改动，不放任何自有提交 | 只有同步脚本（`--ff-only`） |

`main` 始终包含上游的最新内容，`sync/upstream` 是它与上游之间的「中转站」。

```
upstream/main  ──fetch──▶  sync/upstream  ──merge──▶  main（你的改动 + 上游改动）
```

## 远程

| 远程 | 地址 |
|---|---|
| `upstream` | `https://github.com/HoneyMeta/HoneyMOM.git`（原作者仓库，只读参考） |
| `origin` | `https://github.com/cancelpj/HoneyMOM.git`（你的 fork，推送目标） |

本机访问 GitHub 需要走代理，已在**本仓库**（非全局）配置：

```bash
git config http.proxy http://127.0.0.1:3128
git config http.version HTTP/1.1     # 代理下 HTTP/2 会僵死
```

## 日常同步

```powershell
pwsh scripts\sync-upstream.ps1              # 同步上游并合并进 main（不动远端）
pwsh scripts\sync-upstream.ps1 -DryRun      # 只看会同步什么，不改任何东西
pwsh scripts\sync-upstream.ps1 -NoMerge     # 只更新 sync/upstream，暂不合进 main
pwsh scripts\sync-upstream.ps1 -Push        # 同步后把 main 和 sync/upstream 推到 origin
```

脚本流程：

1. `git fetch upstream --tags`
2. `sync/upstream` 用 `--ff-only` 快进到 `upstream/main`（**只允许快进**，保证它永远不含自有提交）
3. `main` 执行 `git merge sync/upstream`：无分叉时快进，有分叉时生成一个合并提交

退出码：`0` 成功 / `1` 出错 / `2` 有冲突需人工处理。

**工作区有未提交改动时会直接跳过**（不做任何改动，退出码 0）——这样定时任务不会因为你正在改代码而报错或半途合并。

**有冲突时**脚本会打印冲突文件清单并停下，解决后：

```powershell
git status                     # 看冲突
git add <冲突文件>
git commit                     # 完成合并
```

想放弃这次合并：`git merge --abort`。

## 定时同步

把同步注册成 Windows 计划任务（每天定时执行）：

```powershell
pwsh scripts\register-sync-task.ps1                 # 默认每天 09:00
pwsh scripts\register-sync-task.ps1 -Time 20:30     # 换时间
pwsh scripts\register-sync-task.ps1 -Unregister     # 删除
```

查看 / 手动触发：

```powershell
schtasks /query /tn HoneyMOM-upstream-sync
schtasks /run   /tn HoneyMOM-upstream-sync
```

任务以当前登录用户身份运行（不需要管理员密码），**机器开机且该用户已登录时才会执行**。

## 冲突处理建议

上游改动和你改的是同一处时，常见选择：

- **保留你的改动**：`git checkout --ours <文件>`（合并时 ours = main = 你的版本）
- **采用上游版本**：`git checkout --theirs <文件>`（theirs = sync/upstream）
- **手动合并**：直接编辑文件后 `git add`

改完记得在 `main` 上提交，然后把 `sync/upstream` 也快进一下，让两边保持一致：

```powershell
git checkout sync/upstream
git merge --ff-only main
git checkout main
```

## 已知的本地补丁

`patches/llm-gateway-compat.patch` 是本 fork 针对自建 / LiteLLM 网关做的兼容补丁（`system` 消息必须放在最前面，否则网关返回 400）：

- `honeymom/services/ai.py`：合并所有 system 消息到最前一条；把字段 `hint` 暴露给模型；查询轮次上限 6 → 12
- `honeymom/schema.py`：给 `part.machine` 加「对应 equipment.code」的提示

上游更新后如果这个补丁被覆盖，重新应用：

```powershell
git apply patches\llm-gateway-compat.patch
```

## 发布

改动都在 `main` 上，发布也从 `main` 打 tag：

```powershell
git tag -a v1.0.0 -m "release v1.0.0"
git push origin main --tags
```
