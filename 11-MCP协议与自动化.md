# 第十一册：MCP 协议与自动化

> **本章你将学到**
> - MCP（Model Context Protocol）是什么，为什么它被称为"Agent 世界的 USB-C"
> - MCP 的客户端-服务器架构和两种连接方式
> - 在 Hermes 中配置和接入 MCP 服务的完整流程
> - GitHub、Notion、Linear、Figma 等主流服务的 MCP 实战接入
> - Cron 定时任务系统的配置与模板
> - 多 Agent 编排和自动化流水线的设计方法
> - 自动化系统的安全与合规最佳实践

---

## 1. MCP 协议：Agent 世界的 USB-C

### 1.1 什么是 Model Context Protocol（MCP）

想象你买了一台新笔记本电脑。它有一个 USB-C 接口。你可以用这个接口充电、接显示器、连移动硬盘、接网线转接头、甚至外接显卡坞。一个接口，万能适配。

现在想象 AI Agent 也要"接外设"——查 GitHub 代码、读 Notion 文档、发 Slack 消息、查 Google 日历。在过去，每接一个"外设"，开发者都要写一套专门的对接代码，就像每台设备都要配一个专用充电器一样麻烦。

**MCP（Model Context Protocol，模型上下文协议）** 就是来解决这个问题的。它是 Anthropic 在 2024 年提出的开放协议，旨在为 AI Agent 和外部工具之间建立统一的通信标准。

用一句话概括：**MCP 让 AI Agent 接入外部服务，像插 USB-C 一样简单。**

### 1.2 MCP 诞生背景（Anthropic 提出）

在 MCP 出现之前，AI Agent 接入外部世界是一片混乱的"战国时代"：

- OpenAI 有 Function Calling，但只能和 OpenAI 的模型用
- LangChain 有 Tool 封装，但每个 Tool 都要单独写适配层
- 每家 SaaS 公司的 API 格式都不一样：有的用 REST，有的用 GraphQL，有的用 gRPC
- 认证方式五花八门：API Key、OAuth、JWT、HMAC...每个都要单独处理

开发者们的痛苦可想而知。每想接一个新服务，就要：
1. 读一遍该服务的 API 文档
2. 写 HTTP 客户端代码
3. 处理各种边界情况和错误码
4. 维护文档告诉 AI 这个工具能干什么
5. 每次 API 升级都要改代码

Anthropic 看到了这个问题。他们想：为什么不能像 USB 标准化硬件接口一样，标准化 AI 和工具的接口呢？于是 MCP 诞生了。

> **Tips**
> MCP 是一个**开放协议**，不是 Anthropic 的私有技术。任何 AI 平台、任何工具开发者都可以免费使用。这有点像 HTTP 协议——Tim Berners-Lee 发明了它，但整个互联网都在用。

### 1.3 设计理念与核心概念

MCP 的设计遵循三个核心原则：

**原则一：统一接口（Universal Interface）**

不管是连接 GitHub、Notion 还是你家智能灯泡，AI 都用同一套"语言"和它们对话。就像不管接什么设备，USB-C 的物理形状和电气协议都是一样的。

**原则二：自描述能力（Self-Describing）**

MCP Server 会主动告诉 AI："我能做这些事，参数是这样的，返回结果是那样的。"AI 不需要提前"学习"每个工具的用法，只需要在运行时读取 Server 的"自我介绍"。

**原则三：双向通信（Bidirectional）**

传统的 API 调用是"我问你答"的单向模式。MCP 支持双向通信——AI 可以请求工具执行操作，工具也可以主动向 AI 推送通知（比如你关注的 GitHub Issue 有人回复了）。

**核心概念速览：**

| 概念 | 类比 | 说明 |
|------|------|------|
| **MCP Client** | 笔记本电脑 | AI Agent 中负责连接外部工具的组件 |
| **MCP Server** | USB 外设 | 提供具体功能的服务端（如 GitHub MCP Server） |
| **Tool** | 外设功能 | Server 暴露给 AI 可调用的功能（如"创建 Issue"） |
| **Resource** | 文件系统 | Server 管理的可读数据（如"某份文档内容"） |
| **Prompt** | 快捷指令 | 预定义的提示模板 |

### 1.4 与传统 API 调用的区别

很多人问：MCP 不就是封装了一层 API 调用吗？有什么区别？

让我们用一个具体的例子来对比——让 AI 帮你创建一个 GitHub Issue：

**传统 API 调用方式：**

```python
# 开发者需要手写这个函数，并告诉 AI 怎么调用它
def create_github_issue(repo, title, body, labels=None):
    """
    创建 GitHub Issue
    参数：
      repo: 仓库名，格式 "owner/repo"
      title: Issue 标题
      body: Issue 内容
      labels: 标签列表，可选
    """
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"title": title, "body": body}
    if labels:
        data["labels"] = labels
    response = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers=headers,
        json=data
    )
    return response.json()

# 然后还要在系统提示词里告诉 AI：
# "如果你需要创建 GitHub Issue，调用 create_github_issue 函数，
#  参数 repo 必须是 owner/repo 格式..."
```

**MCP 方式：**

```yaml
# 配置文件中只需这一行
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
```

然后 AI 自动就知道：
- GitHub MCP Server 提供了哪些工具
- 每个工具需要什么参数
- 参数的类型和约束
- 返回值是什么格式

> **注意**
> MCP 不是替代 API，而是**标准化 API 的接入方式**。GitHub MCP Server 底层仍然在调用 GitHub REST API，但开发者不需要关心这些细节。就像 USB-C 不是替代电线，而是标准化了插头形状。

**对比总结：**

| 维度 | 传统 API 调用 | MCP |
|------|-------------|-----|
| 接入成本 | 高（读文档、写代码、维护） | 低（配置一行 YAML） |
| 自描述 | 无（需要手写文档） | 有（Server 自动声明能力） |
| 动态发现 | 不支持（代码写死） | 支持（运行时枚举工具） |
| 双向通信 | 不支持 | 支持（Server 可推送） |
| 生态互通 | 差（各平台不兼容） | 好（任何 MCP Client 都能接任何 MCP Server） |

---

## 2. MCP 架构详解

### 2.1 客户端-服务器模型

MCP 采用了经典的客户端-服务器（Client-Server）架构：

```
┌─────────────────────────────────────────────────────────────┐
│                      Hermes AI Agent                         │
│                                                              │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │  MCP Client │◄────►│  MCP Client │◄────►│  MCP Client │ │
│  │  (GitHub)   │      │  (Notion)   │      │  (Slack)    │ │
│  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘ │
│         │                    │                    │         │
│         └────────────────────┴────────────────────┘         │
│                         ▲                                   │
│                    AI Core Engine                            │
└─────────────────────────┬───────────────────────────────────┘
                          │ JSON-RPC 2.0
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  GitHub MCP     │ │  Notion MCP     │ │  Slack MCP      │
│  Server         │ │  Server         │ │  Server         │
│  (stdio/http)   │ │  (stdio/http)   │ │  (stdio/http)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │               │               │
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  GitHub API     │ │  Notion API     │ │  Slack API      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

**关键组件说明：**

- **MCP Client**：运行在 Hermes 内部，负责和 MCP Server 建立连接、发送请求、接收响应。每个 Server 对应一个 Client 实例。
- **MCP Server**：独立运行的进程或服务，暴露一组 Tools 和 Resources。它可以是本地进程（stdio 模式），也可以是远程服务（HTTP 模式）。
- **Transport Layer**：Client 和 Server 之间的通信通道，支持 stdio 和 HTTP/SSE 两种方式。
- **JSON-RPC 2.0**：MCP 的通信协议格式，所有消息都是 JSON-RPC 格式的。

### 2.2 stdio vs HTTP/SSE 两种连接方式

MCP 支持两种 Transport 模式，适用于不同场景：

#### stdio 模式（标准输入输出）

```
┌─────────────┐          stdin/stdout          ┌─────────────┐
│  MCP Client │◄──────────────────────────────►│  MCP Server │
│  (父进程)   │         (JSON-RPC 消息)         │  (子进程)   │
└─────────────┘                                └─────────────┘
```

**工作原理：**
- Hermes 启动时，用 `spawn` 启动 MCP Server 进程
- Client 通过 Server 的 stdin 发送 JSON-RPC 请求
- Server 通过 stdout 返回 JSON-RPC 响应
- 两者通过管道（pipe）通信

**适用场景：**
- 本地运行的 MCP Server（如 `npx` 启动的 Node.js 程序）
- 对安全性要求高的场景（不暴露网络端口）
- 简单部署，不需要配置防火墙

**优点：**
- 简单，不需要网络配置
- 安全，没有暴露端口
- 进程生命周期由 Client 管理，Server 随 Client 启动/停止

**缺点：**
- 只能本地运行，无法远程连接
- 一个 Server 进程只能服务一个 Client
- 不适合高并发场景

```yaml
# stdio 模式配置示例
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
```

#### HTTP/SSE 模式

```
┌─────────────┐      HTTP POST/GET       ┌─────────────┐
│  MCP Client │◄────────────────────────►│  MCP Server │
│             │                          │  (HTTP 服务)  │
│             │◄─────────────────────────│             │
│             │      SSE 推送              │             │
└─────────────┘                          └─────────────┘
```

**工作原理：**
- MCP Server 是一个独立的 HTTP 服务，监听某个端口
- Client 通过 HTTP POST 发送 JSON-RPC 请求
- Server 通过 HTTP Response 返回结果
- Server 可以通过 SSE（Server-Sent Events）主动向 Client 推送消息

**适用场景：**
- 远程部署的 MCP Server（如部署在云服务器上）
- 多个 Client 共享一个 Server 的场景
- 需要 Server 主动推送通知的场景

**优点：**
- 可以远程连接
- 支持多个 Client
- Server 可以主动推送（SSE）

**缺点：**
- 需要网络配置（端口、防火墙、HTTPS）
- 需要额外处理认证和安全性
- 部署复杂度更高

```yaml
# HTTP/SSE 模式配置示例
mcp_servers:
  remote-github:
    url: "https://mcp.example.com/github"
    headers:
      Authorization: "Bearer ${MCP_API_KEY}"
    # 是否使用 SSE 接收推送
    sse: true
```

> **Tips**
> 对于个人用户和小团队，**stdio 模式是最简单的选择**。大部分官方 MCP Server 都支持 `npx` 一键启动。只有当你需要多个 Hermes 实例共享一个 MCP Server，或者 Server 必须部署在远程时，才需要考虑 HTTP 模式。

### 2.3 消息格式与协议规范

MCP 使用 JSON-RPC 2.0 作为通信协议。所有消息都是 JSON 格式，分为三种类型：

#### 请求（Request）

Client 向 Server 发送的请求：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_issue",
    "arguments": {
      "repo": "owner/repo",
      "title": "发现 Bug",
      "body": "详情如下..."
    }
  }
}
```

#### 响应（Response）

Server 返回的成功响应：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Issue #42 已成功创建: https://github.com/owner/repo/issues/42"
      }
    ],
    "isError": false
  }
}
```

#### 通知（Notification）

Server 主动推送的通知（单向，不需要响应）：

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/resources/updated",
  "params": {
    "uri": "file:///project/src/main.py"
  }
}
```

**核心方法列表：**

| 方法 | 方向 | 说明 |
|------|------|------|
| `initialize` | C→S | 初始化连接，交换协议版本和能力 |
| `tools/list` | C→S | 获取 Server 提供的所有工具列表 |
| `tools/call` | C→S | 调用指定工具 |
| `resources/list` | C→S | 获取可用资源列表 |
| `resources/read` | C→S | 读取指定资源 |
| `prompts/list` | C→S | 获取可用提示模板 |
| `notifications/resources/updated` | S→C | 资源更新通知 |

### 2.4 工具声明与调用流程

**工具声明（Tool Declaration）** 是 MCP 最核心的设计之一。它让 AI 能够"动态发现"工具的能力，而不是依赖硬编码的提示词。

当 MCP Client 连接到 Server 后，第一件事就是调用 `tools/list`：

```json
// Client 请求
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}

// Server 响应
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "create_issue",
        "description": "在指定仓库创建一个新的 GitHub Issue",
        "inputSchema": {
          "type": "object",
          "properties": {
            "repo": {
              "type": "string",
              "description": "仓库名，格式：owner/repo"
            },
            "title": {
              "type": "string",
              "description": "Issue 标题"
            },
            "body": {
              "type": "string",
              "description": "Issue 内容"
            },
            "labels": {
              "type": "array",
              "items": {"type": "string"},
              "description": "标签列表"
            }
          },
          "required": ["repo", "title"]
        }
      },
      {
        "name": "search_issues",
        "description": "搜索 GitHub Issues",
        "inputSchema": {
          "type": "object",
          "properties": {
            "repo": {"type": "string"},
            "query": {"type": "string"},
            "state": {
              "type": "string",
              "enum": ["open", "closed", "all"]
            }
          },
          "required": ["repo", "query"]
        }
      }
    ]
  }
}
```

Hermes 拿到这个工具列表后，会把它转换成 AI 能理解的格式（通常是在系统提示词中描述这些工具）。当用户说"帮我创建一个 Issue"时，AI 就知道：

1. GitHub Server 有一个叫 `create_issue` 的工具
2. 它需要 `repo`、`title`、`body` 等参数
3. `repo` 是字符串类型，格式是 `owner/repo`
4. `title` 是必填的

然后 AI 会调用 `tools/call`：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "create_issue",
    "arguments": {
      "repo": "mycompany/project",
      "title": "首页加载速度过慢",
      "body": "在 3G 网络下，首页加载需要 8 秒以上..."
    }
  }
}
```

> **Tips**
> 这种"自描述"的设计意味着：即使 GitHub MCP Server 新增了一个工具（比如"创建 Discussion"），Hermes 不需要更新任何代码，下次连接时就能自动发现这个新工具。这就是 MCP 的扩展性优势。

---

## 3. Hermes 中的 MCP 配置

### 3.1 config.yaml 中的 mcp_servers 配置

Hermes 的 MCP 配置位于 `~/.hermes/config.yaml` 的 `mcp_servers` 节下。它的结构非常直观：

```yaml
# ~/.hermes/config.yaml

mcp_servers:
  # Server 名称（自定义，用于标识）
  github:
    # stdio 模式配置
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-github"
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
    # 允许 AI 调用的工具列表（权限控制）
    allowed_tools:
      - "search_repositories"
      - "create_issue"
      - "search_issues"
      - "get_issue"

  # 另一个 Server
  notion:
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-notion"
    env:
      NOTION_API_TOKEN: "${NOTION_TOKEN}"
    allowed_tools: []

  # HTTP 模式的 Server
  remote-tools:
    url: "https://mcp.internal.company.com/tools"
    headers:
      Authorization: "Bearer ${INTERNAL_API_KEY}"
    sse: true
    allowed_tools:
      - "query_database"
      - "send_notification"
```

**配置项说明：**

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `command` | string | stdio 模式下要执行的命令 |
| `args` | array | 命令参数 |
| `env` | object | 环境变量 |
| `url` | string | HTTP 模式下 Server 的地址 |
| `headers` | object | HTTP 请求头 |
| `sse` | boolean | 是否启用 SSE 推送 |
| `allowed_tools` | array | 允许 AI 调用的工具白名单（空数组表示允许所有） |

### 3.2 stdio 和 HTTP/SSE 模式示例

#### stdio 模式完整示例

```yaml
mcp_servers:
  # GitHub MCP Server
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
    allowed_tools:
      - "search_repositories"
      - "get_file_contents"
      - "create_issue"
      - "search_issues"
      - "create_pull_request"
      - "list_commits"

  # Notion MCP Server
  notion:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-notion"]
    env:
      NOTION_API_TOKEN: "${NOTION_TOKEN}"
    allowed_tools: []

  # PostgreSQL MCP Server
  postgres:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-postgres"]
    env:
      POSTGRES_URL: "${DATABASE_URL}"
    allowed_tools:
      - "query"

  # File System MCP Server（访问本地文件）
  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/Users/username/Documents"]
    allowed_tools:
      - "read_file"
      - "list_directory"
      - "search_files"
```

#### HTTP/SSE 模式完整示例

```yaml
mcp_servers:
  # 公司内部 MCP 服务
  company-tools:
    url: "https://mcp.internal.company.com/v1"
    headers:
      Authorization: "Bearer ${COMPANY_MCP_TOKEN}"
      X-Department: "engineering"
    sse: true
    allowed_tools:
      - "query_employee"
      - "book_meeting_room"
      - "request_leave"

  # 第三方 MCP 托管服务
  mcp-cloud:
    url: "https://api.mcp.cloud/v1/github"
    headers:
      X-API-Key: "${MCP_CLOUD_KEY}"
    sse: false
    allowed_tools: []
```

### 3.3 allowed_tools 权限控制

`allowed_tools` 是 MCP 配置中最重要的安全机制。它精确控制 AI 能调用哪些工具。

**场景一：只读权限**

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
    # 只允许读操作，禁止创建/修改
    allowed_tools:
      - "search_repositories"
      - "get_file_contents"
      - "search_issues"
      - "list_commits"
      - "get_commit"
```

**场景二：按仓库隔离**

```yaml
mcp_servers:
  github-readonly:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_READONLY_TOKEN}"
    allowed_tools:
      - "search_repositories"
      - "get_file_contents"
      - "search_issues"

  github-write:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_WRITE_TOKEN}"
    allowed_tools:
      - "create_issue"
      - "create_pull_request"
      - "create_branch"
```

**场景三：完全禁止**

```yaml
mcp_servers:
  dangerous-server:
    command: "npx"
    args: ["-y", "some-risky-server"]
    # 空数组 = 禁止所有工具
    allowed_tools: []
```

> **注意**
> `allowed_tools` 是**白名单机制**。如果一个工具不在列表里，AI 即使"知道"它的存在，也无法调用。这是防止 AI"误操作"的重要防线。

### 3.4 多个 MCP Server 并存

Hermes 支持同时连接任意数量的 MCP Server。当用户提出一个请求时，Hermes 会自动判断：

1. 需要调用哪个（些）Server
2. 调用 Server 中的哪个工具
3. 按什么顺序调用

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"

  notion:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-notion"]
    env:
      NOTION_API_TOKEN: "${NOTION_TOKEN}"

  slack:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-slack"]
    env:
      SLACK_BOT_TOKEN: "${SLACK_BOT_TOKEN}"
```

用户的请求："把 GitHub 上最近的 Bug 整理一下，写到 Notion 文档里，然后在 Slack 通知团队"

Hermes 的处理流程：
1. 调用 GitHub Server 的 `search_issues` 获取 Bug 列表
2. 调用 Notion Server 的 `append_page` 把结果写入文档
3. 调用 Slack Server 的 `send_message` 发送通知

> **Tips**
> 多个 MCP Server 协同工作时，Hermes 会自动处理依赖顺序。比如上面的例子，必须等 GitHub 返回结果后，才能写入 Notion。Hermes 的编排引擎会确保按正确顺序执行。

---

## 4. 实战：接入 GitHub

GitHub 是开发者最熟悉的平台，也是 MCP 生态中最成熟的 Server 之一。让我们从 GitHub 开始实战。

### 4.1 完整配置

```yaml
# ~/.hermes/config.yaml

mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
    # 根据你的需求选择允许的工具
    allowed_tools:
      # 仓库操作
      - "search_repositories"
      - "get_file_contents"
      - "list_branches"
      # Issue 操作
      - "search_issues"
      - "get_issue"
      - "create_issue"
      - "update_issue"
      - "add_issue_comment"
      # PR 操作
      - "create_pull_request"
      - "get_pull_request"
      - "list_pull_requests"
      - "merge_pull_request"
      # Commit 操作
      - "list_commits"
      - "get_commit"
      # 搜索
      - "search_code"
```

### 4.2 Token 获取

GitHub 的 MCP Server 需要 Personal Access Token（PAT）。

**获取步骤：**

1. 登录 GitHub，点击右上角头像 → Settings
2. 左侧菜单拉到底 → Developer settings → Personal access tokens
3. 选择 "Tokens (classic)" 或 "Fine-grained tokens"
4. 点击 "Generate new token"
5. 填写 Token 信息：
   - **Note**：Hermes MCP
   - **Expiration**：选择过期时间（建议 90 天，到期后轮换）
   - **Scopes**：勾选需要的权限：
     ```
     ✅ repo          —— 访问私有仓库（如需）
     ✅ read:org      —— 读取组织信息
     ✅ read:user     —— 读取用户信息
     ✅ read:project  —— 读取项目信息
     ```
6. 点击 "Generate token"
7. **立刻复制 Token**（页面关闭后无法再次查看）

```bash
# 保存到环境变量
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

> **注意**
> Fine-grained tokens 是 GitHub 推荐的新一代 Token，支持更精细的权限控制（可以限定只访问特定仓库）。如果你的公司安全要求严格，建议使用 Fine-grained tokens 替代 Classic tokens。

### 4.3 安全配置

GitHub Token 拥有你账号的访问权限，务必妥善保管：

```bash
# 1. 使用环境变量（基础）
export GITHUB_TOKEN="ghp_xxx"

# 2. 使用 GitHub CLI（推荐）
gh auth login
# 然后用 `gh auth token` 获取 Token

# 3. 使用 1Password CLI（最安全）
export GITHUB_TOKEN=$(op read "op://Private/GitHub/PAT")

# 4. 定期轮换（最佳实践）
# 设置日历提醒，每 90 天重置一次 Token
```

### 4.4 使用示例

配置完成后，重启 Hermes，你就可以直接用自然语言操作 GitHub 了：

**示例1：搜索代码**

```
你: 在 GitHub 上搜索 Hermes 项目里关于 memory 的实现
Hermes: 正在搜索...
Hermes: 找到 12 个相关文件，其中最核心的是：
  1. src/memory/short_term.py - 短期记忆实现
  2. src/memory/long_term.py - 长期记忆实现
  3. src/memory/hybrid.py - 混合记忆策略
  
  需要我查看某个文件的具体内容吗？
```

**示例2：创建 Issue**

```
你: 在我的项目 myapp 里创建一个 Issue，标题是"优化数据库查询性能"，
    内容是：首页加载时用户列表查询耗时超过 2 秒，需要添加索引

Hermes: 正在创建 Issue...
Hermes: ✅ Issue 已创建
  仓库: myname/myapp
  标题: 优化数据库查询性能
  链接: https://github.com/myname/myapp/issues/42
```

**示例3：分析 PR**

```
你: 帮我看看 #15 号 PR 改了哪些文件

Hermes: PR #15 "添加用户认证模块" 的变更概览：
  新增文件：
    - src/auth/login.py
    - src/auth/middleware.py
    - tests/auth/test_login.py
  修改文件：
    - src/main.py (+15/-3)
    - requirements.txt (+2)
  
  需要我查看具体代码差异吗？
```

> **常见问题**
> **Q: 为什么 AI 说"我没有权限"？**
> A: 检查两点：1) `allowed_tools` 里是否允许了这个操作；2) GitHub Token 是否有对应的权限（比如创建 Issue 需要 `repo` scope）。

---

## 5. 实战：接入 Notion

Notion 是知识管理和文档协作的神器。把 Notion 接入 Hermes 后，AI 可以帮你读写文档、管理数据库、整理知识库。

### 5.1 Notion Integration 创建

**步骤一：创建 Integration**

1. 访问 https://www.notion.so/my-integrations
2. 点击 "New integration"
3. 填写信息：
   - **Name**：Hermes Assistant
   - **Associated workspace**：选择你的 Notion Workspace
   - **Type**：Internal（自用）或 Public（公开发布）
   - **Logo**：上传一张图标（可选）
4. 点击 "Submit"

**步骤二：获取 API Key**

创建完成后，在 Integration 详情页找到 "Internal Integration Token"：

```
secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

```bash
export NOTION_TOKEN="secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

> **注意**
> Notion 的 Integration 默认**没有任何页面的访问权限**。你需要手动把页面分享给 Integration，这是 Notion 的安全设计。

**步骤三：授权页面访问**

1. 在 Notion 中打开你要让 AI 访问的页面
2. 点击右上角 "..." → "Add connections"
3. 搜索并选择你创建的 "Hermes Assistant"
4. 确认添加

> **Tips**
> 如果你希望 AI 能访问整个 Workspace 的所有页面，可以在 Integration 的 Capabilities 设置中开启 "Read user information including email addresses"。但建议按需授权，遵循最小权限原则。

### 5.2 API Key 配置

```yaml
mcp_servers:
  notion:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-notion"]
    env:
      NOTION_API_TOKEN: "${NOTION_TOKEN}"
    allowed_tools:
      # 页面操作
      - "notion_search"
      - "notion_retrieve_page"
      - "notion_retrieve_block_children"
      # 数据库操作
      - "notion_query_database"
      - "notion_create_database_item"
      # 写入操作（谨慎开启）
      - "notion_append_block_children"
      - "notion_update_page"
```

### 5.3 MCP 配置

上面的配置已经展示了完整的 MCP 配置。这里补充一些高级用法：

**只读模式（安全推荐）：**

```yaml
mcp_servers:
  notion-readonly:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-notion"]
    env:
      NOTION_API_TOKEN: "${NOTION_TOKEN}"
    allowed_tools:
      - "notion_search"
      - "notion_retrieve_page"
      - "notion_retrieve_block_children"
      - "notion_query_database"
```

**读写模式（需要时开启）：**

```yaml
mcp_servers:
  notion-write:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-notion"]
    env:
      NOTION_API_TOKEN: "${NOTION_TOKEN}"
    allowed_tools:
      - "notion_search"
      - "notion_retrieve_page"
      - "notion_query_database"
      - "notion_create_database_item"
      - "notion_append_block_children"
      - "notion_update_page"
```

### 5.4 使用场景

**场景1：知识库问答**

```
你: 查一下我们产品需求文档里关于"支付模块"是怎么设计的

Hermes: 正在搜索 Notion...
Hermes: 找到相关内容（来自页面"产品需求文档 v2.0"）：
  
  支付模块设计要点：
  1. 支持支付宝、微信支付、银联三种渠道
  2. 支付状态机：待支付 → 处理中 → 成功/失败
  3. 异步通知机制，超时 30 秒自动查询
  4. 对账功能每日凌晨 2 点执行
  
  需要我查看更详细的设计吗？
```

**场景2：数据库管理**

```
你: 在"项目跟踪"数据库里添加一个新任务：
    名称：优化首页性能，负责人：张三，优先级：高，截止日期：下周五

Hermes: 已添加到 Notion 数据库：
  页面: 优化首页性能
  数据库: 项目跟踪
  负责人: 张三
  优先级: 高
  截止日期: 2024-01-12
```

**场景3：会议纪要整理**

```
你: 把今天的会议纪要整理成结构化文档，存到 Notion
    [粘贴会议录音转文字]

Hermes: 正在整理...
Hermes: 已创建 Notion 页面"2024-01-05 产品周会纪要"，包含：
  - 参会人员
  - 核心结论（5 条）
  - 待办事项（8 项，已分配负责人）
  - 下次会议议题
```

---

## 6. 实战：接入更多服务

### 6.1 Linear（项目管理）

Linear 是海外开发者喜爱的项目管理工具，比 Jira 更轻量、更美观。

```yaml
mcp_servers:
  linear:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-linear"]
    env:
      LINEAR_API_KEY: "${LINEAR_API_KEY}"
    allowed_tools:
      - "linear_search_issues"
      - "linear_create_issue"
      - "linear_update_issue"
      - "linear_add_comment"
```

**获取 API Key：**
1. Linear → Settings → API → Personal API keys
2. 点击 "Create key"
3. 复制 `lin_api_xxxxxxxx`

**使用示例：**

```
你: 创建一个 Linear Issue，标题"修复登录页面样式"，
    分配给李明，标签是 bug 和 frontend

Hermes: ✅ Linear Issue 已创建
  标题: 修复登录页面样式
  状态: Todo
  负责人: 李明
  标签: bug, frontend
  链接: https://linear.app/company/issue/PROJ-123
```

### 6.2 Figma（设计协作）

Figma MCP Server 让 AI 能够读取设计稿信息，帮助工程师理解设计规范。

```yaml
mcp_servers:
  figma:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-figma"]
    env:
      FIGMA_ACCESS_TOKEN: "${FIGMA_TOKEN}"
    allowed_tools:
      - "get_file"
      - "get_file_nodes"
      - "get_comments"
```

**获取 Access Token：**
1. Figma → Settings → Personal access tokens
2. 点击 "Create new token"
3. 复制 Token

**使用示例：**

```
你: 查看 Figma 文件 abc123 中"登录页面"的设计规范

Hermes: 登录页面设计规范：
  - 画布尺寸: 375 x 812 (iPhone)
  - 主色调: #1A73E8
  - 按钮圆角: 8px
  - 输入框高度: 48px
  - 间距系统: 4px 基准
  
  需要我导出具体组件的 CSS 代码吗？
```

### 6.3 Slack（团队沟通）

```yaml
mcp_servers:
  slack:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-slack"]
    env:
      SLACK_BOT_TOKEN: "${SLACK_BOT_TOKEN}"
      SLACK_TEAM_ID: "${SLACK_TEAM_ID}"
    allowed_tools:
      - "slack_search_messages"
      - "slack_send_message"
      - "slack_get_channel_history"
```

**获取 Bot Token：**
1. https://api.slack.com/apps → Create New App
2. OAuth & Permissions → Bot Token Scopes
3. 添加 `chat:write`, `search:read`
4. Install to Workspace
5. 复制 "Bot User OAuth Token"（格式：`xoxb-xxx`）

> **注意**
> Slack 的 `search:read` 权限需要工作区管理员批准。如果你的 Bot 只能发消息不能搜索，检查权限是否已审批。

### 6.4 Google Calendar（日程管理）

```yaml
mcp_servers:
  google-calendar:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-gcalendar"]
    env:
      GOOGLE_CLIENT_ID: "${GOOGLE_CLIENT_ID}"
      GOOGLE_CLIENT_SECRET: "${GOOGLE_CLIENT_SECRET}"
      GOOGLE_REFRESH_TOKEN: "${GOOGLE_REFRESH_TOKEN}"
    allowed_tools:
      - "list_events"
      - "create_event"
      - "delete_event"
      - "find_free_time"
```

**OAuth 配置流程：**
1. Google Cloud Console → APIs & Services → Credentials
2. 创建 OAuth 2.0 Client ID（Desktop App 类型）
3. 启用 Google Calendar API
4. 用 OAuth 流程获取 Refresh Token（Server 首次启动时会引导你完成授权）

**使用示例：**

```
你: 帮我看看下周有哪些会议

Hermes: 下周会议安排：
  周一 10:00 - 11:00: 产品周会
  周二 14:00 - 15:30: 技术评审
  周三 09:00 - 10:00: 客户沟通
  周四: 无会议 ✨
  周五 16:00 - 17:00: 团队复盘

需要我帮你在周四安排一个专注工作的时间段吗？
```

### 6.5 Google Drive（文件存储）

```yaml
mcp_servers:
  google-drive:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-gdrive"]
    env:
      GOOGLE_CLIENT_ID: "${GOOGLE_CLIENT_ID}"
      GOOGLE_CLIENT_SECRET: "${GOOGLE_CLIENT_SECRET}"
      GOOGLE_REFRESH_TOKEN: "${GOOGLE_REFRESH_TOKEN}"
    allowed_tools:
      - "search_files"
      - "read_file"
      - "list_folder"
```

### 6.6 PostgreSQL/MySQL（数据库）

数据库 MCP Server 让 AI 能直接查询数据库，是数据分析师的利器。

**PostgreSQL：**

```yaml
mcp_servers:
  postgres:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-postgres"]
    env:
      POSTGRES_URL: "${DATABASE_URL}"
    allowed_tools:
      - "query"
```

**数据库连接字符串格式：**

```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/dbname"
```

> **注意**
> **数据库 MCP Server 是高风险工具！** 建议：
> 1. 使用只读账号（`GRANT SELECT ON ALL TABLES`）
> 2. 开启 `allowed_tools: ["query"]` 但不要给 `execute` 权限
> 3. 生产环境数据库强烈建议通过只读副本（Read Replica）连接
> 4. 避免直接连接含有敏感信息（用户密码、支付信息）的数据库

**使用示例：**

```
你: 查询最近 7 天的新用户注册数量，按天分组

Hermes: 正在查询数据库...

查询结果：
  日期          新注册用户数
  2024-01-01    156
  2024-01-02    203
  2024-01-03    189
  2024-01-04    245
  2024-01-05    198
  2024-01-06    312
  2024-01-07    267
  
  周总计: 1,570 人
  日均: 224 人
  环比增长: +15.3%
```

---

## 7. 6000+ MCP 服务生态

### 7.1 按分类浏览

MCP 生态正在爆发式增长。截至 2024 年底，社区已经有了超过 6000 个 MCP Server，覆盖几乎所有主流 SaaS 服务。

**主要分类：**

| 分类 | 代表服务 | 数量 |
|------|---------|------|
| 开发工具 | GitHub, GitLab, Bitbucket, Vercel | 800+ |
| 生产力 | Notion, Obsidian, Todoist, Trello | 600+ |
| 通讯协作 | Slack, Discord, Teams, Zoom | 500+ |
| 云服务 | AWS, GCP, Azure, Cloudflare | 700+ |
| 数据库 | PostgreSQL, MySQL, MongoDB, Redis | 400+ |
| 数据分析 | BigQuery, Snowflake, Databricks | 300+ |
| 设计创意 | Figma, Canva, Adobe | 200+ |
| 金融商务 | Stripe, PayPal, QuickBooks | 250+ |
| 智能家居 | Home Assistant, Philips Hue | 150+ |
| 其他 | 各种小众工具和企业内部系统 | 2000+ |

### 7.2 热门 Top 20

根据社区使用量排序的 Top 20 MCP Server：

1. **@modelcontextprotocol/server-github** - GitHub 官方 MCP Server
2. **@modelcontextprotocol/server-filesystem** - 本地文件系统访问
3. **@modelcontextprotocol/server-postgres** - PostgreSQL 查询
4. **@modelcontextprotocol/server-notion** - Notion 文档管理
5. **@modelcontextprotocol/server-slack** - Slack 消息收发
6. **@modelcontextprotocol/server-google-maps** - Google Maps 地点搜索
7. **@modelcontextprotocol/server-puppeteer** - 网页浏览和截图
8. **@modelcontextprotocol/server-fetch** - 通用 HTTP 请求
9. **@modelcontextprotocol/server-sqlite** - SQLite 数据库
10. **@modelcontextprotocol/server-brave-search** - Brave 搜索引擎
11. **@modelcontextprotocol/server-memory** - 持久化记忆存储
12. **@modelcontextprotocol/server-sequential-thinking** - 链式思考辅助
13. **@anthropic-ai/server-shopify** - Shopify 电商管理
14. **@modelcontextprotocol/server-aws-kb-retrieval** - AWS 知识库检索
15. **@modelcontextprotocol/server-everart** - AI 图像生成
16. **@modelcontextprotocol/server-duckduckgo** - DuckDuckGo 搜索
17. **@modelcontextprotocol/server-redis** - Redis 缓存操作
18. **@modelcontextprotocol/server-github-advanced** - GitHub 高级功能
19. **@modelcontextprotocol/server-discord** - Discord 深度集成
20. **@modelcontextprotocol/server-youtube** - YouTube 视频分析

> **Tips**
> 安装任何 MCP Server 都可以用 `npx` 一键启动，不需要手动下载：
> ```yaml
> mcp_servers:
>   any-server:
>     command: "npx"
>     args: ["-y", "@scope/server-name"]
> ```

### 7.3 安全评估

使用第三方 MCP Server 时，安全评估必不可少：

**检查清单：**

```
□ 来源可信
  - 是否来自官方账号（@modelcontextprotocol、@anthropic-ai）？
  - 社区使用量大吗？GitHub stars 有多少？
  - 最近还有更新吗？

□ 权限合理
  - Server 请求的权限是否与其功能匹配？
  - 文件系统 Server 是否限制了访问目录？

□ 代码审查
  - 如果可能，快速浏览一下源码
  - 特别关注它如何处理你的 Token/凭证
  - 是否有可疑的网络请求？

□ 网络隔离
  - 能否在沙箱/容器中运行？
  - 能否限制其网络访问权限？

□ 最小权限
  - 用 allowed_tools 限制可调用的工具
  - 给 API Token 设置最小权限
```

> **注意**
> MCP Server 运行在本地时，理论上它可以访问你的文件系统、环境变量、网络。安装来路不明的 Server 就像安装来路不明的软件一样有风险。建议只使用官方或社区广泛验证的 Server。

---

## 8. Cron 定时任务系统

如果说 MCP 让 Hermes 有了"手"（操作外部工具的能力），那 Cron 定时任务系统就是给了 Hermes "生物钟"——让它能按时自动执行任务。

### 8.1 ~/.hermes/cron/tasks.yaml 配置详解

Hermes 的定时任务配置文件位于 `~/.hermes/cron/tasks.yaml`：

```yaml
# ~/.hermes/cron/tasks.yaml

# 全局配置
global:
  # 时区设置
  timezone: "Asia/Shanghai"
  # 任务并发数
  max_concurrent: 3
  # 默认超时时间
  default_timeout: 300
  # 失败重试次数
  default_retries: 2
  # 通知渠道（任务完成/失败时通知你）
  notifications:
    on_success: false      # 成功时不通知（避免打扰）
    on_failure: true       # 失败时通知
    channels:
      - platform: "telegram"
        user_id: "12345678"

# 任务列表
tasks:
  # 任务1：每日新闻摘要
  - id: "daily-news"
    name: "每日 AI 新闻摘要"
    # Cron 表达式：每天早上 8 点执行
    schedule: "0 8 * * *"
    enabled: true
    # 执行内容
    actions:
      - type: "prompt"
        content: |
          搜索今天的人工智能领域重要新闻，
          整理成 5 条要点，每条包含标题和一句话摘要。
          用中文输出。
      - type: "notify"
        platform: "telegram"
        user_id: "12345678"
        message_template: "📰 今日 AI 新闻\n\n{{result}}"

  # 任务2：每周报告生成
  - id: "weekly-report"
    name: "每周数据报告"
    schedule: "0 9 * * MON"
    enabled: true
    actions:
      - type: "mcp"
        server: "postgres"
        tool: "query"
        arguments:
          sql: |
            SELECT 
              DATE(created_at) as date,
              COUNT(*) as new_users
            FROM users
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY date;
      - type: "prompt"
        content: |
          根据以下数据生成周报摘要：
          {{previous_result}}
          
          要求：
          1. 总结本周关键数据
          2. 指出趋势和异常
          3. 给出下周建议
      - type: "notify"
        platform: "lark"
        user_id: "ou_xxxxxxxx"

  # 任务3：网站监控
  - id: "website-monitor"
    name: "网站可用性监控"
    # 每 5 分钟执行一次
    schedule: "*/5 * * * *"
    enabled: true
    timeout: 30
    actions:
      - type: "http"
        method: "GET"
        url: "https://myapp.com/health"
        expected_status: 200
      - type: "condition"
        if: "{{status}} != 200"
        then:
          - type: "notify"
            platform: "telegram"
            user_id: "12345678"
            message_template: "🚨 网站异常！状态码: {{status}}"
```

### 8.2 Cron 表达式语法（详细带示例）

Cron 表达式是定时任务的"时间表语言"。它由 5 个字段组成：

```
┌───────────── 分钟 (0 - 59)
│ ┌───────────── 小时 (0 - 23)
│ │ ┌───────────── 日期 (1 - 31)
│ │ │ ┌───────────── 月份 (1 - 12)
│ │ │ │ ┌───────────── 星期 (0 - 6, 0=周日)
│ │ │ │ │
* * * * *
```

**常用表达式示例：**

| 表达式 | 含义 | 说明 |
|--------|------|------|
| `0 8 * * *` | 每天 8:00 | 每天早上准时执行 |
| `0 */2 * * *` | 每 2 小时 | 在 0:00, 2:00, 4:00...执行 |
| `*/15 * * * *` | 每 15 分钟 | 常用于监控类任务 |
| `0 9 * * MON` | 每周一 9:00 | 周报、周会的最佳时间 |
| `0 9 1 * *` | 每月 1 号 9:00 | 月报、账单提醒 |
| `0 22 * * 1-5` | 工作日 22:00 | 工作日晚间执行 |
| `0 0 * * 0` | 每周日 0:00 | 周日凌晨维护窗口 |
| `0 12 1,15 * *` | 每月 1 号和 15 号 12:00 | 半月度任务 |
| `0 8-18 * * *` | 每天 8:00-18:00 每小时 | 工作时间监控 |
| `@daily` | 每天 0:00 | 简写形式 |
| `@weekly` | 每周日 0:00 | 简写形式 |
| `@hourly` | 每小时 0 分 | 简写形式 |

**特殊字符说明：**

```
*  ：任意值（每分钟/每小时/每天）
,  ：列表（1,15 表示 1 和 15）
-  ：范围（1-5 表示 1 到 5）
/  ：步长（*/5 表示每 5 个单位）
```

> **Tips**
> 如果你记不住 Cron 语法，可以使用在线工具辅助：
> - https://crontab.guru/ - 输入表达式，它用自然语言解释含义
> - https://crontab-generator.org/ - 勾选时间条件，自动生成表达式

### 8.3 定时任务模板

#### 模板1：每日新闻摘要

```yaml
- id: "news-digest"
  name: "每日行业新闻"
  schedule: "0 8 * * *"
  enabled: true
  actions:
    - type: "prompt"
      content: |
        搜索今天 {{date}} 的 {{industry}} 行业重要新闻。
        整理成 3-5 条要点，每条包含：
        - 标题（加粗）
        - 一句话摘要
        - 来源链接
        
        用中文输出，格式清晰易读。
    - type: "notify"
      platform: "telegram"
      user_id: "12345678"
      message_template: |
        📰 {{date}} 行业新闻
        
        {{result}}
```

#### 模板2：每日/周/月报告

```yaml
- id: "daily-report"
  name: "每日数据简报"
  schedule: "0 9 * * *"
  actions:
    - type: "mcp"
      server: "postgres"
      tool: "query"
      arguments:
        sql: |
          SELECT 
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE) as today,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - 1) as yesterday
          FROM orders;
    - type: "prompt"
      content: |
        基于以下数据生成今日简报：
        {{previous_result}}
        
        格式要求：
        📊 今日数据简报 ({{date}})
        
        订单数: X 单（环比昨日 ±X%）
        ...
    - type: "notify"
      platform: "lark"
```

#### 模板3：系统监控告警

```yaml
- id: "health-check"
  name: "服务健康检查"
  schedule: "*/5 * * * *"
  timeout: 10
  actions:
    - type: "http"
      method: "GET"
      url: "https://api.myapp.com/health"
    - type: "condition"
      if: "{{status}} != 200 or {{response_time}} > 2000"
      then:
        - type: "notify"
          platform: "telegram"
          message_template: |
            🚨 服务异常告警
            
            时间: {{timestamp}}
            状态码: {{status}}
            响应时间: {{response_time}}ms
            
            请立即检查！
```

#### 模板4：社交媒体内容发布

```yaml
- id: "social-post"
  name: "定时发布内容"
  schedule: "0 10,15 * * *"
  actions:
    - type: "prompt"
      content: |
        生成一条关于 {{topic}} 的社交媒体帖子。
        平台: 微信公众号
        风格: 专业但亲切
        字数: 300-500 字
        包含一个相关话题标签。
    - type: "notify"
      platform: "telegram"
      message_template: |
        📝 待发布内容：
        
        {{result}}
        
        请审核后手动发布。
```

#### 模板5：竞品监控

```yaml
- id: "competitor-monitor"
  name: "竞品动态监控"
  schedule: "0 9 * * *"
  actions:
    - type: "prompt"
      content: |
        搜索 {{competitor}} 最近 24 小时的动态：
        1. 新产品/功能发布
        2. 官方博客更新
        3. 社交媒体重要发文
        4. 融资/合作新闻
        
        整理成简报，标记需要关注的重要信息。
    - type: "notify"
      platform: "lark"
```

### 8.4 hermes cron 命令详解

```bash
# 查看 cron 帮助
$ hermes cron --help

Usage: hermes cron [OPTIONS] COMMAND [ARGS]...

  管理定时任务

Commands:
  list       列出所有任务
  run        手动执行一个任务
  enable     启用任务
  disable    禁用任务
  logs       查看任务执行日志
  validate   验证配置文件语法
```

**常用命令：**

```bash
# 列出所有任务
$ hermes cron list

输出示例：
ID              NAME                SCHEDULE        STATUS    LAST_RUN
─────────────────────────────────────────────────────────────────────
daily-news      每日 AI 新闻摘要     0 8 * * *       ✓ 启用    2小时前
weekly-report   每周数据报告         0 9 * * MON     ✓ 启用    3天前
website-monitor 网站可用性监控        */5 * * * *     ✓ 启用    5分钟前

# 手动执行一个任务（调试用）
$ hermes cron run daily-news

# 启用/禁用任务
$ hermes cron enable daily-news
$ hermes cron disable weekly-report

# 查看任务日志
$ hermes cron logs daily-news --tail 20

# 验证配置文件语法
$ hermes cron validate

# 实时监控任务执行
$ hermes cron logs --follow
```

### 8.5 调试技巧

定时任务出问题时，按以下步骤排查：

**步骤1：验证配置语法**

```bash
$ hermes cron validate

✅ 配置文件语法正确
  任务数: 5
  启用: 4, 禁用: 1
  警告: 
    - 任务 "backup-db" 没有设置超时时间，将使用默认值 300 秒
```

**步骤2：手动执行任务**

```bash
$ hermes cron run daily-news --verbose

🔄 手动执行任务: daily-news
────────────────────────────────────
步骤1: prompt - 执行中...
✓ 步骤1完成 (耗时 3.2s)
步骤2: notify - 执行中...
✓ 步骤2完成 (耗时 0.5s)
────────────────────────────────────
任务完成，总计耗时 3.7s
```

**步骤3：检查日志**

```bash
# 查看最近失败的执行
$ hermes cron logs --status failed --last 24h

# 查看特定任务的详细日志
$ hermes cron logs website-monitor --tail 50
```

**常见问题：**

| 问题 | 原因 | 解决 |
|------|------|------|
| 任务没有按时执行 | Cron 服务未启动 | `hermes cron start` |
| 执行了但没有收到通知 | 通知配置错误 | 检查 platform 和 user_id |
| MCP 查询超时 | 数据库连接慢 | 增加 timeout 配置 |
| 任务执行成功但结果不对 | Prompt 不够明确 | 优化 prompt 内容 |

> **Tips**
> 开发新任务时，建议先用 `hermes cron run <task-id> --verbose` 手动执行几次，确认输出正确后再等待定时触发。这能节省大量等待时间。

---

## 9. 多 Agent 编排

### 9.1 delegate_task 机制

Hermes 支持一个强大的功能：**多 Agent 编排**。你可以把复杂任务拆解成子任务，分配给多个专门的 Agent 并行处理。

这就像一个项目经理（主 Agent）把大项目拆成多个模块，分配给不同的专家（子 Agent）同时开工，最后汇总结果。

```yaml
# 在任务配置中使用 delegate_task
- id: "complex-analysis"
  name: "复杂投研分析"
  actions:
    - type: "delegate"
      # 最多 3 个子 Agent 并行
      max_workers: 3
      tasks:
        - id: "market-research"
          name: "市场调研"
          prompt: |
            分析 {{company}} 所在行业的市场规模、增长趋势、
            竞争格局。重点关注最近一年的变化。
            
        - id: "financial-analysis"
          name: "财务分析"
          prompt: |
            分析 {{company}} 的财务报表：
            - 营收和利润趋势
            - 现金流状况
            - 关键财务比率
            
        - id: "tech-assessment"
          name: "技术评估"
          prompt: |
            评估 {{company}} 的技术实力：
            - 核心技术和专利
            - 技术团队规模和质量
            - 技术护城河
      
      # 汇总结果
      merge_prompt: |
        将以下三个维度的分析结果整合成一份完整的投研报告：
        
        ## 市场调研
        {{market-research.result}}
        
        ## 财务分析
        {{financial-analysis.result}}
        
        ## 技术评估
        {{tech-assessment.result}}
        
        要求：
        1. 给出综合评分（1-10）
        2. 指出关键风险点
        3. 给出投资建议
```

### 9.2 最多 3 子 Agent 并行

Hermes 目前最多支持 **3 个子 Agent 并行**。这个限制不是技术问题，而是有意设计的：

1. **成本控制**：每个子 Agent 都消耗 API Token，并行太多会迅速耗尽预算
2. **质量保障**：并行任务过多，主 Agent 整合结果时会遗漏关键信息
3. **可调试性**：3 个并行任务是最容易追踪和排错的规模

如果你的任务需要更多并行度，建议分层编排：

```
第一层：拆成 3 个大模块
  ├─ 模块A → 第二层：再拆 3 个子任务
  ├─ 模块B → 第二层：再拆 3 个子任务
  └─ 模块C → 第二层：再拆 3 个子任务
```

> **注意**
> 多层嵌套的 delegate 会增加总耗时和成本。建议只在确实需要并行处理时才使用，简单任务直接用顺序执行即可。

### 9.3 实战案例：投研/内容/代码审查流水线

#### 案例1：AI 投研流水线

```yaml
- id: "investment-research"
  name: "AI 投研报告生成"
  schedule: "0 7 * * MON"
  actions:
    - type: "delegate"
      max_workers: 3
      tasks:
        - id: "collect-data"
          name: "数据收集"
          prompt: |
            收集 {{target_company}} 的最新公开信息：
            1. 搜索最近一周的新闻
            2. 查找最新财报数据
            3. 收集行业研报摘要
            
        - id: "sentiment-analysis"
          name: "舆情分析"
          prompt: |
            分析 {{target_company}} 的市场情绪：
            1. 社交媒体讨论热度
            2. 分析师评级变化
            3. 投资者情绪指标
            
        - id: "peer-comparison"
          name: "同业对比"
          prompt: |
            将 {{target_company}} 与主要竞品对比：
            1. 市值和估值对比
            2. 营收增速对比
            3. 技术实力对比
            
      merge_prompt: |
        基于收集的数据、舆情分析和同业对比，
        生成一份专业的投研报告，包含：
        - 执行摘要
        - 核心数据
        - 风险评估
        - 投资建议
        
    - type: "notify"
      platform: "lark"
      message_template: |
        📊 投研报告已生成
        
        标的: {{target_company}}
        生成时间: {{timestamp}}
        
        {{result}}
```

#### 案例2：内容工厂流水线

```yaml
- id: "content-factory"
  name: "自动化内容生产"
  actions:
    - type: "delegate"
      max_workers: 3
      tasks:
        - id: "topic-research"
          name: "选题研究"
          prompt: |
            基于热点事件 {{event}}，
            生成 5 个适合社交媒体传播的内容选题。
            每个选题包含：标题角度、目标平台、预期效果。
            
        - id: "content-draft"
          name: "内容起草"
          prompt: |
            为选题 "{{topic}}" 撰写完整内容：
            - 微信公众号版本（800 字）
            - 小红书版本（300 字+表情）
            - Twitter 版本（280 字）
            
        - id: "visual-design"
          name: "配图建议"
          prompt: |
            为内容 "{{topic}}" 设计配图方案：
            - 主视觉描述（供设计师参考）
            - 信息图数据点
            - 配色建议
            
      merge_prompt: |
        整合选题、内容和配图方案，
        输出完整的内容发布计划表。
```

#### 案例3：代码审查流水线

```yaml
- id: "code-review-pipeline"
  name: "自动化代码审查"
  # 监听 GitHub Webhook，PR 创建时触发
  trigger:
    type: "webhook"
    source: "github"
    event: "pull_request.opened"
  actions:
    - type: "delegate"
      max_workers: 3
      tasks:
        - id: "security-check"
          name: "安全检查"
          prompt: |
            审查 PR {{pr_url}} 的安全问题：
            - SQL 注入风险
            - XSS 漏洞
            - 敏感信息泄露
            - 依赖包漏洞
            
        - id: "quality-check"
          name: "代码质量"
          prompt: |
            审查 PR {{pr_url}} 的代码质量：
            - 代码复杂度
            - 测试覆盖率
            - 代码风格一致性
            - 设计模式使用
            
        - id: "logic-check"
          name: "业务逻辑"
          prompt: |
            审查 PR {{pr_url}} 的业务逻辑：
            - 需求实现是否完整
            - 边界条件处理
            - 异常处理
            - 性能影响
            
      merge_prompt: |
        整合三方审查意见，生成完整的代码审查报告。
        按严重程度分类，给出明确的修改建议。
        
    - type: "mcp"
      server: "github"
      tool: "add_issue_comment"
      arguments:
        repo: "{{repo}}"
        issue_number: "{{pr_number}}"
        body: "{{result}}"
```

---

## 10. 自动化流水线设计

### 10.1 MCP + Cron + 多 Agent 组合

真正的自动化威力来自于把 MCP、Cron 和多 Agent 编排组合在一起。这三个组件的关系就像乐高积木：

- **MCP** = 积木块（能做什么）
- **Cron** = 定时器（什么时候做）
- **多 Agent** = 分工协作（怎么做最高效）

### 10.2 全自动 AI 投研流水线示例

让我们设计一个完整的、全自动的投研流水线：

```yaml
# ~/.hermes/cron/tasks.yaml

- id: "auto-research-pipeline"
  name: "全自动投研流水线"
  # 每天开盘前执行
  schedule: "0 8 * * MON-FRI"
  enabled: true
  timeout: 600
  actions:
    # 步骤1：并行数据收集（3 个子 Agent）
    - type: "delegate"
      max_workers: 3
      tasks:
        - id: "market-data"
          name: "市场数据"
          prompt: |
            获取今日市场数据：
            - 大盘指数（上证、深证、创业板）
            - 北向资金流向
            - 涨跌停家数
            - 板块涨跌排名
            
        - id: "news-scan"
          name: "新闻扫描"
          prompt: |
            扫描今日重要财经新闻：
            - 政策面消息
            - 行业动态
            - 个股公告
            - 国际市场影响
            
        - id: "technical-analysis"
          name: "技术面"
          prompt: |
            分析自选股的技术面：
            - K线形态
            - 均线系统
            - MACD/KDJ 指标
            - 支撑压力位
      
      merge_prompt: |
        将市场数据、新闻扫描和技术面分析汇总，
        生成早盘简报。
    
    # 步骤2：保存到 Notion
    - type: "mcp"
      server: "notion"
      tool: "notion_append_block_children"
      arguments:
        page_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        children:
          - type: "heading_2"
            text: "{{date}} 早盘简报"
          - type: "paragraph"
            text: "{{previous_result}}"
    
    # 步骤3：发送到飞书群
    - type: "notify"
      platform: "lark"
      channel: "投研群"
      message_template: |
        📊 {{date}} 早盘简报已生成
        
        已保存至 Notion 知识库。
        重点关注的板块：{{highlight_sectors}}
        
        点击查看详情
```

### 10.3 全自动内容工厂示例

```yaml
- id: "content-factory-pipeline"
  name: "全自动内容工厂"
  schedule: "0 6 * * *"
  actions:
    # 步骤1：确定今日选题
    - type: "prompt"
      content: |
        基于今天的日期 {{date}} 和热点事件，
        为科技自媒体账号确定 3 个内容选题。
        要求：
        - 与 AI/科技相关
        - 有话题性和传播潜力
        - 适合公众号+小红书双平台发布
    
    # 步骤2：为每个选题并行生产内容
    - type: "delegate"
      max_workers: 3
      tasks:
        - id: "content-1"
          name: "选题1内容"
          prompt: |
            为选题 "{{topics[0]}}" 撰写：
            1. 公众号文章（1000 字，专业深度）
            2. 小红书笔记（300 字，轻松活泼）
            3. 配图描述（3 张图）
            
        - id: "content-2"
          name: "选题2内容"
          prompt: |
            为选题 "{{topics[1]}}" 撰写：
            1. 公众号文章
            2. 小红书笔记
            3. 配图描述
            
        - id: "content-3"
          name: "选题3内容"
          prompt: |
            为选题 "{{topics[2]}}" 撰写：
            1. 公众号文章
            2. 小红书笔记
            3. 配图描述
      
      merge_prompt: |
        整理三份内容的生产计划：
        - 发布时间表
        - 内容要点
        - 配图需求清单
    
    # 步骤3：保存到 Notion 发布日历
    - type: "mcp"
      server: "notion"
      tool: "notion_create_database_item"
      arguments:
        database_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        properties:
          标题: "{{date}} 内容计划"
          状态: "待审核"
          内容: "{{result}}"
    
    # 步骤4：通知审核
    - type: "notify"
      platform: "telegram"
      message_template: |
        📝 今日内容已生成，请审核
        
        已保存至 Notion 发布日历。
        共 3 篇内容待审核。
```

### 10.4 错误处理与告警

自动化流水线必须具备健壮的错误处理能力：

```yaml
- id: "reliable-pipeline"
  name: "带容错的流水线"
  actions:
    - type: "try"
      try:
        - type: "mcp"
          server: "github"
          tool: "search_issues"
          arguments:
            repo: "mycompany/project"
            query: "is:open label:bug"
      catch:
        - type: "notify"
          platform: "telegram"
          message_template: |
            ⚠️ 任务步骤失败
            任务: {{task_id}}
            步骤: GitHub 查询
            错误: {{error}}
            
            已跳过此步骤，继续执行后续任务。
    
    - type: "prompt"
      content: |
        基于获取的数据生成报告。
        如果数据为空，请说明"今日无新增 Bug"。
    
    # 最终通知，无论成功失败都发送
    - type: "notify"
      platform: "lark"
      message_template: |
        任务 {{task_id}} 执行完成
        状态: {{status}}
        
        {{#if error}}
        异常信息: {{error}}
        {{/if}}
```

**告警升级策略：**

```yaml
global:
  notifications:
    on_failure: true
    escalation:
      # 第一次失败：立即通知
      - after: 0
        channels:
          - platform: "telegram"
            user_id: "12345678"
      
      # 连续失败 3 次：升级告警
      - after: 3
        channels:
          - platform: "lark"
            user_id: "ou_xxxxxxxx"
      
      # 连续失败 5 次：电话/短信告警
      - after: 5
        channels:
          - platform: "sms"
            phone: "+86138xxxxxxxx"
```

---

## 11. 安全与合规

### 11.1 权限最小化

自动化系统的安全基石是**最小权限原则**（Principle of Least Privilege）。

**Token 权限控制：**

```yaml
# GitHub：使用 Fine-grained Token，限定只读特定仓库
mcp_servers:
  github-readonly:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_READONLY_TOKEN}"
    allowed_tools:
      - "search_repositories"
      - "get_file_contents"
      # 禁止所有写操作！

# 数据库：使用只读账号
mcp_servers:
  postgres:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-postgres"]
    env:
      # 这个 URL 连接的是只读副本，账号只有 SELECT 权限
      POSTGRES_URL: "${DATABASE_READONLY_URL}"
```

**分层权限设计：**

```
┌─────────────────────────────────────────┐
│  生产环境（Production）                  │
│  - 只读数据库连接                        │
│  - 只读 GitHub Token                     │
│  - 禁止发送消息/邮件                     │
└─────────────────────────────────────────┘
                    ▲
┌─────────────────────────────────────────┐
│   staging 环境                          │
│  - 读写测试数据库                        │
│  - 可创建 Issue/PR（测试仓库）            │
│  - 可发送到测试群组                      │
└─────────────────────────────────────────┘
                    ▲
┌─────────────────────────────────────────┐
│  开发环境（Development）                 │
│  - 完全权限（本地数据库）                 │
│  - 完整 GitHub Token（个人仓库）          │
│  - 可发送到个人账号                       │
└─────────────────────────────────────────┘
```

### 11.2 敏感数据处理

自动化任务经常需要处理敏感数据。Hermes 提供多层保护：

**环境变量隔离：**

```bash
# 敏感信息只通过环境变量传入，不写入配置文件
export GITHUB_TOKEN="ghp_xxx"
export DATABASE_PASSWORD="secret"
export SLACK_BOT_TOKEN="xoxb-xxx"
```

**日志脱敏：**

```yaml
global:
  security:
    # 日志中自动脱敏的模式
    log_redaction:
      - pattern: "ghp_[a-zA-Z0-9]{36}"
        replacement: "[GITHUB_TOKEN]"
      - pattern: "xoxb-[a-zA-Z0-9-]{10,}"
        replacement: "[SLACK_TOKEN]"
      - pattern: "password[=:]\s*\S+"
        replacement: "password=[REDACTED]"
```

**数据访问审计：**

```yaml
global:
  audit:
    enabled: true
    log_file: "~/.hermes/logs/audit.log"
    # 记录所有 MCP 工具调用
    log_mcp_calls: true
    # 记录所有数据库查询
    log_database_queries: true
```

### 11.3 Rate Limit 与成本控制

自动化任务如果不加限制，可能在短时间内产生大量 API 调用，导致：
1. 触发平台的 Rate Limit
2. 产生意想不到的账单

**Rate Limit 配置：**

```yaml
global:
  rate_limit:
    # 每个 MCP Server 的调用频率限制
    mcp:
      github:
        requests_per_minute: 30
        requests_per_hour: 500
      notion:
        requests_per_minute: 20
      openai:
        requests_per_minute: 60
    
    # 全局预算控制
    budget:
      daily_max_tokens: 1000000    # 每日最大 Token 数
      daily_max_cost_usd: 50       # 每日最大花费（美元）
      alert_threshold: 80          # 达到 80% 时告警
```

**成本监控：**

```bash
# 查看今日 API 使用情况
$ hermes stats --today

今日 API 使用情况
─────────────────────────────────
OpenAI API:
  请求数: 1,234
  Token 数: 456,789
  预估费用: $2.34

GitHub API:
  请求数: 567
  剩余额度: 4,433/5000

总计费用: $2.34
预算使用: 4.7%
```

### 11.4 审计日志

完整的审计日志是合规和排错的必需品：

```yaml
global:
  audit:
    enabled: true
    # 审计日志存储
    storage:
      type: "file"           # file, database, remote
      path: "~/.hermes/audit/"
      retention_days: 90     # 保留 90 天
    
    # 审计事件类型
    events:
      - "mcp.tool_called"           # MCP 工具调用
      - "mcp.server_connected"      # MCP Server 连接
      - "cron.task_executed"        # 定时任务执行
      - "cron.task_failed"          # 定时任务失败
      - "gateway.message_received"  # 收到用户消息
      - "config.changed"            # 配置变更
    
    # 审计日志格式
    format:
      include_timestamp: true
      include_user_id: true
      include_ip: false
      include_full_prompt: false    # 不包含完整 prompt（隐私）
```

审计日志示例：

```json
{
  "timestamp": "2024-01-15T08:00:00+08:00",
  "event": "mcp.tool_called",
  "level": "info",
  "user_id": "zhangsan",
  "details": {
    "server": "github",
    "tool": "create_issue",
    "arguments": {
      "repo": "mycompany/project",
      "title": "[REDACTED]"
    },
    "result": "success",
    "duration_ms": 1234
  }
}
```

> **本章小结（第十一册）**
> 在本章中，我们深入学习了 Hermes 的自动化能力：
> - 理解了 MCP 协议的设计理念、架构和通信机制
> - 掌握了 Hermes 中 MCP 的配置方法，包括 stdio 和 HTTP 两种模式
> - 完成了 GitHub、Notion、Linear、Figma、Slack、Google Calendar、数据库等服务的实战接入
> - 了解了 6000+ MCP 服务生态的全貌和安全评估方法
> - 学会了 Cron 定时任务系统的配置和常用模板
> - 掌握了多 Agent 编排和自动化流水线的设计方法
> - 建立了权限最小化、敏感数据保护、Rate Limit 和审计日志的安全体系
>
> 现在，你的 Hermes 已经从一个"对话式 AI"进化为一个真正的"自动化 Agent"——它能接入外部世界、按时自动执行任务、多个 Agent 协同工作、并且安全可控。这才是 AI Agent 的完整形态。

---

> **作者：鲲鹏Talk**
> 微信视频号 | B站 | 微信公众号 | YouTube | 小红书 | 抖音
> 搜索「鲲鹏Talk」即可找到我，欢迎关注交流！
