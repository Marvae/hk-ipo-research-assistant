# 港股打新研究助手

[![GitHub stars](https://img.shields.io/github/stars/Marvae/hk-ipo-research-assistant?style=flat)](https://github.com/Marvae/hk-ipo-research-assistant/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE.txt)
![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)

港股 IPO 打新数据工具，供 AI 分析。

*An AI Agent Skill for Hong Kong IPO subscription research — live margin financing data, cornerstone investors, sponsor track records, and allotment-odds prediction.*

> ℹ️ **数据源状态（2026-10）**：原主力数据源 AiPO（aipo.myiqdii.com）已被运营方下线（子域名 DNS 记录删除，2026-04 尚可访问、2026-06 起 NXDOMAIN，见 [issue #1](https://github.com/Marvae/hk-ipo-research-assistant/issues/1)），已切换至 AAStocks + 富途（均免登录）作为回退源：新股简况、基石投资者、配发结果（超购倍数/中签率）、暗盘涨跌幅均已恢复。仍缺：招股期实时孖展认购总额与逐券商认购明细、机构评级（无免登录替代源）。AiPO 恢复后会自动优先使用 AiPO。

## 功能

- 实时孖展（13+ 券商明细）
- 基石投资者（名单、金额、锁定期）
- 保荐人历史战绩
- A+H 折价计算
- 中签率预测表格
- 历史数据统计

## 安装

**AI Agent**

```bash
npx skills add Marvae/hk-ipo-research-assistant
```

或把链接丢给你的 agent：`https://github.com/Marvae/hk-ipo-research-assistant`

或使用 ClawHub：
```bash
clawhub install hk-ipo-research-assistant
```

**手动**

```bash
git clone https://github.com/Marvae/hk-ipo-research-assistant.git
cd hk-ipo-research-assistant/hk-ipo-research-assistant
pip3 install -r scripts/requirements.txt
```

## 使用

直接问 AI：
- "最近有什么港股新股？"
- "02692 值得打吗？"
- "帮我分析一下兆威机电"
- "中签率大概多少？"

## 命令参考

```bash
cd hk-ipo-research-assistant
python3 scripts/hkipo.py overview                      # 当前招股一览
python3 scripts/hkipo.py analyze 02692                 # 一键分析
python3 scripts/hkipo.py aipo margin-detail 02692      # 孖展明细
python3 scripts/hkipo.py aipo cornerstone 02692        # 基石投资者
python3 scripts/hkipo.py odds --oversub 38 --price 73  # 中签率表格
python3 scripts/hkipo.py jisilu list --sponsor 招商    # 保荐人历史
python3 scripts/hkipo.py ah compare 02692 --price 73.68 --name 兆威  # A+H折价
```

**输出示例**

```
$ python3 scripts/hkipo.py overview

📈 美格智能 (03268)
   孖展: 16.27 亿港元 | 入场费: 2915 港元 | PE: 59.2x

📈 兆威機電 (02692)
   孖展: 77.86 亿港元 | 入场费: 7442 港元 | PE: 82.0x
```

```
$ python3 scripts/hkipo.py odds --oversub 38 --price 73

    手数 │      金额 │   中签率 │ 分组
───────┼─────────┼────────┼─────
     1 │   36,865 │  0.134% │ 甲组
    10 │  368,650 │   1.11% │ 甲组
   135 │4,976,775 │  11.4%  │ 甲组
```

## 数据来源

- [AiPO](https://aipo.myiqdii.com) — 孖展、基石、评级、暗盘（2026-06 起不可用，保留優先級，恢復後自動切回）
- [AAStocks](https://www.aastocks.com) — 新股简况、基石投资者、配发结果（回退源）
- [富途](https://www.futunn.com) — 已上市新股暗盘/首日表现（回退源）
- [集思录](https://www.jisilu.cn) — 历史数据、保荐人战绩
- [TradeSmart](https://lowrisktradesmart.org) — 中签率算法
- [港交所披露易](https://www.hkexnews.hk) — 招股书链接
- [东方财富](https://www.eastmoney.com) — A+H 折价计算

**数据来自第三方网站，可能存在延迟或错误。AI 分析结果取决于模型能力，可能存在幻觉或误判，仅供参考，不构成投资建议。用户需自行确保符合相关网站服务条款及当地法律法规。**

## 同作者

- [douban-cli](https://github.com/Marvae/douban-cli) — 豆瓣命令行工具 + AI Agent Skill
- X: [@Marvae24](https://x.com/Marvae24)

## License

MIT
