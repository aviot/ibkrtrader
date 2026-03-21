# IBKR PySide6 桌面交易终端

现在这个项目改成了 **PySide6 桌面 GUI**，不是终端 TUI 了。

它的目标是提供一个可继续扩展的 IBKR 手动交易桌面端：

- **桌面窗口 GUI**，适合放在多屏交易环境里。
- **实时行情** 自动刷新 `last / bid / ask`。
- **小键盘即时触发** 下单，不需要回车。
- **持仓 / 未成交订单 / 账户 / 活动日志** 都在一个窗口里。
- 默认依然支持 **dry-run**，方便你本地联调热键和界面。

## 当前界面

主窗口包含：

- **交易概览**：symbol、模式、最新价、买卖价、更新时间、当前数量、限价偏移。
- **实时行情面板**
- **账户面板**
- **快捷下单面板**
- **持仓表格**
- **未成交订单表格**
- **小键盘映射表**
- **活动日志**

## 小键盘映射

- `8`：市价买入
- `2`：市价卖出
- `7`：限价买入（`last - offset`）
- `1`：限价卖出（`last + offset`）
- `0`：全部撤单
- `+`：数量 `+100`
- `-`：数量 `-100`
- `4`：缩小限价偏移
- `6`：扩大限价偏移
- `Esc`：关闭窗口

## 安装

### 仅安装项目

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 安装 GUI

```bash
pip install -e '.[gui]'
```

### 安装 GUI + IBKR API

```bash
pip install -e '.[gui,ibkr]'
```

## 运行

### 本地 dry-run GUI

```bash
ibkr-shell
```

### 接 TWS / IB Gateway

```bash
export IBKR_DRY_RUN=false
export IBKR_HOST=127.0.0.1
export IBKR_PORT=7497
export IBKR_CLIENT_ID=7
export IBKR_SYMBOL=TSLA
export IBKR_QUANTITY=100
ibkr-shell
```

## 环境变量

- `IBKR_HOST`
- `IBKR_PORT`
- `IBKR_CLIENT_ID`
- `IBKR_SYMBOL`
- `IBKR_EXCHANGE`
- `IBKR_CURRENCY`
- `IBKR_QUANTITY`
- `IBKR_DRY_RUN`
- `IBKR_REFRESH_HZ`

## Windows 双击启动打包

如果你要做成“下载后双击打开”的 Windows GUI，可以直接用仓库里自带的打包配置：

### 安装打包依赖

```bash
pip install -e ".[build,gui,ibkr]"
```

### 构建 exe

```bash
python scripts/build_windows.py
```

构建完成后，可执行文件会在：

```text
dist/ibkr-shell/ibkr-shell.exe
```

这个产物就是面向 Windows 的双击启动版本。源码仓库里还附带了 `launch_gui.pyw`，如果用户机器已经装好了 Python 和依赖，也可以直接双击这个 `pyw` 文件启动 GUI。

## 当前行为说明

### dry-run

- 会自动生成模拟实时行情。
- 下单后会立即反映到持仓和账户面板。
- 适合先验证 GUI 排布和小键盘手感。

### live IBKR

- 连接 TWS / IB Gateway。
- 自动刷新实时行情。
- 自动拉取当前 symbol 的持仓、未成交订单和账户摘要。
- 可直接从 GUI 用按钮或小键盘触发下单。

## 下一步建议

如果你还要继续做，我建议接着补：

1. 委托双击撤单 / 改单
2. 多 symbol watchlist
3. 成交回报面板
4. 风控弹窗（二次确认、单笔上限、最大仓位）
5. 自定义热键映射保存
