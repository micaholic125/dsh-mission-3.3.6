# 心灵终结 3.3.6 平衡补丁

《心灵终结》（Mental Omega，简称 MO）3.3.6 的社区**数值平衡补丁**。

它**只改数值**——造价、血量、装甲、速度、视野、武器伤害/射程/射速、支援技能时间——
通过把一个改好的 `rulesmo.ini` 放进游戏目录实现「外置同名覆盖」。
不新增单位、不改美术与音效、**不修改任何 `.mix` / `.exe`**；删掉那个文件就完全回到原版。

| | |
|---|---|
| 当前版本 | **v1.0.1**（改动明细见 [`CHANGELOG.md`](CHANGELOG.md)） |
| 改动规模 | **28 项平衡调整 / 69 个数值参数** |
| 逐条说明 | [`公告-定稿.md`](公告-定稿.md)（面向玩家，含每条的「原值 → 新值」） |
| 机读明细 | [`changes/batch*.json`](changes/)（`[节] + 键 = 新值`，构建脚本的唯一输入） |
| 许可 | [MIT](LICENSE)。游戏数据/规则文件版权归 Mental Omega 团队所有，**不在**本许可范围 |

---

## 一、这一版改了什么

28 项调整覆盖四大阵营及其子阵营（完整文案与设计理由见 [`公告-定稿.md`](公告-定稿.md)）：

| 阵营 | 项数 | 涉及单位 / 技能 |
|---|---:|---|
| 盟军共通 | 1 | 闪电风暴 |
| 欧盟（EU） | 8 | 雷神炮艇、光棱坦克、火控穹顶、圣骑士支援、狙击手、冥卫坦克、传送节点、超时空起重机 |
| 苏军共通 | 2 | 放射装甲 γ / β |
| 中国（CN） | 2 | 核能奔涌、女娲加农炮 |
| 俄罗斯（RU） | 1 | 猎狼犬直升机 |
| 厄普西隆军 | 4 | 克隆缸、雷格机动前哨站、马尔翁、磁力射线 |
| 焚风共通 | 3 | 铁骑兵、长枪战士、加速旋塔 |
| 科洛尼亚侧翼 | 5 | 先锋炮艇机、无齿翼龙、长生鸟空中哨站、多智龙火炮、优莱卡 |
| 狂鲨先锋 | 2 | 沙德雷聚波坦克、爆裂蜂 |

> 「项」是一条公告级调整；一条调整常对应多个数值参数（例如「冥卫坦克」包含造价与索敌行为），
> 所以 28 项对应 **69 个数值参数**。数字可自行复核：
> `python tools/ini_compare.py rulesmo_original.ini rulesmo.ini` 会输出差异总数。

---

## 二、玩家：安装与还原

### 安装

1. 到本仓库的 **Releases** 页面下载最新发布包（`MO-Balance-Patch-v1.0.1.zip`）；
2. **完整解压**（不要只把其中一个文件拖出来）；
3. **完全退出游戏**（包括后台的 `MentalOmegaClient.exe`）；
4. 双击 **`安装.bat`**，看到「安装完成」即可。

安装脚本会自动定位游戏目录（找不到时可以把游戏文件夹拖进窗口）；
安装前会自动备份你原有的 `rulesmo.ini`，不会覆盖丢失。

### 还原

双击 **`恢复原版.bat`**：

- 如果安装前你已有自己的 `rulesmo.ini`，会还原成你原来那份；
- 如果没有，就删掉补丁文件，回到完全原版状态。

卸载**永远安全**：MIX 包里的原版规则文件从未被改动，删掉 `rulesmo.ini` 即恢复原版。

### 装完怎么确认生效

进游戏随便开一局遭遇战，看造价最直观：**光棱坦克应为 1050**（原 1450）、
**雷神炮艇应为 1800**（原 2000）、**铁骑兵应为 350**（原 450）。
完整验证清单、常见报错与排查步骤见 [`release/使用说明.txt`](release/使用说明.txt)。

---

## 三、开发者：从抽取基准到部署

### 前置条件

- **Windows 10/11**（部署与游戏内验证；构建/比对本身跨平台）
- **Python 3.9+**，只用标准库，**无需 `pip install` 任何东西**
- **自备 Mental Omega 3.3.6**：游戏目录下需有 `gamemd.exe` 与 `expandmo99.mix`
  （**版本必须正好是 3.3.6**，本补丁的「原值」全部取自该版本的 `rulesmo.ini`，其它版本数值对不上）

> 仓库**不含任何游戏文件**。原版规则文件必须由你从自己的游戏安装中提取。

### 1. 抽取原版基准

```bash
git clone https://github.com/micaholic125/dsh-mission-3.3.6.git
cd dsh-mission-3.3.6

# 从你自己的 expandmo99.mix 里抽出原版 rulesmo.ini（输出 rulesmo_original.ini，只读基准）
python tools/extract_rules.py --game-dir "<游戏安装目录>"
```

默认输出到仓库根的 `rulesmo_original.ini`，**已存在时不会覆盖**（内容一致则跳过）；
要重抽请加 `--force`。加 `--strict` 会在提取结果与已知 3.3.6 基准
（2,290,321 字节 / 固定 sha1）不符时直接报错，适合确认自己的游戏版本。

`<游戏安装目录>` 是**示例占位**（例如 `D:\Games\Mental Omega`）。
不想每次带参数，可以设环境变量，之后所有工具都会自动找到游戏目录：

```bat
:: cmd
set "MO_GAME_DIR=D:\Games\Mental Omega"
```

```powershell
# PowerShell
$env:MO_GAME_DIR = "D:\Games\Mental Omega"
```

### 2. 改数值

所有平衡改动都写在 [`changes/`](changes/) 的 JSON 里，一条改动 = 一个 `[节] + 键 = 新值`：

```json
{
  "batch": "batch5-2026-01-01",
  "note": "这一批做了什么、依据哪条 issue",
  "changes": [
    {"section": "APOC", "key": "Strength", "value": 500, "note": "天启坦克 血量 620→500"}
  ]
}
```

- 格式与硬性约定见 [`CONTRIBUTING.md`](CONTRIBUTING.md)
- 改动粒度、数值上下限、写入格式要求见 [`docs/03-设计规范.md`](docs/03-设计规范.md)

### 3. 构建覆盖文件

```bash
# 依次叠加所有批次；新增批次就追加到命令末尾（cmd/PowerShell 不会展开 *.json，请逐个列）
python tools/build_override.py changes/batch1.json changes/batch2.json changes/batch3.json changes/batch4.json
```

产物是仓库根目录的 `rulesmo.ini`（已在 `.gitignore` 中忽略，不会进版本库）。
想先看改动明细而不落盘，加 `--dry-run`；要输出到别处用 `--out <路径>`。

### 4. 校验条数

```bash
# 差异条数必须等于 changes 里的条数，多一条少一条都要停下来查
python tools/ini_compare.py rulesmo_original.ini rulesmo.ini
```

不带参数时默认比对仓库根的 `rulesmo_original.ini` ↔ `rulesmo.ini`；明细太多可用 `--limit 50` 限制。

### 5. 部署 / 体检 / 回滚

```bash
python tools/deploy.py check      # 只读：游戏是否在运行、目录是否正确、当前部署的是哪一版
python tools/deploy.py deploy     # 先备份到 backup/<时间戳>_deploy/，再写入游戏目录并校验
python tools/deploy.py rollback   # 删除覆盖文件，恢复原版（备份可回滚）
```

写游戏目录前会自动确认游戏未运行并强制备份。游戏目录解析顺序：
`--game-dir` 参数 > 环境变量 `MO_GAME_DIR` > 自动探测常见安装位置；
另有 `drill`（回滚演练）等动作，见 `python tools/deploy.py --help`。
`--game-dir` 写在动作之后即可：`python tools/deploy.py check --game-dir "D:\Games\Mental Omega"`。

### 6. 打包发布（维护者）

```bash
python tools/make_release.py v1.0.1     # 生成 dist/MO平衡补丁_v1.0.1/ 与 ASCII 命名的 zip
```

发布包内容：`安装.bat` / `恢复原版.bat` / `使用说明.txt` / 改动清单 / 平衡公告 / `_internal/`（补丁本体）。
成品包**不进仓库**，作为 GitHub Release 附件发布。

---

## 四、目录结构

```
.
├─ changes/              # 改动清单（本项目的"源码"）：每批一个 JSON，按顺序叠加构建
├─ docs/                 # 需求与范围、技术方案、设计规范、执行步骤、安全规范、数据参考、核对记录
├─ devlog/               # 开发日志（按日，四段式：完成/代办/风险/下一步）
├─ release/              # 打包进 Release 的一键安装/还原脚本与使用说明
├─ tools/                # 工具链：提取、改值、比对、构建、部署、打包（纯标准库）
├─ 公告-定稿.md           # v1.0.1 完整公告（玩家视角，含 28 条「原值 → 新值」）
├─ 需求.md                # 改动请求模板与提交流程
├─ AGENT.md              # 维护与协作说明（多 agent 并行改文件时的约定）
├─ CONTRIBUTING.md       # 贡献指南：提建议、提 PR、提交前自检
├─ CHANGELOG.md          # 版本历史
├─ LICENSE               # MIT（游戏数据不在许可范围，见文末）
└─ .github/              # CI（语法/清单结构/无游戏数据）与 issue 模板
```

**本地生成、不进版本库**（由脚本产出，随时可重建）：

| 文件 | 来源 | 说明 |
|---|---|---|
| `rulesmo_original.ini` | `tools/extract_rules.py` | 从你自己的 `expandmo99.mix` 抽出的原版基准，**只读** |
| `rulesmo.ini` | `tools/build_override.py` | 覆盖文件：基准 + 所有批次改动 |
| `单位名录.csv` / `单位名录_自检报告.md` | `tools/make_unit_catalog.py` / `tools/check_catalog.py` | 中文名 ↔ 节点 ID ↔ 数值的检索表与歧义自检 |
| `dist/` | `tools/make_release.py` | 发布成品包，作为 Release 附件 |
| `backup/` | `tools/deploy.py` | 部署/回滚前的快照（含游戏文件副本，**绝不入库**） |

---

## 五、这个项目怎么运转

1. **数值改动只有一个入口**：`changes/*.json`。想改什么，先改清单，再构建；
2. **一次一批**：一批一个文件，单批建议 ≤ 20 条，便于定位与回滚；
3. **条数必须对得上**：构建后差异条数必须等于清单条数，多一条少一条都要停下来查；
4. **数值必须逐键核对**：公告里写的「原值」都要与 `rulesmo_original.ini` 逐键比对确认；
5. **写游戏前必备份**：部署自动备份到 `backup/`，回滚只有一步（删覆盖文件）；
6. **过程留痕**：每轮改动写进 `devlog/`（完成 / 代办 / 风险 / 下一步）。

---

## 六、免责声明

- 本项目是**非官方**社区补丁，与 **Mental Omega 团队**、EA / Petroglyph 及其关联方**无关**，
  未获得其授权或认可；Mental Omega 及相关名称、素材的版权归其权利人所有。
- **本仓库不包含任何游戏数据**：不含 `.mix`、`.exe`、原版 `rulesmo.ini`，
  也不含从游戏提取/派生的名录数据。请自备正版 Mental Omega 3.3.6。
- 本补丁只修改**单机规则文件**的数值，不修改内存、不注入进程、不修改联机协议。
  但联机时双方规则不一致可能导致不同步，**建议与对手使用同一版本**。
- 使用本补丁造成的任何问题（存档异常、联机不同步、第三方工具冲突等）由使用者自行承担；
  按上文方法删除 `rulesmo.ini` 即可完全恢复原版。

## 七、许可

- **代码与文档**（`tools/`、`docs/`、`.github/`、`changes/` 等）：[MIT License](LICENSE)，© 2026 micaholic125
- **游戏数据与规则文件**（`rulesmo.ini`、`expandmo99.mix` 及其提取/衍生内容）：
  版权归 **Mental Omega 团队**所有，**不在 MIT 许可范围内**，本仓库也不分发它们。

## 八、致谢

- **Mental Omega 团队**——做出这款值得认真对待平衡的 MOD；
- 心灵终结中文社区的汉化者与资料整理者——中文单位名映射与对局经验大多来自社区；
- RA2 / YR 模组社区的公开 INI 文档与工具思路；
- 所有提交平衡建议、复测反馈与 Bug 报告的玩家。

> 想提建议：用 [Issue 模板](.github/ISSUE_TEMPLATE/)；想直接改数值：先读 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
