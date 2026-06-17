# Ticketmaster 活动下载器

从 Ticketmaster Discovery API 拉取活动，按时间 / 地点 / 关键词筛选，导出成 CSV。

## 怎么用

1. 打开 `run.py`，改里面的 `config` 字典（API key、时间、城市等）。
2. 运行：

```bash
python run.py
```

3. 结果写到 `config["out"]` 指定的 CSV 文件（默认 `events.csv`）。

只用到 Python 标准库，不需要装任何额外包。

## config 各项说明

| 键 | 说明 | 是否必填 |
|------|------|------|
| `apikey` | Ticketmaster API key（[免费申请](https://developer.ticketmaster.com)） | 必填 |
| `start_time` / `end_time` | 时间范围，UTC 格式 `2026-04-10T00:00:00Z` | 可选 |
| `city` | 城市名 | 可选 |
| `country_code` | 国家代码：US、GB、PK… | 可选 |
| `keyword` | 关键词搜索 | 可选 |
| `out` | 输出 CSV 文件名 | 可选，默认 `events.csv` |
| `size` | 每页数量（最大 200） | 可选，默认 100 |
| `max_pages` | 最多翻几页 | 可选，默认 5 |

不需要的项删掉或留空即可。

## 两个文件

- `run.py` —— 你只需要改这里的 config，然后运行。
- `ticketmaster_download.py` —— 实际逻辑：`download(config)` 负责拉取、转换、写 CSV。

## CSV 列

```
name, description, location_name, latitude, longitude, address,
start_time, end_time, city, primary_category, secondary_categories,
thumbnail_image, additional_images, external_link, is_paid
```
