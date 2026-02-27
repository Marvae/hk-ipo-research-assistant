---
name: hk-ipo-research-assistant
description: 港股打新研究助手。获取招股信息、分析对比、查历史参考。
---

# 港股打新研究助手

收集港股打新公开数据，辅助用户做研究功课。

**⚠️ 本工具仅获取公开数据，不构成投资建议。所有分析和判断由 AI 基于公开信息生成，中签率、首日表现等均为估算，实际以官方公告为准。投资有风险，据此操作风险自担。**

## 安装

```bash
pip install -r requirements.txt
```

## 数据工具

```bash
cd scripts

python3 cli.py fetch list              # 当前招股列表
python3 cli.py fetch detail <code>     # 单只详情
python3 cli.py fetch ah <code>         # A+H 折价（仅 A+H 股需要）
python3 cli.py fetch calendar          # 按截止日分组
python3 cli.py fetch history --limit N # 历史数据
```

输出纯 JSON。脚本失败时可直接访问数据源：
- 招股信息：http://www.aastocks.com/tc/stocks/market/ipo/upcomingipo
- 历史数据：http://www.aastocks.com/tc/stocks/market/ipo/listedipo.aspx

## A+H 判断

`fetch list` 和 `fetch detail` 已含 `is_ah_stock` 字段。
**只有 `is_ah_stock: true` 时**才需要调用 `fetch ah` 获取折价率。

## 分析框架

拿到数据后，按以下维度分析：

### 基本面
- 行业前景（热门 vs 传统）
- 公司质量（盈利、研发、地位）
- 募资用途（研发扩产 vs 还债补流）
- 保荐人（头部 vs 小行）

### 市场信号
- 基石投资者（明星基石？数量金额？）
- 公开发售比例（<5% 可能供不应求）
- A+H 折价（>30% 算大折价）
- 发行机制（A=有回拨，B=无回拨）

### 风险
- 行业周期、估值水平
- 超购预期（热门股中签率极低）
- 无基石风险

## 工作流程

### 用户问"最近有什么新股"
1. `fetch list` + `fetch calendar`
2. 按截止日分组呈现

### 用户问某只新股
1. `fetch detail <code>`
2. 若 `is_ah_stock: true` → `fetch ah <code>`
3. 读 `references/analysis-guide.md`
4. 按框架整理，可用 web search 补充财务/新闻

### 用户要对比同期新股
1. `fetch list` 获取列表
2. 逐只 `fetch detail`
3. A+H 股调用 `fetch ah`
4. 横向对比表格

### 用户问打新机制
读 `references/ipo-mechanism.md`（甲乙组、回拨、红鞋、暗盘）

## 数据补充（Web Search）

CLI 不含的信息需要 web search：

| 信息 | 搜索词 |
|------|--------|
| 财务数据 | `[公司名] 招股书 财务数据` |
| 行业分析 | `[行业] 2026 前景` |
| 实时超购 | `[股票名] 孖展 超购` |

## 个性化配置

配置文件：`config/user-profile.yaml`

```yaml
capital: 22000        # 打新本金（港元）
risk: conservative    # conservative / balanced / aggressive
margin: never         # never / cautious / active
broker: longbridge
fee: 99
```

## 输出原则

- 呈现信息，不强制下结论
- 利好风险都列出
- 标注数据来源（招股书 vs 网上 vs 估算）
- 预估处说明不确定性

## 参考文件

- `references/ipo-mechanism.md` — 打新机制详解
- `references/analysis-guide.md` — 分析要点
- `references/risk-preferences.md` — 风险策略

## ⚠️ 免责声明

本工具仅获取公开数据，不构成投资建议。中签率和首日表现均为 AI 估算，实际以公告为准。
