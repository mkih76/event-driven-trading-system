# OQ 方案 - 运维与运营标准

---

## 一、部署标准

### 1.1 标准化部署流程

```
1. 环境检查 → 2. 代码拉取 → 3. 配置注入 → 4. 容器构建 → 5. 健康检查 → 6. 上线
```

### 1.2 部署检查清单

- [ ] 服务器最低配置满足（2核 4G）
- [ ] Docker 和 Docker Compose 已安装
- [ ] `.env` 文件已配置（API Key）
- [ ] 防火墙已开放 80/443 端口
- [ ] `docker-compose up -d` 执行成功
- [ ] `curl http://localhost/health` 返回 200
- [ ] 前端 `http://localhost` 可访问

---

## 二、监控标准

### 2.1 核心监控指标

| 指标 | 告警阈值 | 处理方式 |
|------|----------|----------|
| 后端健康检查 | 连续 3 次失败 | 触发重启 |
| 容器内存使用 | > 90% | 告警通知 |
| API 错误率 | > 5% | 查看日志排查 |
| 磁盘使用 | > 80% | 清理日志与缓存 |
| LLM 调用延迟 | > 60s | 检查 API Key 额度 |

### 2.2 日志管理

```bash
# 查看实时日志
docker-compose logs -f [backend|frontend|nginx]

# 日志保留策略
- 开发环境：保留最近 3 天
- 生产环境：保留最近 7 天，建议配置日志收集

# 日志文件位置
/opt/event-trading-system/data/logs/
```

---

## 三、运维操作规范

### 3.1 日常维护

| 操作 | 命令 |
|------|------|
| 查看所有容器状态 | `docker-compose ps` |
| 重启指定服务 | `docker-compose restart backend` |
| 重建指定服务 | `docker-compose up -d --build backend` |
| 更新代码 | `git pull && docker-compose up -d --build` |
| 清理未使用镜像 | `docker image prune -f` |
| 查看资源占用 | `docker stats` |

### 3.2 故障处理

**LLM 服务不可用（降级模式启动）：**
```
1. 检查 API Key 是否正确配置
2. 登录 SiliconFlow/OpenAI 控制台检查余额
3. 如国内访问异常，检查 VPS 网络策略
4. 切换备用 LLM Provider
```

**前端无法加载：**
```
1. docker-compose logs frontend  # 查看构建日志
2. docker-compose restart frontend
3. docker-compose up -d --build frontend
```

**API 返回 500 错误：**
```
1. docker-compose logs backend
2. 检查 .env 配置是否完整
3. 重启后端: docker-compose restart backend
```

### 3.3 数据备份

```bash
# 备份数据目录
tar -czf backup_$(date +%Y%m%d).tar.gz /opt/event-trading-system/data/

# 备份 .env 配置
cp /opt/event-trading-system/.env ~/event-trading-env.bak
```

---

## 四、版本管理

### 4.1 版本命名

```
v{MAJOR}.{MINOR}.{PATCH}
- MAJOR: 架构重大调整
- MINOR: 新增功能
- PATCH: Bug 修复
```

### 4.2 更新流程

```bash
cd /opt/event-trading-system

# 1. 备份当前状态
cp .env .env.bak

# 2. 更新代码
git pull origin master

# 3. 重新构建
docker-compose up -d --build

# 4. 健康检查
curl http://localhost/health

# 5. 如有问题回滚
git reset --hard HEAD~1
docker-compose up -d --build
```

---

## 五、安全运营

| 安全项 | 措施 |
|--------|------|
| API Key 保护 | .env 文件权限 600，不放 Git |
| 定期更新 | 每月检查 Docker 镜像更新 |
| 访问控制 | 生产环境配置 Nginx 认证或 IP 白名单 |
| HTTPS | 使用 Let's Encrypt 配置 SSL 证书 |
| 备份 | 每周自动备份 .env 和数据目录 |

---

## 六、应急响应

| 级别 | 场景 | 响应时间 | 处理方式 |
|------|------|----------|----------|
| P0 | 服务完全不可用 | 15 分钟 | 重启服务，联系云厂商 |
| P1 | API 返回错误率 > 20% | 30 分钟 | 查看日志，切换备用 LLM |
| P2 | 响应延迟明显增加 | 2 小时 | 检查 LLM API 余额与限流 |
| P3 | 非核心功能异常 | 24 小时 | 下次版本修复 |

---

## 七、联系方式

| 角色 | 职责 |
|------|------|
| 项目维护者 | GitHub Issues: mkih76/event-driven-trading-system |
| 文档 | docs/ 目录下所有运营文档 |
| 紧急联系 | 通过 GitHub Issue 提交工单 |
