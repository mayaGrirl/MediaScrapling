# MediaScrapling

[English](#english) · [简体中文](#简体中文)

One platform that runs [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) and [Scrapling](https://github.com/D4Vinci/Scrapling) as two cooperating capabilities. You start one worker, use one Redis queue, one proxy pool, one cookie store, and one MySQL database.

<a id="english"></a>

## English

MediaCrawler already knows how to collect public posts from Xiaohongshu, Douyin, Kuaishou, Bilibili, Weibo, Baidu Tieba, and Zhihu. Scrapling already knows how to fetch normal and JavaScript pages and keep CSS or XPath selectors working when a page layout changes. This repository does not paste those two codebases together. It is the control plane both of them share.

| Piece | Role |
| --- | --- |
| [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | Platform capability. Login, signatures, and site-specific collection stay in that project. |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | Web capability. Fetching, adaptive parsing, and the in-process spider stay in Scrapling. |
| This repo | One queue, one proxy pool, one session store, one `VideoItem` table, one CLI. |

### Why one platform is better than running both tools

- One command (`crawler worker`) consumes social-site jobs and ordinary web jobs.
- A web page that links to Bilibili, Douyin, or the other known hosts becomes a MediaCrawler job on the same queue. Scrapling does not improvise those sites.
- When MediaCrawler returns HTML, Scrapling fills the empty title, video URL, and cover on the same record.
- Proxies and cookies are stored once in Redis. Both capabilities read that store. Neither keeps a private pool.
- Results land in one MySQL table, so you query one place instead of merging two exporters.
- MediaCrawler stays a short-lived child process because its global config and browser cannot share an interpreter with Scrapling. That isolation is inside the worker. There is no second service to start.

### Layout

```text
app/platform/          jobs, Redis queue, proxy pool, sessions, MySQL
app/capabilities/web.py    Scrapling fetch and parse
app/capabilities/media.py  one MediaCrawler run per platform job
app/cooperate.py       hand HTML to Scrapling; promote known links to media jobs
```

Clone MediaCrawler next to this app. It is not vendored.

```powershell
git clone https://github.com/NanmiCoder/MediaCrawler third_party/MediaCrawler
```

`scrapling` is a Python dependency of this project.

### Run locally

Python 3.12 or newer, Redis on `127.0.0.1:6379`, and a MySQL database you can reach.

```powershell
copy .env.example .env
uv sync --extra dev
uv run crawler proxy-add http://127.0.0.1:7890
uv run crawler crawl https://example.com
uv run crawler worker
```

`powershell -File scripts/run_local.ps1` does the same start.

Put the real MySQL URL only in `.env`. That file is gitignored.

### Docker

```powershell
docker compose -f docker/docker-compose.yml up --build
```

Services are Redis, MySQL, and one `platform` worker. Mount `third_party/MediaCrawler` at `/opt/MediaCrawler`. If that directory is missing, media jobs fail with a clear error and web jobs continue.

### Keywords

MediaCrawler, Scrapling, crawler, spider, web scraping, Xiaohongshu, Douyin, Bilibili, Kuaishou, Weibo, Zhihu, Tieba, Redis queue, proxy pool, unified crawler platform.

<a id="简体中文"></a>

## 简体中文

[MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 已经能采集小红书、抖音、快手、B 站、微博、贴吧、知乎的公开内容。[Scrapling](https://github.com/D4Vinci/Scrapling) 已经能抓普通网页和动态网页，并在页面结构变化后继续用选择器取字段。本仓库不是把两份源码拷进同一个目录，而是让它们共用同一套控制面。

| 部分 | 作用 |
| --- | --- |
| [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | 平台能力。登录、签名和站点采集逻辑留在原项目。 |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | 网页能力。请求、自适应解析和进程内 Spider 留在 Scrapling。 |
| 本仓库 | 一条队列、一个代理池、一个会话库、一张结果表、一个命令行。 |

### 合成一个平台的好处

- 只启动 `crawler worker`，社交平台任务和普通网页任务都由它消费。
- 网页里出现 B 站、抖音等已知站点链接时，自动变成同一条队列上的 MediaCrawler 任务，不由 Scrapling 硬抓这些站点。
- MediaCrawler 返回 HTML 时，由 Scrapling 补全同一条记录里的标题、视频地址和封面。
- 代理和 Cookie 只存在 Redis。两种能力都从这里读，不再各管一个代理池。
- 结果进同一张 MySQL 表，查询时不用合并两套导出文件。
- MediaCrawler 使用全局配置和浏览器，不能和 Scrapling 挤在同一个 Python 进程里，所以平台在处理平台任务时拉起短生命周期子进程。这个子进程没有自己的队列和数据库，使用者不需要再启动第二个程序。

### 目录

```text
app/platform/          任务、Redis 队列、代理池、会话、MySQL
app/capabilities/web.py    Scrapling 抓取与解析
app/capabilities/media.py  每个平台任务执行一次 MediaCrawler
app/cooperate.py       把 HTML 交给 Scrapling；把已知站点链接升级为平台任务
```

MediaCrawler 不放进本仓库，克隆到旁边：

```powershell
git clone https://github.com/NanmiCoder/MediaCrawler third_party/MediaCrawler
```

`scrapling` 是本项目的 Python 依赖。

### 本地运行

需要 Python 3.12 或更高版本、本机 Redis（`127.0.0.1:6379`），以及可连接的 MySQL。

```powershell
copy .env.example .env
uv sync --extra dev
uv run crawler proxy-add http://127.0.0.1:7890
uv run crawler crawl https://example.com
uv run crawler worker
```

也可以执行 `powershell -File scripts/run_local.ps1`。

真实数据库地址只写在 `.env`。该文件已在 `.gitignore` 中，不要提交。

### Docker

```powershell
docker compose -f docker/docker-compose.yml up --build
```

服务只有 Redis、MySQL 和一个 `platform` worker。把 `third_party/MediaCrawler` 挂到 `/opt/MediaCrawler`。目录不存在时，平台任务记失败，网页任务继续。

### 检索关键词

MediaCrawler、Scrapling、爬虫、spider、网页采集、小红书、抖音、B站、快手、微博、知乎、贴吧、Redis 队列、代理池、统一采集平台。
