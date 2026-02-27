# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), follows [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-02-27 (Preview)

### Philosophy
脚本只抓数据，AI 做分析。

### Features
- `fetch list` — 当前招股列表（含 A+H 识别）
- `fetch detail <code>` — 详细招股信息（保荐人、基石、回拨、机制 A/B）
- `fetch ah <code>` — A+H 折价计算
- `fetch calendar` — 按截止日分组
- `fetch history` — 历史 IPO 表现参考

### Data Sources
- AAStocks（招股信息、历史数据）
- 腾讯财经 API（A 股价格）

### Notes
- 所有命令输出纯 JSON
- 脚本失败时可直接访问 AAStocks 网页获取数据
