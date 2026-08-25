# 历史行情缠论分析工具

---

`chanlun` 是一个基于缠中说禅理论，用于历史行情数据分析的 Python 包。

可用于量化交易、Jupyter 分析、以及 Html 页面展示。

> 项目 GitHub 地址 : https://github.com/luoweining/chanlun

**主要功能**

目前，`chanlun` 已经实现以下功能:

* 分型
* 笔
* 线段
* 中枢
* 买卖点
* 背驰
* 趋势
* 多级别分析

## 安装

### 用 pip 安装

    pip install -U chanlun

### 本地编译安装

    git clone https://github.com/luoweining/chanlun.git
    cd chanlun
    python3 setup.py install

### 使用示例

[使用示例.ipynb](https://github.com/luoweining/chanlun/tree/main/example/使用示例.ipynb)

    import pandas as pd
    from chanlun import cl
    from chanlun import kcharts

    # 获取 行情K线数据
    code = 'SH.688122'
    frequency = '30m'
    klines = pd.read_csv('./data/688122.csv')

    # 依据 K 线数据，计算缠论数据
    cl_data = cl.CL(code, frequency).process_klines(klines)
    chart = kcharts.render_charts('%s - %s' % (code, frequency), cl_data)
    # 图标展示
    chart

## chanlun_a.py —— A股缠论分析脚本

一个命令行脚本，自动完成「拉取 A股 K线 → 缠论计算 → 生成图表 + 信号 CSV」，无需手动准备数据。

### 依赖

复用项目已有依赖（`pandas` / `numpy` / `pyecharts` / `TA-Lib`），数据源用 `baostock`（默认，稳定）或 `akshare`。

### 用法

```bash
# 贵州茅台 日线，前复权
python chanlun_a.py --code 600519 --freq d --start 2023-01-01 --end 2024-06-30

# 平安银行 30 分钟线
python chanlun_a.py --code 000001 --freq 30 --start 2024-05-01 --end 2024-06-30
```

### 参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `--code` | 6 位 A股代码（6/9 开头沪市，其余深市） | 600519 |
| `--freq` | 周期：`d`/`w`/`m` 或 `5`/`15`/`30`/`60` 分钟 | d |
| `--start` | 开始日期 YYYY-MM-DD | 2023-01-01 |
| `--end` | 结束日期 YYYY-MM-DD | 2024-06-30 |
| `--adjust` | 复权方式：前复权 / 后复权 / 不复权 | 前复权 |
| `--source` | 数据源：baostock / akshare | baostock |
| `--csv` | 信号 CSV 输出文件名 | signals.csv |
| `--out` | 图表 HTML 输出文件名 | chart.html |

### 输出

- `chart.html`：K线 + 分型 + 笔 + 线段 + 中枢 + MACD 图表，双击浏览器打开
- `signals.csv`：每根笔 / 线段上的买卖点（一买 / 二买 / 三买 / 类二买 / 类三买 + 对应卖点）与背驰（笔 / 线段 / 盘整 / 趋势）信号，Excel 直接打开不乱码

### 实际效果展示

![Demo-1](https://github.com/luoweining/chanlun/raw/main/images/demo-1.png)

**有 bug 请在这个页面提交： https://github.com/luoweining/chanlun/issues**
