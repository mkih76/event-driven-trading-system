#!/bin/bash
# =============================================================================
# Event Trading System - VPS 一键部署脚本
# 适用系统: Ubuntu 20.04+ / Debian 11+
# 使用方式: bash <(curl -sL https://raw.githubusercontent.com/mkih76/event-driven-trading-system/master/deploy.sh)
# 或本地运行: bash deploy.sh
# =============================================================================

set -e

APP_DIR="/opt/event-trading-system"
ENV_FILE="$APP_DIR/.env"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 检查 root
if [[ $EUID -ne 0 ]]; then
   warn "建议使用 root 运行: sudo bash deploy.sh"
fi

# =============================================================================
# 步骤 1: 检查环境
# =============================================================================
info "检查系统环境..."

if ! command -v docker &> /dev/null; then
    info "安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    info "Docker 安装完成"
fi

if ! command -v docker-compose &> /dev/null; then
    info "安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    info "Docker Compose 安装完成"
fi

docker --version
docker-compose --version

# =============================================================================
# 步骤 2: 创建目录
# =============================================================================
info "创建应用目录..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# =============================================================================
# 步骤 3: 下载最新代码
# =============================================================================
if [ -d "$APP_DIR/.git" ]; then
    info "更新代码..."
    git pull origin master
else
    info "克隆代码仓库..."
    git clone https://github.com/mkih76/event-driven-trading-system.git "$APP_DIR"
    cd "$APP_DIR"
fi

# =============================================================================
# 步骤 4: 配置环境变量
# =============================================================================
if [ ! -f "$ENV_FILE" ]; then
    info "创建配置文件..."
    cp "$APP_DIR/.env.example" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    warn "请编辑 $ENV_FILE 填入你的 API Key"
    warn "推荐使用 SiliconFlow（国内可直接访问）: https://cloud.siliconflow.cn"
    echo ""
    read -p "请输入 SiliconFlow API Key（跳过请直接回车）: " API_KEY
    if [ -n "$API_KEY" ]; then
        sed -i "s/your_siliconflow_api_key/$API_KEY/" "$ENV_FILE"
        info "API Key 已配置"
    else
        warn "未配置 API Key，LLM 调用将使用降级模式"
    fi
else
    info "使用已有配置文件"
fi

# =============================================================================
# 步骤 5: 配置防火墙
# =============================================================================
info "配置防火墙..."

if command -v ufw &> /dev/null; then
    ufw allow 22/tcp    comment 'SSH'
    ufw allow 80/tcp    comment 'HTTP'
    ufw allow 443/tcp   comment 'HTTPS'
    ufw --force enable
    info "防火墙已开放 22/80/443 端口"
elif command -v firewalld &> /dev/null; then
    firewall-cmd --permanent --add-port=80/tcp
    firewall-cmd --permanent --add-port=443/tcp
    firewall-cmd --reload
fi

# =============================================================================
# 步骤 6: 启动服务
# =============================================================================
info "构建并启动容器（首次部署约需 3-5 分钟）..."
docker-compose up -d --build

# =============================================================================
# 步骤 7: 健康检查
# =============================================================================
info "等待服务启动..."

for i in {1..30}; do
    sleep 2
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        info "后端 API 就绪 ✓"
        break
    fi
    if [ $i -eq 30 ]; then
        error "后端启动超时，请检查日志: docker-compose logs backend"
    fi
    echo -n "."
done

for i in {1..15}; do
    sleep 2
    if curl -sf http://localhost > /dev/null 2>&1; then
        info "前端就绪 ✓"
        break
    fi
    if [ $i -eq 15 ]; then
        warn "前端启动较慢，稍后请访问 http://$(curl -s ifconfig.me):80"
    fi
    echo -n "."
done

echo ""
echo ""
info "============================================"
info "  部署完成!"
info "============================================"
info "  前端地址: http://$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
info "  API 地址: http://$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):8080"
info "  健康检查: http://$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):8080/health"
info ""
info "  常用命令:"
info "    查看日志:    cd $APP_DIR && docker-compose logs -f"
info "    重启服务:    cd $APP_DIR && docker-compose restart"
info "    更新代码:    cd $APP_DIR && git pull && docker-compose up -d --build"
info "    停止服务:    cd $APP_DIR && docker-compose down"
info "============================================"
info ""

# =============================================================================
# 步骤 8: SSL 证书（可选）
# =============================================================================
echo ""
read -p "是否需要配置 HTTPS（Let's Encrypt）？(y/N): " ENABLE_SSL
if [ "$ENABLE_SSL" = "y" ] || [ "$ENABLE_SSL" = "Y" ]; then
    read -p "请输入你的域名: " DOMAIN
    if [ -n "$DOMAIN" ]; then
        info "配置 SSL 证书..."
        apt-get update && apt-get install -y certbot python3-certbot-nginx
        certbot --nginx -d "$DOMAIN" --noninteractive --agree-tos -m admin@"$DOMAIN"
        info "HTTPS 配置完成: https://$DOMAIN"
    fi
fi
