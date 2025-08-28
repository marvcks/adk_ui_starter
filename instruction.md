### 角色设定

你是一名**资深前端/全栈开发专家**，精通 **Angular**、**React** 和 **Python**。你专注于构建现代化、交互友好且功能丰富的 **AI 对话界面**。

---

### 项目目标

基于 `/Users/xiaohuxu/Documents/python/deepmodeling/build-your-agent/agents/adk_ui_starter/ui` 中的前端代码，进行**美化、调整和功能增强**，以实现一个更健壮、可维护的 AI 对话界面。

---

### 任务分解

#### 1. 调整 `websocket-server.py` 代码

**1.1. 分析与对比**

你需要深入分析以下两个代码库，并进行详细对比：
* **现有后端代码：** `/Users/xiaohuxu/Documents/python/deepmodeling/build-your-agent/agents/adk_ui_starter/websocket-server.py`
* **参考代码库：** `/Users/xiaohuxu/Documents/python/deepmodeling/build-your-agent/agents/adk_ui_starter/useful_data/adk-web-main`

重点关注前后端通信的实现方式，特别是 `adk-web-main` 中 Angular 代码与后端通信的逻辑。

分析的重点包括：
* `websocket-server.py` 中 **`async def process_message(self, context: ConnectionContext, message: str)`** 函数的结构。
* `adk-web-main` 中，前端如何处理来自后端的消息（例如，数据的状态管理、不同类型消息的展示逻辑）。

完成分析后，请总结两者的主要区别，并说明 `websocket-server.py` 中缺失或需要优化的功能。

**在给出总结后，请等待我的确认再继续。**

**1.2. 思考与修改计划**

基于上述分析，请制定一份详细的**后端代码重构计划**。此计划应解决 `websocket-server.py` 中 `process_message` 函数可读性和可维护性差的问题，并集成从 `adk-web-main` 中学到的、缺失的后端处理逻辑。

重构计划应包含：
* 具体的代码结构调整建议（例如，模块化、分层）。
* 新增功能的实现思路（例如，如何更好地处理不同类型的消息）。

**在给出修改计划后，请等待我的确认再继续。**

**1.3. 代码编写**

根据已确认的修改计划，开始编写并重构 `websocket-server.py` 代码。请确保新代码清晰、可维护，并完整实现了计划中的功能。

---
