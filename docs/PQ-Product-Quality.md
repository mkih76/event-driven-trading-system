# IO 方案 - 产品质量标准

---

## 一、代码质量标准

### 1.1 前端代码质量

| 指标 | 标准 |
|------|------|
| TypeScript | 严格模式，`tsc --noEmit` 零错误 |
| ESLint | 无 error 级别警告 |
| 测试覆盖 | 核心 hooks 单元测试（useAnalysis） |
| 构建 | `next build` 通过，无 warnings 导致构建失败 |

### 1.2 后端代码质量

| 指标 | 标准 |
|------|------|
| Python | 3.11+，无语法错误 |
| 类型 | Pydantic 模型完整覆盖 API 输入输出 |
| 异常处理 | 所有 LLM 调用有 try/except，有重试机制 |
| 降级 | LLM 不可用时自动切换 RuleBasedFallback 模式 |

---

## 二、功能验收标准

### 2.1 核心功能

| 功能点 | 验收条件 |
|--------|----------|
| 事件理解 | 输入事件标题，返回事件类型、情绪值(-1~1)、核心实体列表 |
| 传导分析 | 返回完整传导链，每步包含起止行业、传导类型、传导率、时滞 |
| 信号生成 | 每条信号包含行业、做多/做空、置信度(0-100)、推理依据 |
| 流式分析 | SSE 正确推送 step1/step2/step3/step99 四类事件 |
| 降级提示 | LLM 不可用时，前端显示 DegradationBanner |

### 2.2 可视化功能

| 功能点 | 验收条件 |
|--------|----------|
| 传导图谱 | SVG 正确渲染任意节点数，节点悬停放大，边着色正确 |
| 情绪仪表 | 数值显示与颜色（红/绿）对应正确 |
| 响应式布局 | 移动端（375px）可正常浏览 |

### 2.3 接口契约

```
POST /api/v1/analyze
Response:
{
  "success": true,
  "data": {
    "event_analysis": { ... },
    "transmission": { "transmission_chain": [...] },
    "signals": [...],
    "processing_time_ms": 1234
  },
  "cached": false,
  "degradation_message": "当前使用规则模式..."
}

POST /api/v1/analyze/stream
Response: text/event-stream
  event: step=1, status=done|streaming, data={...}
  event: step=2, status=done|streaming, data={...}
  event: step=3, status=done|streaming, data=[...]
  event: step=99, status=done
```

---

## 三、性能标准

| 指标 | 标准 |
|------|------|
| API 响应时间（P99） | ≤ 30秒（含 LLM 调用） |
| 前端首屏加载 | ≤ 3秒（4G 网络） |
| 并发支持 | 单实例支持 50 并发请求 |
| 缓存 | 相同事件标题结果缓存，TTL=1小时 |

---

## 四、安全标准

| 检查项 | 要求 |
|--------|------|
| API Key | 不硬编码，存储于环境变量或 .env |
| .env | 已加入 .gitignore，不提交到代码仓库 |
| CORS | 仅允许已知域名访问 API |
| 输入校验 | Pydantic 模型校验所有输入字段 |
| 限流 | 生产环境建议配置 Nginx 限流 |

---

## 五、兼容性标准

| 项目 | 要求 |
|------|------|
| 浏览器 | Chrome 90+、Firefox 90+、Safari 15+、Edge 90+ |
| 操作系统 | Windows 10+、macOS 12+、Ubuntu 20.04+ |
| 移动端 | iOS Safari 15+、Android Chrome 90+ |
| 屏幕 | 桌面优先，支持 1366x768 及以上分辨率 |
