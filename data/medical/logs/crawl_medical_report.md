# 医疗新闻爬虫运行报告

生成时间：2026-06-16 22:01:30

| 数据源 | URL | 状态 | 条数 | 失败原因 |
|---|---|---|---:|---|
| 新华健康-首页 | https://www.news.cn/health/ | success | 30 |  |
| 新华健康-大健康 | https://www.news.cn/health/djk/index.html | success | 26 |  |
| 新华健康-科普汇 | https://www.news.cn/health/kph/index.html | success | 20 |  |
| 新华健康-视屏区 | https://www.news.cn/health/spq/index.html | success | 24 |  |
| 新华健康-权威发布 | https://www.news.cn/health/qwfb/index.html | success | 23 |  |
| 新华健康-重要资讯 | https://www.news.cn/health/zyzy/index.html | success | 26 |  |
| 新华健康-热点专题 | https://www.news.cn/health/rdzt/index.html | success | 11 |  |
| 央广网健康-央广 | https://health.cnr.cn/yg/ | success | 250 |  |
| 央广网健康-健康今日热点 | https://health.cnr.cn/jkjrjd/ | success | 250 |  |
| 央广网健康-医药企业 | https://health.cnr.cn/yyqy/ | success | 96 |  |
| 央广网健康-医药资讯 | https://health.cnr.cn/yyzx/ | success | 70 |  |
| 央广网健康-名医陪你 | https://health.cnr.cn/mypy/ | success | 30 |  |
| 央广网健康-何问中西 | https://health.cnr.cn/jkzt/hwzx/ | success | 17 |  |
| 央广网健康-苗岭名医 | https://health.cnr.cn/mlm/ | discarded | 1 | row count < 10 |

输出文件：`data/raw/medical_news_raw.csv`。
已删除 0 条的 `medical_comment_raw.csv`、`medical_drug_device_raw.csv`、`medical_insurance_raw.csv`、`medical_regulation_raw.csv`。
人民网健康、健康中国在当前环境下没有稳定可用的批量新闻列表，本轮未作为默认数据源。
