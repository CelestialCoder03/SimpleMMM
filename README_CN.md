# SimpleMMM

[English](README.md) | [中文](README_CN.md)

一个现代化的开源营销组合模型（Marketing Mix Modeling）Web 应用。上传营销数据，配置模型，使用多种回归技术进行训练，并通过直观的界面查看结果。

## 功能特性

**建模能力**
- 多种模型类型：OLS、Ridge、贝叶斯回归（PyMC）、ElasticNet
- 数据变换：广告存量效应（几何衰减、Weibull）、饱和效应（Hill、Logistic）
- 灵活约束：系数范围、符号约束、贡献度限制
- 多粒度分析：全国、区域、城市、渠道级别建模
- 层级模型：支持约束和先验的继承
- 预算优化与情景分析

**前端**
- React 19 + TypeScript + Vite
- 分步式模型配置向导
- 基于 ECharts 的交互式可视化（分解图、贡献度图、响应曲线）
- 中英文双语支持（i18n）
- 深色/浅色主题，跟随系统偏好

**后端**
- 基于 Celery + Redis 的异步模型训练
- 数据探索：描述性统计、相关性分析、分布可视化、时序预览
- 导出功能：CSV、Excel、JSON、HTML 报告
- RESTful API，附带 OpenAPI 文档

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI, Python 3.11+, SQLAlchemy, Celery |
| 前端 | React 19, TypeScript, Vite, TailwindCSS, shadcn/ui, ECharts |
| 状态管理 | Zustand（客户端）, TanStack Query（服务端）|
| 数据库 | PostgreSQL, Redis |
| 建模 | scikit-learn, PyMC, NumPy, Pandas |
| 部署 | Docker Compose, Nginx |

## 快速开始

### Docker Compose（推荐）

```bash
git clone https://github.com/CelestialCoder03/SimpleMMM.git
cd SimpleMMM

# 启动所有服务（API、前端、PostgreSQL、Redis、Celery Worker、Nginx）
cd docker
docker compose up -d

# 访问应用
# 应用：    http://localhost
# API 文档：http://localhost/api/docs
```

### 本地开发

**前置条件：** Python 3.11+（需安装 [uv](https://docs.astral.sh/uv/)）、Node.js 22+、PostgreSQL、Redis

**1. 启动基础服务：**

```bash
# 方式 A：仅用 Docker 运行数据库服务
cd docker && docker compose up -d db redis

# 方式 B：本地安装（macOS）
brew install postgresql@16 redis
brew services start postgresql@16 redis
createdb mmm
```

**2. 配置环境变量：**

```bash
cp .env.example .env
# 按需编辑 .env —— 默认配置适用于本地开发
```

**3. 后端：**

```bash
cd backend
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# 在另一个终端启动 Celery Worker
uv run celery -A app.workers.celery_app worker -l info
```

**4. 前端：**

```bash
cd frontend
npm install
npm run dev
```

**5. 打开应用：**

- 前端界面：http://localhost:3000
- API 文档：http://localhost:8000/api/v1/docs

## 项目结构

```
SimpleMMM/
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── api/       # REST 接口
│   │   ├── models/    # SQLAlchemy 模型
│   │   ├── schemas/   # Pydantic 数据模式
│   │   ├── services/  # 业务逻辑与建模引擎
│   │   └── workers/   # Celery 异步任务
│   └── migrations/    # Alembic 数据库迁移
├── frontend/          # React 前端
│   └── src/
│       ├── api/       # API 客户端
│       ├── components/# UI 组件
│       ├── pages/     # 页面组件
│       ├── stores/    # Zustand 状态管理
│       └── i18n/      # 国际化翻译
├── docker/            # Docker Compose 配置
│   ├── docker-compose.yml
│   └── nginx/
└── docs/              # 文档
```

## 文档

- [建模规范](docs/modeling-specification.md) — 支持的模型、数据变换、约束条件
- [API 规范](docs/api-specification.md) — REST API 接口说明

## 许可证

[MIT](LICENSE)
