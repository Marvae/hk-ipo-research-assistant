# HK IPO Research Assistant / 港股打新研究助手

港股打新公开数据获取工具。可作为 OpenClaw Skill 使用，也可独立运行脚本。

**⚠️ 免责声明：本工具仅获取公开数据，不构成投资建议。所有分析和判断由 AI 基于公开信息生成，中签率、首日表现等均为估算，实际以官方公告为准。投资有风险，据此操作风险自担。**

## 作为 Skill 安装

```
把本项目 clone 到 skill 目录，Agent 会自动识别 SKILL.md
```

## 独立使用

```bash
pip install -r requirements.txt
cd scripts
python3 cli.py fetch list
python3 cli.py fetch detail 02715
python3 cli.py fetch ah 02715
python3 cli.py fetch calendar
python3 cli.py fetch history --limit 10
```

所有命令输出 JSON。

## 功能

| 命令 | 说明 |
|------|------|
| `fetch list` | 当前招股新股列表 |
| `fetch detail <code>` | 详细招股信息（保荐人、基石、募资用途、发行机制） |
| `fetch ah <code>` | A+H 折价分析 |
| `fetch calendar` | 按截止日分组，规划资金 |
| `fetch history` | 历史 IPO 表现（超购、中签率、首日涨幅） |

## 数据来源

- 招股信息：[AAStocks](http://www.aastocks.com/tc/stocks/market/ipo/upcomingipo)
- A 股价格：腾讯财经 API
- 繁简转换：OpenCC

脚本失败时，可直接访问 AAStocks 网页获取数据。

## 参考文档

- `references/ipo-mechanism.md` — 港股打新机制（甲乙组、回拨、红鞋、暗盘）
- `references/analysis-guide.md` — 新股分析要点
- `references/risk-preferences.md` — 风险偏好与策略

## ⚠️ 免责声明

本工具仅获取公开数据，不构成投资建议。所有分析由 AI 基于公开信息生成，中签率、首日表现等均为估算，实际以官方公告为准。投资有风险，据此操作风险自担。

---

MIT License | 禁止商业转售
