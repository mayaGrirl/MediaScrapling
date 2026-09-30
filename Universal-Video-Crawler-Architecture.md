# Universal Video Crawler
## 通用视频采集框架架构与开发规划

> 项目定位：基于 **MediaCrawler + Scrapling** 构建统一、可扩展、插件化的开源通用视频/网页数据采集框架。
>
> 核心原则：**两个项目不是简单并列安装，而是作为两个独立 Engine 接入统一 Core。**
>
> 本文档用于项目立项、架构设计、开发拆分、部署以及 GitHub 开源维护。

---

# 1. 项目目标

## 1.1 核心目标

构建一个开源的通用数据采集框架，统一处理：

- 视频网站
- 社交媒体平台
- 普通 Web 网站
- 动态 JS 网站
- HTML 页面
- 多分页内容
- 作者/用户信息
- 视频/图片/文章元数据
- 评论等公开数据
- 媒体资源后处理
- 数据持久化
- 任务队列
- Proxy 管理
- Session 管理
- 失败重试
- 并发采集
- 插件扩展

项目不将某一个具体网站写死在核心代码中，而是采用 **Engine + Adapter + Plugin** 架构。

---

# 2. 核心项目

## 2.1 MediaCrawler

MediaCrawler 作为：

> **平台专用采集 Engine**

主要负责已经存在专用采集逻辑的平台，例如：

- 抖音
- 小红书
- Bilibili
- 快手
- 微博
- 知乎
- 贴吧
- TikTok
- 其他后续平台

MediaCrawler 已经包含大量平台相关逻辑，因此原则上不重新实现这些平台能力，而是通过 Adapter 接入统一 Core。

官方仓库：

https://github.com/NanmiCoder/MediaCrawler

---

## 2.2 Scrapling

Scrapling 作为：

> **通用 Web Scraping Engine**

主要负责：

- 普通 HTTP 请求
- Async HTTP
- 动态网页
- Browser Fetching
- JS 页面
- CSS Selector
- XPath
- Adaptive Parser
- Spider
- 并发
- Session
- Proxy
- 通用网站采集

官方仓库：

https://github.com/D4Vinci/Scrapling

---

# 3. 总体架构

```text
                         ┌─────────────────────┐
                         │    Web / CLI API    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Task Manager     │
                         │ 任务创建/取消/重试   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Platform Detector  │
                         │ URL / Domain / Type │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  │                                   │
                  ▼                                   ▼
        ┌─────────────────────┐             ┌─────────────────────┐
        │ MediaCrawler Engine │             │  Scrapling Engine   │
        │                     │             │                     │
        │ 平台专用采集         │             │ 通用 Web 采集        │
        └──────────┬──────────┘             └──────────┬──────────┘
                   │                                   │
                   └─────────────────┬─────────────────┘
                                     ▼
                           ┌─────────────────────┐
                           │  Normalize Layer    │
                           │ 统一数据标准化        │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │    Data Pipeline    │
                           └──────────┬──────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
                 Redis              MySQL          Object Storage
                    │
                    ▼
              Media Pipeline
                    │
                    ▼
                  FFmpeg
                    │
              ┌─────┼─────┐
              ▼     ▼     ▼
             MP4   HLS   Cover
```

---

# 4. 设计原则

## 4.1 不直接合并两个上游项目

错误方案：

```text
UniversalCrawler/
├── MediaCrawler源码
└── Scrapling源码
```

然后让两个项目分别运行。

这只能算项目集合。

正确方案：

```text
UniversalCrawler
│
├── Core
├── Engine
├── Adapter
├── Plugin
├── Storage
├── Queue
├── Proxy
├── Session
└── Media Pipeline
```

MediaCrawler 和 Scrapling 都作为 Engine 接入。

---

# 5. Engine 设计

统一接口：

```python
from abc import ABC, abstractmethod


class CrawlerEngine(ABC):

    @abstractmethod
    async def crawl(self, task):
        pass

    @abstractmethod
    async def close(self):
        pass
```

---

# 6. MediaCrawler Engine

```text
MediaCrawler
      │
      ▼
MediaCrawlerAdapter
      │
      ▼
CrawlerEngine
      │
      ▼
Normalize
```

职责：

- 调用 MediaCrawler 平台实现
- 接收统一 Task
- 转换平台参数
- 获取平台数据
- 转换为统一 Model
- 将原始数据保留到 raw_data
- 将标准数据交给 Pipeline

---

# 7. Scrapling Engine

```text
Scrapling
    │
    ├── Fetcher
    ├── AsyncFetcher
    ├── StealthyFetcher
    ├── DynamicFetcher
    └── Spider
            │
            ▼
      ScraplingAdapter
            │
            ▼
       CrawlerEngine
```

职责：

- 普通网页采集
- 动态页面采集
- 通用视频页面识别
- CSS/XPath 数据提取
- Adaptive Parser
- Spider Crawl
- 页面级任务调度

---

# 8. Engine Factory

```python
class EngineFactory:

    engines = {
        "media": MediaCrawlerEngine,
        "scrapling": ScraplingEngine,
    }

    @classmethod
    def create(cls, engine_type):
        engine = cls.engines.get(engine_type)

        if not engine:
            raise ValueError(
                f"Unsupported engine: {engine_type}"
            )

        return engine()
```

---

# 9. 自动 Engine 选择

任务支持：

```json
{
  "engine": "auto",
  "url": "https://example.com/video/123"
}
```

处理流程：

```text
URL
 │
 ▼
Platform Detector
 │
 ├── 已知平台
 │      ↓
 │  MediaCrawler
 │
 └── 未知平台
        ↓
     Scrapling
```

例如：

```text
douyin.com
    ↓
MediaCrawler

xiaohongshu.com
    ↓
MediaCrawler

bilibili.com
    ↓
MediaCrawler

unknown-site.com
    ↓
Scrapling
```

---

# 10. Platform Registry

平台不应该写死在 Core。

```python
class PlatformRegistry:

    _platforms = {}

    @classmethod
    def register(cls, name, adapter):
        cls._platforms[name] = adapter

    @classmethod
    def get(cls, name):
        return cls._platforms.get(name)
```

插件可以注册：

```python
PlatformRegistry.register(
    "example",
    ExampleAdapter
)
```

---

# 11. 统一数据模型

## 11.1 VideoItem

```python
class VideoItem:

    id: str

    platform: str

    platform_id: str

    title: str

    description: str

    author_id: str

    author_name: str

    video_url: str

    cover_url: str

    duration: int

    publish_time: str

    play_count: int

    like_count: int

    comment_count: int

    share_count: int

    tags: list

    raw_data: dict
```

---

# 12. Author

```python
class Author:

    id: str

    platform: str

    platform_id: str

    username: str

    nickname: str

    avatar_url: str

    profile_url: str

    follower_count: int

    following_count: int

    video_count: int

    raw_data: dict
```

---

# 13. Comment

```python
class Comment:

    id: str

    platform: str

    platform_id: str

    video_id: str

    author_id: str

    content: str

    like_count: int

    publish_time: str

    parent_id: str | None

    raw_data: dict
```

---

# 14. MediaResource

```python
class MediaResource:

    id: str

    type: str

    url: str

    mime_type: str

    extension: str

    size: int | None

    duration: int | None

    width: int | None

    height: int | None

    checksum: str | None

    local_path: str | None

    storage_path: str | None
```

---

# 15. Task 模型

```json
{
  "id": "task_001",
  "url": "https://example.com/video/123",
  "engine": "auto",
  "platform": "auto",
  "task_type": "video",
  "priority": 10,
  "max_retry": 3,
  "status": "pending"
}
```

状态：

```text
pending
running
success
failed
retrying
cancelled
```

---

# 16. Redis 设计

Redis 作为统一任务系统。

推荐 Key：

```text
crawler:task:pending
crawler:task:running
crawler:task:success
crawler:task:failed

crawler:task:{id}

crawler:lock:{id}

crawler:proxy:pool

crawler:session:{platform}:{account}

crawler:rate:{domain}

crawler:stats:{date}
```

---

# 17. MySQL 设计

核心表：

```text
crawler_tasks
crawler_videos
crawler_authors
crawler_comments
crawler_media
crawler_platforms
crawler_proxies
crawler_sessions
crawler_logs
crawler_plugins
```

建议所有核心表包含：

```text
id
created_at
updated_at
deleted_at
```

---

# 18. Storage Pipeline

数据流：

```text
Engine
  ↓
Normalize
  ↓
Validate
  ↓
Deduplicate
  ↓
Pipeline
  ↓
MySQL
```

媒体：

```text
VideoItem
   ↓
MediaResource
   ↓
Download Queue
   ↓
Downloader
   ↓
FFmpeg
   ↓
Object Storage
```

---

# 19. 去重机制

视频唯一标识优先级：

```text
1. platform + platform_id
2. canonical URL
3. media URL
4. checksum
```

Redis：

```text
crawler:dedupe:{platform}:{platform_id}
```

MySQL：

```text
UNIQUE(platform, platform_id)
```

媒体文件可以使用：

```text
SHA256
MD5
文件大小 + URL
```

作为辅助去重依据。

---

# 20. Proxy Manager

统一代理接口：

```python
class ProxyManager:

    async def acquire(
        self,
        platform=None,
        domain=None
    ):
        pass

    async def release(
        self,
        proxy
    ):
        pass

    async def report_success(
        self,
        proxy
    ):
        pass

    async def report_failure(
        self,
        proxy
    ):
        pass
```

代理信息：

```text
id
host
port
username
password
protocol
country
provider
status
success_rate
failure_count
last_used_at
expires_at
```

---

# 21. Session Manager

统一管理：

```text
Cookie
User-Agent
Session
Browser Context
Platform Account
```

数据结构：

```text
platform
account_id
cookie
user_agent
proxy_id
status
last_used_at
expires_at
```

注意：

- Cookie 不应该写入 Git
- `.env` 不存真实 Cookie
- 生产环境应加密敏感 Session
- 日志不得输出 Cookie、Token、密码

---

# 22. Browser Manager

第一阶段只统一生命周期，不强行统一底层 Browser 对象。

```python
class BrowserManager:

    async def acquire(self, mode):
        pass

    async def release(self, browser):
        pass
```

支持：

```text
playwright
CDP
Scrapling browser session
```

未来再抽象：

```text
BrowserContext
Page
Session
```

---

# 23. Media Pipeline

媒体处理建议独立于爬虫 Engine。

```text
Crawler
   ↓
Media URL
   ↓
Media Task
   ↓
Downloader
   ↓
FFmpeg
   ↓
Transcoder
   ↓
Thumbnail Generator
   ↓
Storage
```

支持：

- MP4
- HLS
- MPEG-TS
- M3U8
- JPG
- PNG
- WebP
- GIF

---

# 24. FFmpeg

FFmpeg 主要负责：

- 视频封装
- 格式转换
- 音视频合并
- 缩略图
- 视频信息检测
- 分辨率检测
- 时长检测
- HLS/TS 处理
- 转码

示例：

```bash
ffprobe video.mp4
```

不要让 FFmpeg 逻辑进入 MediaCrawler 或 Scrapling Engine。

---

# 25. Spider 体系

Scrapling Spider 负责通用网站。

```text
Spider
│
├── GenericSpider
├── ArticleSpider
├── VideoSpider
├── ImageSpider
└── SitemapSpider
```

示例：

```python
class VideoSpider(Spider):

    name = "video"

    async def parse(self, response):

        yield {
            "title": ...,
            "video_url": ...,
            "cover_url": ...
        }
```

---

# 26. 插件系统

最终支持：

```text
plugins/
├── platform/
├── engine/
├── storage/
├── downloader/
└── middleware/
```

插件接口：

```python
class Plugin:

    name = "example"

    async def setup(self):
        pass

    async def shutdown(self):
        pass
```

---

# 27. 推荐目录结构

```text
universal-video-crawler/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── crawler.py
│   │   ├── engine.py
│   │   ├── factory.py
│   │   ├── task.py
│   │   ├── scheduler.py
│   │   └── pipeline.py
│   │
│   ├── engines/
│   │   ├── media_crawler/
│   │   │   ├── engine.py
│   │   │   └── adapter.py
│   │   │
│   │   └── scrapling/
│   │       ├── engine.py
│   │       ├── adapter.py
│   │       └── spider.py
│   │
│   ├── platforms/
│   │   ├── registry.py
│   │   ├── detector.py
│   │   └── adapters/
│   │
│   ├── models/
│   │   ├── task.py
│   │   ├── video.py
│   │   ├── author.py
│   │   ├── comment.py
│   │   └── media.py
│   │
│   ├── queue/
│   │   ├── redis.py
│   │   └── worker.py
│   │
│   ├── proxy/
│   │   ├── manager.py
│   │   └── pool.py
│   │
│   ├── session/
│   │   ├── manager.py
│   │   └── cookie.py
│   │
│   ├── storage/
│   │   ├── mysql.py
│   │   ├── redis.py
│   │   ├── json.py
│   │   └── object_storage.py
│   │
│   ├── media/
│   │   ├── downloader.py
│   │   ├── ffmpeg.py
│   │   └── thumbnail.py
│   │
│   └── middleware/
│       ├── retry.py
│       ├── rate_limit.py
│       ├── logging.py
│       └── metrics.py
│
├── plugins/
│   └── README.md
│
├── migrations/
│
├── tests/
│
├── scripts/
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── config/
│   ├── app.yaml
│   ├── database.yaml
│   ├── redis.yaml
│   └── proxy.yaml
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── LICENSE
```

---

# 28. 安装方案

## 28.1 Mac

推荐 Python 3.12。

```bash
brew install python@3.12
```

安装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

项目：

```bash
git clone <YOUR_REPOSITORY>
cd universal-video-crawler
```

安装：

```bash
uv sync
```

浏览器：

```bash
uv run playwright install chromium
```

启动：

```bash
uv run python -m app.main
```

---

# 29. Ubuntu 22.04

安装：

```bash
sudo apt update

sudo apt install -y \
    git \
    curl \
    ffmpeg \
    python3 \
    python3-venv
```

安装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

项目：

```bash
git clone <YOUR_REPOSITORY>

cd universal-video-crawler

uv sync
```

浏览器：

```bash
uv run playwright install chromium

uv run playwright install-deps chromium
```

---

# 30. Docker

推荐服务：

```text
crawler
redis
mysql
worker
```

开发环境：

```text
docker compose up -d
```

生产环境：

```text
crawler-api
crawler-worker-1
crawler-worker-2
crawler-worker-N
redis
mysql
```

Worker 可以水平扩展。

---

# 31. 推荐 Docker 架构

```text
                    Nginx
                      │
                      ▼
                 Crawler API
                      │
                      ▼
                    Redis
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
      Worker 1      Worker 2      Worker N
        │             │             │
        └─────────────┼─────────────┘
                      ▼
             MediaCrawler / Scrapling
                      │
                      ▼
                    MySQL
                      │
                      ▼
                 Object Storage
```

---

# 32. 配置文件

`.env.example`：

```env
APP_ENV=production
APP_DEBUG=false

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=crawler
MYSQL_USERNAME=root
MYSQL_PASSWORD=

FFMPEG_PATH=/usr/bin/ffmpeg

WORKER_CONCURRENCY=4

DEFAULT_ENGINE=auto
```

真实：

```text
.env
```

必须加入：

```text
.gitignore
```

---

# 33. CLI

建议统一 CLI：

```bash
crawler start
crawler stop
crawler status
crawler crawl URL
crawler task:list
crawler task:retry
crawler task:cancel
crawler worker
crawler platform:list
crawler plugin:list
crawler proxy:list
crawler stats
```

例如：

```bash
crawler crawl https://example.com/video/123
```

自动：

```text
URL
 ↓
Detector
 ↓
Engine
 ↓
Task
 ↓
Crawler
 ↓
Normalize
 ↓
Storage
```

---

# 34. API

未来提供 REST API：

```text
POST /api/tasks
GET  /api/tasks
GET  /api/tasks/{id}
POST /api/tasks/{id}/retry
POST /api/tasks/{id}/cancel

GET /api/videos
GET /api/videos/{id}

GET /api/platforms
GET /api/plugins

GET /api/proxies
GET /api/stats
```

---

# 35. 任务示例

```json
{
  "url": "https://example.com/video/123",
  "engine": "auto",
  "platform": "auto",
  "task_type": "video",
  "download_media": false,
  "max_retry": 3,
  "priority": 10
}
```

---

# 36. 日志

统一日志字段：

```text
timestamp
level
request_id
task_id
worker_id
engine
platform
url
duration
status
error
```

示例：

```text
INFO
task_id=task_001
engine=scrapling
platform=generic
status=success
duration=1.82s
```

敏感数据禁止输出：

```text
Cookie
Authorization
Password
Token
Proxy Password
Session Secret
```

---

# 37. Retry

建议指数退避：

```text
第 1 次：1s
第 2 次：2s
第 3 次：4s
第 4 次：8s
```

并设置最大重试次数。

不同错误分类：

```text
NetworkError
Timeout
HTTP 429
HTTP 403
HTTP 5xx
ParseError
BrowserError
StorageError
```

不要所有异常都无限重试。

---

# 38. Rate Limit

统一：

```text
domain
platform
proxy
account
```

维度控制。

例如：

```text
example.com
    ↓
RateLimiter
    ↓
1 request / second
```

出现 429 后自动降低并发。

---

# 39. 健康检查

```bash
crawler health
```

检查：

```text
Redis
MySQL
FFmpeg
Chromium
Proxy
Worker
Engine
Storage
```

输出：

```text
Redis       OK
MySQL       OK
FFmpeg      OK
Chromium    OK
Scrapling   OK
MediaCrawler OK
Worker      OK
```

---

# 40. Metrics

建议记录：

```text
tasks_total
tasks_success
tasks_failed
tasks_retry
requests_total
requests_success
requests_failed
response_time
download_bytes
download_success
download_failed
proxy_success_rate
engine_success_rate
platform_success_rate
```

未来可接：

- Prometheus
- Grafana

---

# 41. 测试策略

## Unit Test

测试：

```text
EngineFactory
PlatformDetector
Normalize
Task
ProxyManager
SessionManager
Deduplicate
Pipeline
```

## Integration Test

测试：

```text
Redis
MySQL
Scrapling
MediaCrawler
FFmpeg
```

## E2E

测试：

```text
Task
 ↓
Engine
 ↓
Parse
 ↓
Normalize
 ↓
Storage
 ↓
Media
```

---

# 42. 开发阶段

## Phase 1：基础框架

- [ ] 项目初始化
- [ ] pyproject.toml
- [ ] Core
- [ ] Task
- [ ] Engine
- [ ] Factory
- [ ] Redis
- [ ] MySQL

## Phase 2：Scrapling

- [ ] ScraplingAdapter
- [ ] Fetcher
- [ ] AsyncFetcher
- [ ] Browser
- [ ] Spider
- [ ] GenericVideoSpider

## Phase 3：MediaCrawler

- [ ] MediaCrawlerAdapter
- [ ] PlatformRegistry
- [ ] 平台映射
- [ ] Model Normalize
- [ ] 原始数据保存

## Phase 4：任务系统

- [ ] Worker
- [ ] Retry
- [ ] RateLimit
- [ ] ProxyManager
- [ ] SessionManager

## Phase 5：媒体

- [ ] Downloader
- [ ] FFmpeg
- [ ] Thumbnail
- [ ] Object Storage

## Phase 6：开源

- [ ] README
- [ ] CONTRIBUTING
- [ ] LICENSE
- [ ] CI
- [ ] Release
- [ ] Plugin SDK
- [ ] Documentation

---

# 43. 第一版 MVP

不要一开始就做所有功能。

第一版只做：

```text
Scrapling
+
MediaCrawler
+
Redis
+
MySQL
+
统一 VideoItem
+
EngineFactory
+
PlatformDetector
+
Worker
+
FFmpeg
```

先完成：

```text
URL
 ↓
Task
 ↓
Engine
 ↓
VideoItem
 ↓
MySQL
```

确认主流程稳定后，再加入：

```text
Proxy
Session
Plugin
Metrics
Object Storage
Web API
```

---

# 44. 最重要的架构边界

## Core 不应该知道具体平台细节

错误：

```python
if platform == "xxx":
    ...
```

正确：

```python
adapter = PlatformRegistry.get(platform)
adapter.crawl(task)
```

---

## Engine 不应该负责数据库

错误：

```text
Scrapling
 ↓
MySQL
```

正确：

```text
Scrapling
 ↓
VideoItem
 ↓
Pipeline
 ↓
MySQL
```

---

## Downloader 不应该负责爬网页

错误：

```text
Downloader
 ↓
寻找视频 URL
```

正确：

```text
Crawler
 ↓
获取 Media URL
 ↓
Downloader
```

---

# 45. 第三方站点 Adapter

框架只提供：

```python
class SiteAdapter:

    name = "example"

    async def detect(self, url):
        pass

    async def crawl(self, task):
        pass

    async def normalize(self, data):
        pass
```

具体站点作为 Plugin。

这样可以：

```text
Core
 │
 ├── 官方平台 Adapter
 │
 └── 第三方 Plugin
```

第三方插件可以独立发布。

---

# 46. 合规与安全

项目定位为：

> 用于公开、合法、有授权的数据采集、研究、测试和内容管理。

开发时必须：

- 遵守目标网站 Terms of Service
- 遵守 robots.txt 和适用的访问规则
- 遵守当地法律法规
- 尊重版权
- 不采集未经授权的私人数据
- 不绕过访问控制
- 不保存不必要的敏感信息
- 控制请求频率
- 提供域名/任务级暂停能力

项目文档中应明确：

> 本项目是通用采集基础设施，不保证任何特定网站始终可用，也不鼓励绕过网站访问控制或进行未经授权的数据采集。

---

# 47. GitHub Repository 建议

仓库名称：

```text
universal-video-crawler
```

简介：

```text
An extensible open-source video and web crawling framework powered by MediaCrawler and Scrapling.
```

中文：

```text
基于 MediaCrawler + Scrapling 的开源通用视频与 Web 数据采集框架。
```

Topics：

```text
python
crawler
web-scraping
web-crawler
video-crawler
scrapling
mediacrawler
playwright
redis
mysql
ffmpeg
spider
automation
```

---

# 48. License

在确定开源协议之前，需要分别检查：

- MediaCrawler License
- Scrapling License
- 第三方依赖 License

不要因为主项目使用 MIT/BSD 就默认所有集成代码都可以随意重新授权。

建议建立：

```text
THIRD_PARTY_LICENSES.md
```

记录：

```text
项目
版本
License
仓库
修改内容
```

---

# 49. Git 分支策略

建议：

```text
main
dev
feature/*
fix/*
release/*
```

开发：

```text
feature/scrapling-engine
feature/mediacrawler-engine
feature/redis-queue
feature/video-model
feature/ffmpeg-pipeline
```

稳定后：

```text
feature/*
   ↓
dev
   ↓
main
```

---

# 50. GitHub Actions

CI 至少检查：

```text
Python 3.11
Python 3.12
Python 3.13
```

执行：

```text
ruff
pytest
mypy
build
```

未来：

```text
Docker Build
Security Scan
Release
PyPI
```

---

# 51. 项目长期发展

最终可以形成：

```text
Universal Video Crawler
│
├── Core
├── MediaCrawler Engine
├── Scrapling Engine
├── Plugin SDK
├── Proxy Manager
├── Session Manager
├── Task Queue
├── Media Pipeline
├── API
├── Web UI
└── CLI
```

最终目标不是：

> “一个可以爬某几个网站的脚本集合”。

而是：

> **一个可以持续接入不同数据源、不同爬虫引擎和不同媒体处理能力的通用采集平台。**

---

# 52. 推荐技术栈

| 模块 | 技术 |
|---|---|
| Language | Python 3.11+ |
| Package Manager | uv |
| Platform Engine | MediaCrawler |
| Generic Engine | Scrapling |
| Browser | Playwright / CDP |
| Queue | Redis |
| Database | MySQL |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| HTTP | Scrapling / HTTPX |
| Media | FFmpeg |
| API | FastAPI |
| CLI | Typer |
| Logging | structlog / logging |
| Metrics | Prometheus |
| Container | Docker |
| Reverse Proxy | Nginx |
| CI | GitHub Actions |
| Object Storage | S3-compatible |

---

# 53. 最终架构总结

核心关系：

```text
                  Universal Video Crawler
                           │
                     ┌─────┴─────┐
                     │   Core    │
                     └─────┬─────┘
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
     MediaCrawler Engine          Scrapling Engine
             │                           │
       平台专用采集                   通用网页采集
             │                           │
             └─────────────┬─────────────┘
                           ▼
                    Normalize Layer
                           │
                           ▼
                     Unified Models
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                  Redis         MySQL
                    │
                    ▼
               Media Pipeline
                    │
                  FFmpeg
                    │
                    ▼
               Object Storage
```

最终原则：

**MediaCrawler = Platform Engine**

**Scrapling = Generic Web Engine**

**Core = Task / Queue / Proxy / Session / Normalize / Storage / Plugin**

**FFmpeg = Media Processing**

**Redis = Task & State**

**MySQL = Structured Data**

**Object Storage = Media**

**Plugin = Future Ecosystem**

这套设计可以作为项目的第一版正式架构文档，后续开发时优先保持 Core 与两个上游项目解耦。
