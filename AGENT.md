# AGENT.md — 维护与协作说明

> 给**接手这个仓库的人或自动化助手**看的：项目约定、禁止事项、多 agent 并行协作规则。
> 动手前请先读 [`README.md`](README.md)、[`CONTRIBUTING.md`](CONTRIBUTING.md)、
> [`docs/03-设计规范.md`](docs/03-设计规范.md)、[`docs/05-安全规范.md`](docs/05-安全规范.md)。

本项目只做**数值平衡**，不改游戏本体、不动 MIX 原包。
所有改动都是一条 `[节] + 键 = 新值`，写在 `changes/*.json` 里，构建成覆盖用的 `rulesmo.ini`。

---

## 一、事实的唯一出处

| 类别 | 路径 | 说明 |
|---|---|---|
| **改动唯一入口** | `changes/*.json` | 所有数值改动都在这里；构建脚本只读这里 |
| 原版基准（本地生成） | `rulesmo_original.ini` | 由 `tools/extract_rules.py` 从玩家自己的 `expandmo99.mix` 抽出，**只读，永不修改** |
| 覆盖文件（本地生成） | `rulesmo.ini` | 构建产物，部署到 `<游戏安装目录>\rulesmo.ini` |
| 玩家文案 | `公告-定稿.md` | 面向玩家的完整公告；「项数」「数值参数」口径以它为准 |
| 需求基线 | `docs/01-需求.md` | 目标、范围、名词、验收标准 |
| 技术方案 | `docs/02-技术方案.md` | MIX 提取原理、外置覆盖机制、工具链 |
| 设计规范 | `docs/03-设计规范.md` | 改动粒度、数值上下限、写入格式 |
| 执行步骤 | `docs/04-执行步骤.md` | Phase 划分与验收门槛 |
| 安全规范 | `docs/05-安全规范.md` | 备份 / 回滚 / 校验 / 禁止事项 |
| 数据参考 | `docs/06-数据参考.md` | 关键 ID、提取参数、名录字段 |
| 核对与改动记录 | `docs/07-*.md`、`docs/08-*.md` | 公告核对报告、第一批改动逐条清单 |
| 历史需求存档 | `docs/09-用户原始需求-v1.0.1.md` | v1.0.1 的原始需求原文（不可再改，只作追溯） |
| 改动请求 | `需求.md` | 改动请求模板与提交流程 |
| 开发日志 | `devlog/YYYY-MM-DD.md` | 每日「完成 / 代办 / 风险 / 下一步」，机制见 `devlog/README.md` |
| 工具 | `tools/*.py` | 见下方「工具清单」 |
| 对外发布包 | `release/` → `dist/` | `release/` 是打包素材，`dist/` 是成品（不入库） |

> 对外界提问的答复口径：**版本与条数以 `公告-定稿.md` + `CHANGELOG.md` 为准**，
> 数值以 `changes/*.json` 为准，二者必须一致。

## 二、工具清单

| 脚本 | 作用 |
|---|---|
| `tools/extract_rules.py` | 从 `expandmo99.mix` 按横幅定位抽出原版 `rulesmo.ini`（唯一的数据入口） |
| `tools/ini_edit.py` | 行级改值：保留注释/CRLF/编码，原子写入 + sha1 校验，改前校验节与键存在 |
| `tools/ini_compare.py` | 语义比对（按 `[节]+键`，忽略格式差异），用于复核「改动条数 = 清单条数」 |
| `tools/build_override.py` | 基准 + `changes/*.json` → `rulesmo.ini`；前置校验 + 独立复核 + 反向检查清单外改动 |
| `tools/deploy.py` | `check` / `deploy` / `rollback`：进程检查、强制备份（含 sha1）、部署后校验、回滚演练 |
| `tools/make_release.py` | 打包可交付 zip：双击安装/还原、使用说明、改动清单、SHA256SUMS |
| `tools/make_unit_catalog.py` | 生成 `单位名录.csv`（中文名 ↔ 节点 ID ↔ 数值） |
| `tools/check_catalog.py` | 名录自检：找出「同名不同 ID」「玩家版 vs AI 版」等歧义 |
| `tools/merge_names.py` | **一次性内部工具**：合并社区汉化工程的多份中文名表；源数据不随仓库分发 |
| `tools/devlog.py` | 创建 / 追加当日开发日志 |

**路径策略（硬性）**：源码里不得硬编码本机绝对路径。游戏目录按优先级解析：
命令行参数（`--game-dir`）→ 环境变量 `MO_GAME_DIR` → 常见安装路径自动探测 → 中文报错提示用户指定。
所有相对路径按**仓库根**解析（不依赖当前目录），`extract_rules` / `build_override` / `ini_compare` 默认读写仓库根的文件。

### 本地一键脚本（Windows，维护者便利）

| 文件 | 作用 |
|---|---|
| `一键体检.bat` | 只读：游戏是否在运行、当前部署 sha1、生效改动数、是否已是最新 |
| `一键部署.bat` | 备份 → 部署 → 校验 sha1 |
| `一键恢复原版.bat` | 备份 → 删除覆盖文件 → 确认恢复原版 |

参数会透传给 Python（如 `一键部署.bat --game-dir "E:\MO"`）；脚本自动探测 Python（PATH → `py` → 常见安装目录），
找不到时给中文提示。**双击前务必退出游戏**（脚本也会检查并拒绝）。

## 三、工作说明（必须遵守）

1. **小步稳进**：一次只做明确点名的改动；没点名的单位不碰。
2. **基准只读**：`rulesmo_original.ini` 是原版抽取值，只作基准；所有改动在副本上生成 `rulesmo.ini`。
3. **条数必须对得上**：写入后用 `tools/ini_compare.py` 复核，差异条数必须与清单**完全一致**；
   多一条、少一条都要停下来报告，不许「顺手优化」。
4. **写游戏前必备份**：部署前对 `<游戏安装目录>\rulesmo.ini`（若已存在）做快照并存 sha1。
5. **原子写入**：先写 `.tmp` → 校验 → 替换；禁止直接覆盖。
6. **回滚只有一步**：删除 `<游戏安装目录>\rulesmo.ini` 即恢复原版（MIX 从未被改动）。
7. **游戏运行中不写文件**：检测到 `gamemd.exe` / `MentalOmegaClient.exe` 在跑，就停下。
8. **每轮收尾更新当日 devlog**：完成 / 代办 / 风险 / 下一步，四段必填。
9. **路径引用带行号**：如 `docs/03-设计规范.md:12`；对外回复用短句中文，让非程序用户能懂。
10. **不提交游戏本体与大文件**：任何 `.mix` / `.exe` / 原版 `rulesmo.ini` / 名录数据 / `dist/`
    一律不入库（`.gitignore` 已拦截，CI 会再查一遍）。

## 四、禁止事项

- ❌ 修改 / 删除 `<游戏安装目录>` 下任何 `.mix`、`.exe`、`.dll`
- ❌ 在未备份的情况下覆盖已有 `rulesmo.ini`
- ❌ 游戏运行时写文件
- ❌ 为绕过权限限制而切换 shell / 提升权限 / 改 ACL
- ❌ 改动未经点名的单位 / 武器
- ❌ 提交游戏数据、发布成品包或本机绝对路径进版本库
- ❌ 改写 git 历史、强推、删除他人未提交的改动

## 五、多 agent 并行协作约定

多个自动化助手可能同时在同一个工作区改文件，因此：

- **一个文件同一时刻只由一个 agent 写**；不同 agent 各写各的文件，不交叉。
- **动手前先 `git status`**，确认没有他人未提交的改动；发现目标文件被别人改过，
  **先读当前内容再改**，禁止盲目覆盖。
- 提交信息前缀带 agent 标识，便于追溯，如 `[lead]`、`[docs]`、`[tools]`；
  提交由维护者统一执行，助手默认**不自行 commit / push**。
- **共享事实的唯一出处**：`公告-定稿.md`（口径）、`changes/*.json`（数值）、
  `rulesmo_original.ini`（只读基准，本地生成）。
- **互斥资源**：`changes/*.json`、工作区 `rulesmo.ini`、`<游戏安装目录>\rulesmo.ini`
  —— 同一时刻只允许一个 agent 操作。
- 跨 agent 传递信息写进文件（`需求.md` 或当日 `devlog`），**不留口头约定**。
- 收尾时更新共享任务状态，并在答复里给出「改了什么 / 验证了什么 / 还有什么没做」。

## 六、环境须知（踩过的坑）

- Python 用**系统原生 Windows 版**时**不认 `/d/...` 这类 MSYS 路径**，脚本内一律用相对路径或 `r"D:\..."`。
- 中文输出乱码时设 `PYTHONIOENCODING=utf-8`。
- 规则文件是 **CRLF**：不得改成 LF，不得凭空加 BOM（见 `.gitattributes`）。
- 只在标准库范围内写脚本：玩家机器上不应要求 `pip install`。
- 不要为了跑命令去切换 shell 或绕过沙箱限制。

## 七、对外发布前检查清单

- [ ] `python .github/scripts/check_changes.py` 通过（改动清单结构）
- [ ] `python .github/scripts/check_tracked.py` 通过（版本库无游戏数据、无本机路径）
- [ ] `python tools/ini_compare.py rulesmo_original.ini rulesmo.ini` 的差异条数 = 清单条数
- [ ] `公告-定稿.md`、`CHANGELOG.md`、`release/使用说明.txt` 的版本号与数字一致
- [ ] 仓库跟踪文件里搜不到本机绝对路径：`git grep -n "D:/"` / `git grep -n "C:/Users"`
- [ ] 发布包（`dist/*.zip`）作为 Release 附件上传，**不进仓库**

## 八、当前状态

见 `devlog/` 最新一篇与 [`CHANGELOG.md`](CHANGELOG.md)。
