---
name: verify-chain
description: 验证链 — 角色对抗式技术文章交叉验证。写完IT文章后，Critic 提取关键断言并生成核查问题，多个 Verifier SubAgent 独立上下文联网验证，Repairer 自动修复。用于规避 AI 幻觉、知识过时、信息遗漏。
---

# 验证链（Verify Chain）

## 触发条件

当用户明确表示以下意图时调用此技能：
- "验证这篇文章"、"核查文章内容"、"check 文章"、"verify article"
- "检查有没有错误"、"帮我审稿"
- 写完一篇 IT 技术文章后主动询问是否需要验证
- 用户提到 `/verify` 或 `/验证链`

## 适用场景

- **服务端开发**：C/C++、Rust、Go、Java、Python、Node.js 等后端服务、Web 框架、微服务、中间件、网络编程
- **桌面/客户端开发**：Qt、Win32/WinUI、Electron、跨平台 GUI 应用
- **嵌入式与物联网**：RTOS（FreeRTOS、Zephyr、RT-Thread 等）、驱动开发、BSP/硬件抽象层、MCU/DSP 编程
- **图形学与渲染**：OpenGL/Vulkan/DirectX、Shader 开发、游戏引擎、渲染管线与性能优化
- **系统与底层**：操作系统原理、Linux 内核、网络协议（TCP/IP、HTTP/2、gRPC）、并发模型、性能剖析
- **三方库与生态**：开源库使用与二次开发（fmt、Boost、tokio、serde、Lombok 等）、版本迁移、API 行为差异
- **数据库与存储**：SQL/NoSQL、索引与查询优化、事务、缓存（Redis 等）、消息队列
- **DevOps 与基础设施**：K8s、Docker、CI/CD、Linux 运维、云原生、可观测性
- **前端开发**：React/Vue 等框架、构建工具（Vite/Webpack）、浏览器 API、CSS 工程化
- **移动开发**：Android/iOS、Flutter、React Native
- **通用形式**：技术教程、操作指南、最佳实践文档、技术博客、技术对比评测

## 不适用场景

- 纯理论/学术论文（需要专家同行评审，AI 无法替代）
- 非技术类内容（散文、小说、新闻评论）
- 纯个人经验分享（"我在项目中遇到的一个坑"——个人经历无法核查）
- 企业内部私有系统、闭源库/未公开硬件寄存器等无公开资料可对照的细节（此类断言通常只能标记 ❓，需人工确认）

## 执行流程

### 阶段 1：Critic — 断言提取

```
使用 Critic System Prompt（prompts/critic.md）
输入：完整文章 Markdown
输出：10-20 个关键断言，按 6 类标注
```

**执行方式**：串行。这是整个流程的入口，必须先完成。

**输出解析**：从 Critic 的输出中解析出每个断言的结构化数据（编号、原文摘录、类别、核查问题、建议核查路径）。

如果 Critic 返回的断言数量 < 5，重新执行一次 Critic，要求它更仔细地审查。

### 阶段 2：Verifier — 并行交叉验证

```
使用 Verifier System Prompt（prompts/verifier.md）
对每个断言启动一个独立 SubAgent
SubAgent 需携带联网搜索能力
```

**执行方式**：所有 Verifier SubAgent 并行启动。

**关键要求**：
- 每个 SubAgent 使用**独立的对话上下文**（Agent 工具默认行为）
- 每个 SubAgent 携带 Verifier System Prompt + 单个断言的数据
- SubAgent 需要联网搜索权限（WebSearch + WebFetch 工具）
- 禁止 Critic 的输出和原文全文进入 Verifier 上下文（仅携带其负责的单个断言）

**并发控制**：
- 默认同时启动全部 SubAgent
- 如果断言数量较多（>15），可分批启动（每批 10 个）

**输出收集**：等待所有 SubAgent 完成后，按编号收集核查结果。

### 阶段 3：Repairer — 自动修复

```
使用 Repairer System Prompt（prompts/repairer.md）
输入：原始文章全文 + 所有核查结果
输出：修复报告 + 修复后文章
```

**执行方式**：串行。必须在所有 Verifier 完成后执行。

**筛选输入**：只将有问题的核查结果（⚠️ 不完整 / ❌ 错误 / ❓ 无法确定）传给 Repairer。✅ 准确的断言不需要修复。

### 阶段 4：报告

向用户展示：

1. **核查摘要**：
   - 总共验证了 N 个断言
   - ✅ 准确：X 个
   - ⚠️ 不完整：Y 个
   - ❌ 错误：Z 个
   - ❓ 无法确定：W 个

2. **修复清单**：哪些问题已自动修复

3. **待人工确认项**：❓ 无法确定的内容

4. **输出文件**：
   - `article-verified.md`：修复后的文章
   - `verification-report.md`：完整核查报告（含所有断言 + 核查结论 + 来源）

## 用户交互规则

- **默认全自动执行**：Critic → Verifier × N → Repairer → 报告，中间不询问用户
- **如果用户说"先审再改"**：阶段 2 完成后暂停，展示核查结果让用户审核，由用户决定哪些要修复，再进入阶段 3
- **如果用户说"只查不改"**：跳过阶段 3，只输出核查报告
- **如果用户标注了特定关注点**（如"重点检查命令参数"）：在阶段 1 中将用户指示传递给 Critic

## 核心设计原则

1. **角色分离**：Critic 只提问不回答，Verifier 只核查不修改，Repairer 只修复不质疑
2. **上下文隔离**：每个 Verifier 独立上下文，避免 Critic 的偏见"传染"给 Verifier
3. **联网优先**：所有核查必须基于联网搜索结果，不得仅凭模型内置知识
4. **权威来源**：严格区分可信来源和内容农场，宁缺毋滥
5. **最小修复**：只改有问题的部分，保持原文风格
