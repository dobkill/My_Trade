# A-Trade A股行情研究终端 MVP

这是一个本地个人使用的 A 股行情研究终端 MVP，不包含自动交易、券商下单、账户登录或复杂量化框架。

整体模块保持解耦：

```text
A股行情数据 -> FastAPI Backend -> REST/WebSocket -> React + KLineChart Pro GUI
                         |
                         +-> Parquet / CSV -> ml/ PyTorch 示例
```

## 项目结构

```text
backend/   FastAPI、Provider 抽象、实时服务、Parquet/CSV 数据层
frontend/  React + TypeScript + Vite + @klinecharts/pro 行情 GUI
ml/        可选 PyTorch Dataset/MLP pipeline 示例
data/      本地 Parquet、CSV、缓存数据
scripts/   安装、启动、联调、smoke test 脚本
```

## 安装

使用已有 Conda 环境，不创建新的 venv 或 conda env：

```bash
cd /home/a/Yuan/Code/A_Trade
conda activate Trade
./scripts/bootstrap.sh
```

`bootstrap.sh` 会：

- 使用当前 `Trade` 环境里的 `python -m pip` 安装后端依赖
- 验证 `eltdx` import 和真实行情 quote
- 检查 `node` / `npm`
- 执行 `npm --prefix frontend install`
- 检查 PyTorch 是否存在，但不会自动安装或改变 CUDA 版本

## 启动

```bash
cd /home/a/Yuan/Code/A_Trade
conda activate Trade
./scripts/dev.sh
```

地址：

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000
Swagger:  http://127.0.0.1:8000/docs
```

也可以分别启动：

```bash
./scripts/start_backend.sh
./scripts/start_frontend.sh
```

## API

```text
GET /api/health
GET /api/symbols/search?q=茅台
GET /api/stocks/{symbol}/quote
GET /api/stocks/{symbol}/klines?period=1d&start=&end=&adjust=qfq
GET /api/stocks/{symbol}/export?period=1d&adjust=qfq&format=csv
GET /api/stocks/{symbol}/export?period=1d&adjust=qfq&format=parquet
WS  /ws/stocks/{symbol}
```

统一股票代码格式：

```text
SH.600519
SZ.000001
SZ.300750
BJ.xxxxxx
```

支持周期：

```text
1m / 5m / 15m / 30m / 60m / 1d / 1w / 1M
```

支持复权：

```text
none / qfq / hfq
```

## 数据目录

```text
data/parquet/daily/              日/周/月 K 线 upsert 数据
data/parquet/minute/{symbol}/    分钟 K 线按月分片
data/parquet/*.parquet           GUI 导出的 Parquet 文件
data/csv/                        GUI 导出的 CSV 文件
data/cache/                      股票列表等低频缓存
```

Parquet schema 保持训练友好：

```text
symbol, datetime, timestamp, open, high, low, close,
volume, turnover, period, adjust, source
```

写入时会排序、去重并 merge/upsert，避免重复保存相同 K 线。

## Provider

后端 API 不直接调用 AKShare 或 TDX，而是通过 `MarketDataProvider` 抽象访问：

```text
MarketDataManager
  -> TdxProvider
  -> AKShareProvider
```

默认配置：

```env
MARKET_DATA_PROVIDER=auto
```

`auto` 策略优先使用 TDX/eltdx，失败后 fallback 到 AKShare。GUI 右上角会显示当前行情源和连接状态。

### TDX / eltdx

`eltdx` 使用公开网络协议研究性质的免费行情源，适合个人研究，不是交易所官方行情，也不保证 SLA。当前实现用于实时 quote、盘口快照和 K 线历史。

### AKShare

AKShare Provider 实现了 A 股代码/名称搜索、东方财富历史日/周/月 K、东方财富分钟 K、实时行情表。免费公共接口可能因为网络、代理、限流或字段变更失败；后端会捕获错误并返回规范 JSON，不把 traceback 暴露给 GUI。

## 前端

前端使用：

```text
React + TypeScript + Vite + @klinecharts/pro + klinecharts
```

功能：

- 股票代码和名称搜索
- 自选股 `localStorage` 保存
- Quote header、行情源状态、WebSocket 实时更新
- 周期切换：`1m/5m/15m/30m/60m/日/周/月`
- 复权切换：不复权/前复权/后复权
- KLineChart Pro 内置指标：`MA / EMA / VOL / MACD / RSI / KDJ`
- KLineChart Pro drawing toolbar：趋势线、水平线、线段、价格线、Fibonacci、平行线/通道等内置 overlay
- CSV / Parquet 下载

## PyTorch

`ml/` 是可选示例，不被 FastAPI 或 GUI import。

如果当前 `Trade` 环境没有 PyTorch，行情终端仍然正常运行。需要训练示例时，请按你的 CPU/CUDA 情况自行安装 PyTorch，不要无脑覆盖现有 CUDA 环境。

运行示例：

```bash
python ml/train_example.py \
  --data data/parquet/daily/SH.600519.parquet
```

Dataset 输出：

```text
X = 最近 60 根 K 线的 open/high/low/close/volume
y = 下一根 K 线收益率
```

## 测试

```bash
python -m pytest
npm --prefix frontend run build
./scripts/smoke_test.sh
```

`smoke_test.sh` 会检查：

- `/api/health`
- 搜索 `600519`
- `SH.600519` 和 `SZ.000001` 日 K
- CSV 导出
- Parquet 导出
- 重新读取 Parquet
- WebSocket 建连并接收消息

如果当前休市，WebSocket 收到 `market_status=closed` 是正常行为，不会生成假 Tick。

## 配置

复制 `.env.example` 为 `.env` 后可覆盖：

```env
APP_HOST=127.0.0.1
APP_PORT=8000
MARKET_DATA_PROVIDER=auto
REALTIME_POLL_SECONDS=2.5
DATA_DIR=/home/a/Yuan/Code/A_Trade/data
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

## 注意事项

- 免费行情源不保证稳定性、延迟、字段或历史长度。
- 分钟数据只保存真实返回的数据，不伪造缺失历史。
- 本项目不包含自动交易、券商下单、Kafka/Redis/Docker/Kubernetes、复杂 AI 模型或权限系统。
