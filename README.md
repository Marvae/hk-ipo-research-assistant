# 港股打新研究助手

港股 IPO 打新数据工具，供 AI 分析。

## 功能

- 实时孖展（13+ 券商明细）
- 基石投资者（名单、金额、锁定期）
- 保荐人历史战绩
- A+H 折价计算
- 中签率预测表格
- 历史数据统计

## 安装

**AI Agent**

把链接丢给你的 agent：`https://github.com/Marvae/hk-ipo-research-assistant`

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

- [AiPO](https://aipo.myiqdii.com) — 孖展、基石、评级、暗盘
- [集思录](https://www.jisilu.cn) — 历史数据、保荐人战绩
- [TradeSmart](https://lowrisktradesmart.org) — 中签率算法
- [港交所披露易](https://www.hkexnews.hk) — 招股书链接
- [东方财富](https://www.eastmoney.com) — A+H 折价计算

**数据来自第三方网站，可能存在延迟或错误。AI 分析结果取决于模型能力，可能存在幻觉或误判，仅供参考，不构成投资建议。用户需自行确保符合相关网站服务条款及当地法律法规。**

## License

MIT
