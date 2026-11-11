# AGENT.md — 心灵终结 3.3.6 平衡性脚本 · 工作指引

> **先读我，再动手。** 项目根目录 `D:\AIWORK\DSH mission\3.3.6`，游戏 `D:\Mental Omega`（MO 3.3.6）。
> 本项目只做**数值平衡**，不改游戏本体、不动 MIX 原包。

---

## 一、标准文件路径（全部为唯一出处，改需求先改文件）

| 类别 | 路径 | 说明 |
|---|---|---|
| **实时需求收件箱** | `需求.md` | **用户在这里直接写需求/修改方案**，我按编号读取执行 |
| 需求基线与范围 | `docs/01-需求.md` | 目标、范围、名词、验收标准（定稿） |
| 技术方案 | `docs/02-技术方案.md` | MIX 提取原理、外置覆盖机制、工具链 |
| 设计规范 | `docs/03-设计规范.md` | 改动粒度、数值上下限、写入格式要求 |
| 执行步骤 | `docs/04-执行步骤.md` | Phase 划分与验收门槛 |
| 安全规范 | `docs/05-安全规范.md` | 备份/回滚/校验/禁止事项 |
| 数据参考 | `docs/06-数据参考.md` | 关键 ID、MIX 偏移、名录字段说明 |
| 开发日志 | `devlog/YYYY-MM-DD.md` | 每日完成/代办/风险/下一步，机制见 `devlog/README.md` |
| 基准规则文件 | `rulesmo_original.ini` | 从 MIX 抽出的**原版**，只读，永不修改 |
| 中文名录 | `单位名录.csv` | 1,722 条，中文名↔ID↔数值 |
| 名录自检报告 | `单位名录_自检报告.md` | 同名/AI版/歧义分组清单 |
| 中文名映射 | `unit_names_cn_merged.json` | 单位 1,722 + 武器 377 |
| 工具 | `tools/*.py` | 见下方"工具清单" |

## 二、工具清单

| 脚本 | 作用 |
|---|---|
| `tools/ini_edit.py` | 行级改值：保留注释/CRLF/编码，原子写入 + sha1 校验，改前校验节与键存在 |
| `tools/ini_compare.py` | 语义比对（按 [节]+键，忽略格式差异），用于复核"改动条数=名单条数" |
| `tools/merge_names.py` | 合并 `D:\Default Project\config\unit_names_cn*.json` 为一份总表 |
| `tools/make_unit_catalog.py` | 生成 `单位名录.csv` |
| `tools/check_catalog.py` | 名录自检：找出"同名不同 ID""AI 版 vs 玩家版"等歧义 |
| `tools/build_override.py` | 从基准 + `changes/*.json` 生成 `rulesmo.ini`；前置校验 + 独立复核 + 反向检查有无清单外改动；支持多批次叠加 |
| `tools/deploy.py` | `check` / `deploy` / `rollback` / `drill`：进程检查、强制备份（含游戏基准文件 sha1）、部署后校验、回滚演练 |
| `tools/make_release.py` | 打包可交付 zip（`dist/MO平衡补丁_v<版本>/`），内含双击安装/还原、使用说明、改动清单、SHA256SUMS |
| `tools/devlog.py` | 创建/追加当日开发日志 |

## 二·五、本地一键操作（用户双击即可，无需命令行）

| 文件 | 作用 |
|---|---|
| `一键体检.bat` | 只读：显示游戏是否运行、当前部署版本 sha1、当前生效改动数、是否已是最新 |
| `一键部署.bat` | 备份 → 部署 → 校验 sha1（会写 `backup/<时间戳>_deploy/`） |
| `一键恢复原版.bat` | 备份 → 删除覆盖文件 → 确认恢复原版（会写 `backup/<时间戳>_rollback/`） |

这三个 bat 会自动探测 Python（`python` → `py` → 两个已知安装路径），并在 `cmd` 下用 UTF-8 输出中文。
**双击前务必退出游戏**（脚本也会检查并拒绝）。

## 三、工作说明（必须遵守）

1. **小步稳进**：一次只做用户明确点名的改动；没点名的单位不碰。
2. **基准只读**：`rulesmo_original.ini` 是原始抽取值，只作基准；所有改动在副本上生成 `rulesmo.ini`。
3. **条数必须对得上**：写入后用 `ini_compare.py` 复核，差异条数必须与用户名单**完全一致**；多一条、少一条都要停下来报告，不许"顺手优化"。
4. **写游戏前必备份**：部署前对 `D:\Mental Omega\rulesmo.ini`（若已存在）做快照并存 sha1；无则记录"无旧文件"。
5. **原子写入**：先写 `.tmp` → 校验 → 替换；禁止直接覆盖。
6. **回滚只有一步**：删除 `D:\Mental Omega\rulesmo.ini` 即恢复原版（MIX 未被改动）。
7. **游戏运行中不写文件**：检测到 `gamemd.exe`/`MentalOmegaClient.exe` 在跑，就不做离线保存。
8. **每轮收尾更新当日 devlog**：完成 / 代办 / 风险 / 下一步，四段必填。
9. **路径引用带行号**：如 `docs/03-设计规范.md:12`；回复用短句中文，让非程序用户能懂。
10. **不提交/不复制游戏本体与大文件**：`D:\Mental Omega` 下的 `.mix`、`.exe` 一律不搬进工作区。

## 四、环境须知（踩过的坑，勿重复）

- **Bash 不可用时报错形如** `EXECUTOR_UNAVAILABLE ... link ... winuxcmd.exe -> ...od.exe`：
  根因是 `winuxcmd.exe` 这个 inode 的 NTFS 硬链接数接近上限 1024（历史残留执行树占满）。
  修法（已验证有效、字节 sha256 不变）：把
  `D:\DeepSeek-Harness\home\profiles\desktop\node_modules\dsh-ops\runtime\win32-x64\niubash\winuxcmd\usr\bin\winuxcmd.exe`
  用自己的副本原地替换，使 inode 归零重来。
- `D:\dsh-ops-exec\` 下可能有历史残留执行树，被拒绝删除（EPERM）；**它们不影响功能，不要为它折腾权限**。
- **不要**为了跑命令去切换 shell 或绕过沙箱。
- Python 为系统原生 Windows 版（`python` 直接可用），**不认 `/d/...` 这类 MSYS 路径**，脚本内一律用 `D:/...` 或 `r"D:\..."`。
- 中文输出乱码时设 `PYTHONIOENCODING=utf-8`。

## 五、技术路线（已定，勿改）

外置同名覆盖：把改好的 `rulesmo.ini` 放到 `D:\Mental Omega\`，游戏优先读它，MIX 内原文件不动。
依据：用户既有工程 `D:\Default Project\src\rules_writer.py` 中 `OVERRIDE_NAME = "rulesmo.ini"` 已跑通此路线。

## 六、禁止事项

- 不修改 `D:\Mental Omega` 下任何 `.mix` / `.exe`；
- 不删除用户的备份目录（`D:\Default Project\backup_by_trainer\`）；
- 不在未备份的情况下覆盖已有 `rulesmo.ini`；
- 不擅自扩大改动范围（用户没点名的单位/武器一律不动）。

## 七、多 Agent 协作约定

本目录已设为 **AO Claude 多 Agent 协作区**（尚未启用）。启用后必须遵守：

- **一个文件同一时刻只由一个 Agent 写**；不同 Agent 各写各的文件，不交叉。
- 动手前先 `git status` 确认没有他人未提交的改动；写完立刻 commit。
- commit message 前缀带 Agent 标识，便于追溯，如 `[lead]`、`[agent-b]`。
- **共享事实的唯一出处**：`rulesmo_original.ini`（只读基准）、`单位名录.csv`、`单位名录_自检报告.md`。
- 需求以 `需求.md` 为准；跨 Agent 传递信息写进 `需求.md` 或当日 `devlog`，不留口头约定。
- **只读文件**：`rulesmo_original.ini`，任何 Agent 都不得修改。
- **互斥资源**：`changes/*.json`、工作区 `rulesmo.ini`、`D:\Mental Omega\rulesmo.ini` —— 同一时刻只允许一个 Agent 操作。
- 发现文件被别人改过：**先读当前内容再改**，禁止盲目覆盖。

## 八、当前状态

见 `devlog/` 最新一篇。
