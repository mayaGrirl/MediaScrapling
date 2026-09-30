# MediaScrapling

[简体中文](#简体中文) · [English](#english)

MediaScrapling 把 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 和 [Scrapling](https://github.com/D4Vinci/Scrapling) 放进**同一个平台**。你只启动一个 worker，只维护一条 Redis 队列、一个代理池、一个 Cookie 库和一张 MySQL 结果表。

<a id="简体中文"></a>

## 简体中文

### 这个仓库是什么

| 部分 | 来源 | 在本平台里做什么 |
| --- | --- | --- |
| 平台能力 | [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | 小红书、抖音、快手、B 站、微博、贴吧、知乎。登录和站点采集留在上游，本仓库不复制它的源码。 |
| 网页能力 | [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | 普通网页的请求和 HTML 解析。`scrapling[fetchers]` 是本项目的 Python 依赖。 |
| 平台本身 | 本仓库 | 任务、队列、代理、会话、落库、可视化操作界面，以及两边互相交接。 |

合成之后的行为：

- 一个 `crawler worker` 同时消费两种任务。
- 网页里出现已知站点链接时，向**同一条队列**追加一条 MediaCrawler 任务。
- MediaCrawler 若返回 HTML，由 Scrapling 补同一条记录里空着的标题、视频地址、封面。
- 代理和 Cookie 只放在 Redis。两种能力都从这里读。

MediaCrawler 使用全局配置和浏览器，不能和 Scrapling 挤在同一个解释器里。worker 处理平台任务时会拉起短生命周期子进程。这个子进程没有自己的队列和数据库。

### 目录

```text
app/cli.py                 命令行：crawl / worker / jobs / proxy-add
app/platform/config.py     从 .env 读取配置
app/platform/models.py     Job、VideoItem、域名到平台的映射
app/platform/queue.py      Redis 列表 crawler:jobs
app/platform/proxy.py      Redis 集合 crawler:proxies
app/platform/session.py    Redis 键 crawler:session:{平台名}
app/platform/store.py      MySQL 表 jobs、videos
app/platform/worker.py     唯一消费循环
app/capabilities/web.py    Scrapling 抓取与字段解析
app/capabilities/media.py  调用 MediaCrawler 一次并读回 JSON
app/cooperate.py           HTML 补字段；已知链接升级为平台任务
docker/                    一个 platform 服务 + Redis + MySQL
scripts/run_local.ps1      Windows 本机启动 worker
tests/                     不访问外网的单元测试
third_party/MediaCrawler   需要你自己 clone，已在 .gitignore
```

### 环境要求

- Python 3.12 或更高版本
- 可连接的 Redis。本仓库客户端使用 RESP2，兼容不支持 `HELLO` 的旧 Redis
- 可连接的 MySQL 8，库和账号需要已建好，字符集 `utf8mb4`
- 可选：本机 clone 的 MediaCrawler。没有它时网页任务仍能跑，平台任务会记为失败

建议用 [uv](https://docs.astral.sh/uv/) 安装依赖。没有 uv 时用 `pip install -e ".[dev]"`。

### 配置

复制示例文件，只改本机的 `.env`。`.env` 已忽略，不要提交。

```powershell
copy .env.example .env
```

| 变量 | 含义 | 示例 |
| --- | --- | --- |
| `APP_ENV` | 环境名，当前代码只保存它 | `local` |
| `REDIS_URL` | 队列、代理池、Cookie | `redis://127.0.0.1:6379/0` |
| `MYSQL_URL` | SQLAlchemy 连接串，带 utf8mb4 | `mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE?charset=utf8mb4` |
| `MEDIACRAWLER_HOME` | MediaCrawler 仓库根目录，里面要有 `main.py` | `third_party/MediaCrawler` |
| `MEDIA_TIMEOUT_SECONDS` | 单次 MediaCrawler 子进程超时 | `900` |

远程 MySQL 时，把 `HOST` 换成服务器地址，并确认该账号可以从你的机器访问 3306。密码里如果有 `@`、`:`、`/`，要做 URL 编码。

MediaCrawler：

```powershell
git clone https://github.com/NanmiCoder/MediaCrawler third_party/MediaCrawler
```

按上游 README 在该目录里安装它自己的依赖和浏览器。本平台优先使用 `third_party/MediaCrawler/.venv` 里的 Python；没有虚拟环境时，用当前解释器执行它的 `main.py`。

### 安装与检查

在仓库根目录：

```powershell
uv sync --extra dev
uv run pytest
uv run crawler --help
```

`pytest` 只检查路由、命令拼装和 HTML 解析，不请求网站，也不连接你的数据库。

### 日常操作

先保证 Redis 和 MySQL 可用，然后启动控制台。这条命令会同时跑 worker，并打开浏览器。

```powershell
uv run crawler ui
```

浏览器地址是 `http://127.0.0.1:8080`。服务先完成监听，再打开浏览器。页面上可以填写 `http` 或 `https` 网址入队、添加代理、查看任务。列表按创建时间倒序，每 3 秒刷新。网页里发现的已知站点链接会作为新任务出现在同一张表里。

`--host 0.0.0.0` 时页面仍用本机 `127.0.0.1` 打开。不需要弹浏览器时加 `--no-browser`。

仍然可以用命令行：

```powershell
uv run crawler crawl https://example.com
uv run crawler worker
```

| URL 主机 | capability | platform |
| --- | --- | --- |
| xiaohongshu.com | media | xhs |
| douyin.com、v.douyin.com | media | dy |
| kuaishou.com | media | ks |
| bilibili.com、b23.tv | media | bili |
| weibo.com、m.weibo.cn | media | wb |
| tieba.baidu.com | media | tieba |
| zhihu.com | media | zhihu |
| 其它 | web | 空 |

查看最近任务：

```powershell
uv run crawler jobs --limit 20
```

输出格式：`任务ID 状态 capability URL 错误信息`。状态为 `pending`、`running`、`done`、`failed`。

只处理队列里当前的一条然后退出（适合试跑）：

```powershell
uv run crawler worker --once
```

加入代理。worker 在任务自己没带代理时，从池里随机取一条。

```powershell
uv run crawler proxy-add http://127.0.0.1:7890
```

Windows 也可以：

```powershell
powershell -File scripts/run_local.ps1
```

它会执行 `uv sync --extra dev`，在没有 `.env` 时从示例复制，然后启动 worker。

### 一次任务实际发生了什么

1. `crawler crawl` 调用 `classify()`，写入 Redis 列表 `crawler:jobs`，并在 MySQL `jobs` 插入 `pending`。
2. worker `BLPOP` 到任务后标为 `running`。
3. 网页任务：进程内 `scrapling.fetchers.Fetcher.get`。代理来自任务或代理池。若任务有 `cookie_key`，从 `crawler:session:{key}` 读取并放到 `Cookie` 头。
4. 抓到的 HTML 用 Scrapling `Selector` 取 `title`、`video/source` 的 `src`、`og:video`、`og:image`。
5. HTML 里每个链接再经过 `classify()`。已知站点会再入队一条 `media` 任务，并带上当前代理。
6. 平台任务：子进程执行 `main.py --platform <代码> --type detail --lt qrcode`，工作目录是 `MEDIACRAWLER_HOME`。环境变量有 `CRAWLER_PROXY`、`CRAWLER_COOKIE`、`CRAWLER_KEYWORD`、`CRAWLER_URL`。
7. 子进程退出码为 0 时，优先读 `MEDIACRAWLER_HOME/data/platform_result.json`。没有这个文件时，尝试把 stdout 最后一行当 JSON。
8. JSON 里的 `html` 再交给 Scrapling 补空字段。结果写入 `videos`。
9. 失败时 `jobs.error` 保存异常文本，worker 继续下一条。缺 MediaCrawler 目录时不会把整个 worker 打崩。

`videos` 列：`job_id`、`platform`、`source_url`、`title`、`video_url`、`cover_url`、`raw`。

`platform_result.json` 建议字段：

```json
{
  "url": "https://www.bilibili.com/video/BV1xx",
  "title": "",
  "video_url": "",
  "cover_url": "",
  "html": "<html>...</html>"
}
```

上游 MediaCrawler 默认把数据写到它自己的 CSV、JSON 或数据库，**不会**自动产生 `platform_result.json`，也**不会**读取 `CRAWLER_PROXY` 这些变量。这是当前骨架的边界。二次开发要在 `app/capabilities/media.py` 里把平台任务包映射成上游真实配置，或在上游外包一层，把结果写成上面的 JSON。

当前 CLI 的 `crawl` 总是带 URL，因此子进程 `--type` 目前总是 `detail`。`keyword` 会写入任务和环境变量 `CRAWLER_KEYWORD`，但还没有单独的搜索入队命令。

Cookie 还没有 CLI。代码里写入方式：

```python
from app.platform.context import PlatformContext

ctx = PlatformContext.open()
ctx.sessions.put("bili", "SESSDATA=...")
```

键名与平台代码一致：`xhs`、`dy`、`ks`、`bili`、`wb`、`tieba`、`zhihu`。

### Docker

在仓库根目录：

```powershell
docker compose -f docker/docker-compose.yml up --build
```

三个服务：`redis`、`mysql`、`platform`。`platform` 监听 `8080`，容器内执行 `crawler ui --host 0.0.0.0 --no-browser`。浏览器打开 `http://127.0.0.1:8080`。`platform` 的 Redis 和 MySQL 指向 compose 内部主机名，并把 `third_party/MediaCrawler` 挂到 `/opt/MediaCrawler`。

要用自己的远程 MySQL 时，改 `docker/docker-compose.yml` 里 `platform.environment.MYSQL_URL`，不要把密码写进 README 或提交到 Git。

### 二次开发时改哪里

| 目标 | 修改 |
| --- | --- |
| 增加一个已知站点 | `app/platform/models.py` 的 `HOST_PLATFORM`。值必须是 MediaCrawler 的平台代码。 |
| 改网页抽字段 | `app/capabilities/web.py` 的 `parse_html`。保持返回 `title`、`video_url`、`cover_url`。 |
| 改两种能力如何交接 | `app/cooperate.py`。`enrich_with_web` 只补空字段。`promote_known_links` 负责入队。 |
| 改 MediaCrawler 调用方式 | `app/capabilities/media.py` 的 `command` 和 `_read_result`。 |
| 改表结构 | `app/platform/store.py`。当前只在启动时 `create_all`，没有迁移工具。改列后需要自己处理已有表。 |
| 加命令或页面 | `app/cli.py`、`app/server.py`、`app/console.html`。页面文件要随包发布，已写在 `pyproject.toml` 的 package-data 里。 |
| 加测试 | `tests/`。不要在测试里请求外站或依赖真实 Redis。 |

执行一条任务的入口是 `app.platform.worker.execute`。新能力不要自己连数据库，通过 `PlatformContext` 使用队列、代理、会话和 `Store`。

### 测试

```powershell
uv run pytest
```

### 许可与使用范围

MediaCrawler 上游是非商业学习许可。Scrapling 使用它自己的许可证。使用本平台采集公开数据时，同时遵守两个上游的许可证、目标站点条款，以及你所在地的法律。不要用它做未授权访问或绕过访问控制。

<a id="english"></a>

## English

MediaScrapling is the control plane for [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) and [Scrapling](https://github.com/D4Vinci/Scrapling). One worker, one Redis queue, one proxy pool, one cookie store, one MySQL schema.

### What lives where

| Piece | Source | Responsibility here |
| --- | --- | --- |
| Platform capability | [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | Xiaohongshu, Douyin, Kuaishou, Bilibili, Weibo, Tieba, Zhihu. This repo does not vendor that code. |
| Web capability | [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | HTTP fetch and HTML parsing via the `scrapling[fetchers]` dependency. |
| Platform | This repo | Jobs, queue, proxies, sessions, storage, the browser console, and the hand-off between the two. |

A page fetched by Scrapling that links to a known host enqueues a MediaCrawler job on the same queue. HTML returned by MediaCrawler is parsed by Scrapling to fill an empty title, video URL, or cover. MediaCrawler runs as a short-lived child process because its global config and browser cannot share an interpreter with Scrapling.

### Layout

```text
app/cli.py                 crawl, worker, jobs, proxy-add
app/platform/              settings, models, Redis, MySQL, worker loop
app/capabilities/web.py    Scrapling fetch and parse
app/capabilities/media.py  one MediaCrawler subprocess per platform job
app/cooperate.py           fill fields from HTML; promote known links
docker/                    redis, mysql, one platform service
scripts/run_local.ps1      Windows worker start
tests/                     unit tests with no network
third_party/MediaCrawler   gitignored clone of MediaCrawler
```

### Requirements

Python 3.12+, Redis, and MySQL 8 (`utf8mb4`). The Redis client speaks RESP2 so older servers that reject `HELLO` still work. MediaCrawler is optional: web jobs run without it, and platform jobs fail with an error stored on the job row.

### Configure

```powershell
copy .env.example .env
```

| Variable | Meaning |
| --- | --- |
| `APP_ENV` | Label stored in settings. |
| `REDIS_URL` | Queue, proxy set, and cookies. |
| `MYSQL_URL` | `mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE?charset=utf8mb4` |
| `MEDIACRAWLER_HOME` | Directory that contains MediaCrawler `main.py`. |
| `MEDIA_TIMEOUT_SECONDS` | Subprocess timeout. Default 900. |

Do not commit `.env`. URL-encode reserved characters in the password.

```powershell
git clone https://github.com/NanmiCoder/MediaCrawler third_party/MediaCrawler
```

Install MediaCrawler's own dependencies in that directory. This platform uses `third_party/MediaCrawler/.venv` when it exists, otherwise the current Python.

### Install

```powershell
uv sync --extra dev
uv run pytest
uv run crawler --help
```

### Operate

Terminal:

```powershell
uv run crawler ui
```

This starts the worker and opens `http://127.0.0.1:8080` after the server is listening. The page accepts only `http` and `https` URLs, adds proxies, and refreshes the newest jobs every 3 seconds. Links to known hosts found on a web page show up in the same table. `--host 0.0.0.0` still opens `127.0.0.1`. Pass `--no-browser` to skip the window. `crawler crawl` and `crawler worker` remain available.

Host mapping: `xiaohongshu.com` → `xhs`, `douyin.com` → `dy`, `kuaishou.com` → `ks`, `bilibili.com` and `b23.tv` → `bili`, `weibo.com` → `wb`, `tieba.baidu.com` → `tieba`, `zhihu.com` → `zhihu`. Every other host is `web`.

`crawler crawl` classifies the URL, pushes JSON onto the Redis list `crawler:jobs`, and inserts a `pending` row in `jobs`. The worker sets `running`, then:

- Web: `Fetcher.get` in-process. Proxy comes from the job or `crawler:proxies`. A cookie is read from `crawler:session:{cookie_key}` when set. `parse_html` reads title, video `src`, and `og:image`. Known-host links become new `media` jobs.
- Media: `main.py --platform <code> --type detail --lt qrcode` with `cwd` set to `MEDIACRAWLER_HOME`. The child receives `CRAWLER_PROXY`, `CRAWLER_COOKIE`, `CRAWLER_KEYWORD`, and `CRAWLER_URL`. On exit 0 the worker reads `data/platform_result.json`, or the last stdout line if it is JSON. Scrapling fills empty title, video URL, and cover. The row goes to `videos`.

Upstream MediaCrawler does not emit `platform_result.json` and does not read those `CRAWLER_*` variables. Mapping a job onto MediaCrawler's real config, and writing that JSON, is the integration point in `app/capabilities/media.py`.

`crawl` always passes a URL, so `--type` is currently always `detail`. There is no CLI for cookies:

```python
from app.platform.context import PlatformContext
PlatformContext.open().sessions.put("bili", "SESSDATA=...")
```

### Docker

```powershell
docker compose -f docker/docker-compose.yml up --build
```

Override `platform.environment.MYSQL_URL` in the compose file when you want an external database. Do not commit the password.

### Where to extend

| Change | File |
| --- | --- |
| New known host | `HOST_PLATFORM` in `app/platform/models.py` |
| Extracted fields | `parse_html` in `app/capabilities/web.py` |
| Hand-off rules | `app/cooperate.py` |
| MediaCrawler command and result file | `app/capabilities/media.py` |
| Tables | `app/platform/store.py` (`create_all` only, no migrations) |
| CLI and console | `app/cli.py`, `app/server.py`, `app/console.html` |

Call `app.platform.worker.execute` for one job. New capabilities should use `PlatformContext` instead of opening their own database clients.

### Tests

```powershell
uv run pytest
```

Follow the licenses of both upstream projects and the terms of the sites you collect from. This platform is for public data you are allowed to collect. It is not a tool for unauthorized access.
