# -*- coding: utf-8 -*-
"""
A股缠论分析脚本

从 baostock（默认）或 akshare 拉取任意 A股 K线数据，
运行缠论计算（分型/笔/线段/中枢/买卖点/背驰），并生成可独立打开的图表 HTML。

用法示例：
    # 贵州茅台 日线，前复权
    python chanlun_a.py --code 600519 --freq d --start 2023-01-01 --end 2024-06-30

    # 平安银行 30 分钟线，不复权
    python chanlun_a.py --code 000001 --freq 30 --adjust 不复权

    # 指定数据源 akshare
    python chanlun_a.py --code 600519 --freq d --source akshare

参数说明：
    --code    6 位 A股代码（6/9 开头为沪市，其余为深市）
    --freq    周期：d=日线 w=周线 m=月线，或 5/15/30/60=分钟线
    --start   开始日期 YYYY-MM-DD
    --end     结束日期 YYYY-MM-DD
    --adjust  复权方式：前复权/后复权/不复权（默认前复权）
    --source  数据源：baostock（默认）/ akshare
    --out     输出 HTML 文件名（默认 chart.html）
"""
import argparse
import datetime
import pathlib
import sys

# Windows 控制台默认 GBK，直接 print UTF-8 中文会乱码，这里强制以 UTF-8 输出
if sys.platform == "win32":

    class _UTF8Filter:
        def __init__(self, target):
            self.target = target

        def write(self, s):
            self.target.buffer.write(s.encode("utf-8"))
            self.target.buffer.flush()

        def flush(self):
            self.target.flush()

    sys.stdout = _UTF8Filter(sys.stdout)
    sys.stderr = _UTF8Filter(sys.stderr)

# 将本项目 src 目录加入搜索路径，以导入开源版 chanlun 包
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

import pandas as pd  # noqa: E402

from chanlun import cl  # noqa: E402
from chanlun import kcharts  # noqa: E402


def to_baostock_code(code: str) -> str:
    """把 6 位代码转成 baostock 需要的 sh./sz. 前缀格式"""
    code = code.strip()
    if code.lower().startswith(("sh.", "sz.")):
        return code.lower()
    if code[0] in ("6", "9"):
        return "sh." + code
    return "sz." + code


def fetch_baostock(code: str, freq: str, start: str, end: str, adjust: str) -> pd.DataFrame:
    """通过 baostock 拉取 A股 K线数据"""
    import baostock as bs

    adjust_flag = {"前复权": "2", "后复权": "1", "不复权": "3"}[adjust]
    bs_code = to_baostock_code(code)

    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock 登录失败: {lg.error_msg}")

    try:
        # 分钟线额外请求 time 字段（含具体时分秒），日/周/月线不支持该字段
        if freq in ("5", "15", "30", "60"):
            fields = "date,time,code,open,high,low,close,volume"
        else:
            fields = "date,code,open,high,low,close,volume"
        rs = bs.query_history_k_data_plus(
            bs_code, fields, start_date=start, end_date=end,
            frequency=freq, adjustflag=adjust_flag,
        )
        if rs.error_code != "0":
            raise RuntimeError(f"baostock 查询失败: {rs.error_msg}")
        df = rs.get_data()
    finally:
        bs.logout()

    if df.empty:
        raise RuntimeError(f"未获取到数据，请检查代码 {code} 与日期范围")

    # 分钟线：真实时间在 time 字段（17 位 YYYYMMDDHHMMSSmmm）；日/周/月：用 date 字段
    if freq in ("5", "15", "30", "60"):
        df["date"] = pd.to_datetime(df["time"], format="%Y%m%d%H%M%S%f")
    else:
        df["date"] = pd.to_datetime(df["date"])

    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df.reset_index(drop=True)


def fetch_akshare(code: str, freq: str, start: str, end: str, adjust: str) -> pd.DataFrame:
    """通过 akshare（东方财富）拉取 A股 K线数据"""
    import os

    import akshare as ak
    import requests

    # 复权方式映射：中文 -> akshare 参数（qfq=前复权 hfq=后复权 ''=不复权）
    adjust_map = {"前复权": "qfq", "后复权": "hfq", "不复权": ""}
    ak_adjust = adjust_map[adjust]

    # 东财是境内站点，走系统代理（如 Clash/VPN）会被服务器掐断，这里强制 requests 直连
    for _env in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        os.environ.pop(_env, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"
    _orig_request = requests.sessions.Session.request

    def _request_direct(self, method, url, **kwargs):
        # 忽略系统代理，直连
        self.trust_env = False
        return _orig_request(self, method, url, **kwargs)

    requests.sessions.Session.request = _request_direct

    if freq in ("5", "15", "30", "60"):
        # 分钟线走 stock_zh_a_hist_min_em，历史更长
        df = ak.stock_zh_a_hist_min_em(
            symbol=code, period=freq,
            start_date=f"{start} 00:00:00", end_date=f"{end} 23:59:59",
            adjust=ak_adjust,
        )
    else:
        # 日/周/月线走 stock_zh_a_hist
        period = {"d": "daily", "w": "weekly", "m": "monthly"}[freq]
        start_fmt = start.replace("-", "")
        end_fmt = end.replace("-", "")
        df = ak.stock_zh_a_hist(
            symbol=code, period=period,
            start_date=start_fmt, end_date=end_fmt, adjust=ak_adjust,
        )

    if df.empty:
        raise RuntimeError(f"未获取到数据，请检查代码 {code} 与日期范围")

    # 统一列名：分钟线是「时间」列，日/周/月线是「日期」列
    df = df.rename(columns={"日期": "date", "时间": "date", "开盘": "open", "收盘": "close",
                            "最高": "high", "最低": "low", "成交量": "volume"})
    df["date"] = pd.to_datetime(df["date"])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[["date", "open", "high", "low", "close", "volume"]]
    return df.reset_index(drop=True)


def freq_label(freq: str) -> str:
    """把周期参数转成图表标题里的人类可读标签"""
    return {"d": "d", "w": "w", "m": "m"}.get(freq, f"{freq}m")


def render_standalone_html(title: str, cl_data) -> pathlib.Path:
    """将缠论图表渲染成独立可打开的 HTML 文件"""
    options_json = kcharts.render_charts(title, cl_data, config={"show_bi_zs": True, "show_ma": False})
    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
</head>
<body>
<div id="chart" style="width:1400px;height:760px;"></div>
<script>
var chart = echarts.init(document.getElementById('chart'));
chart.setOption({options});
window.addEventListener('resize', function() {{ chart.resize(); }});
</script>
</body>
</html>""".format(title=title, options=options_json)
    out = pathlib.Path(ARGS.out)
    out.write_text(html, encoding="utf-8")
    return out


# 买卖点 / 背驰 的中文名称与排序
MMD_CN = {
    "1buy": "一买", "2buy": "二买", "3buy": "三买",
    "l2buy": "类二买", "l3buy": "类三买",
    "1sell": "一卖", "2sell": "二卖", "3sell": "三卖",
    "l2sell": "类二卖", "l3sell": "类三卖",
}
MMD_ORDER = {"1buy": 0, "2buy": 1, "l2buy": 2, "3buy": 3, "l3buy": 4,
             "1sell": 5, "2sell": 6, "l2sell": 7, "3sell": 8, "l3sell": 9}
BC_CN = {"bi": "笔背驰", "xd": "线段背驰", "pz": "盘整背驰", "qs": "趋势背驰"}
BC_ORDER = {"bi": 0, "xd": 1, "pz": 2, "qs": 3}


def _fmt_date(fx):
    """分型可能为空（未完成的线），安全取时间"""
    if fx is None or fx.k is None:
        return ""
    return str(fx.k.date)


def export_signals_csv(cl_data, path):
    """把每根笔 / 线段上的买卖点、背驰信号导出为 CSV（每行一条线）"""
    rows = []

    def add_row(prefix, line):
        mmd_codes = {m.name for m in line.mmds}
        mmds = [MMD_CN[c] for c in sorted(mmd_codes, key=lambda c: MMD_ORDER.get(c, 99))]
        bc_codes = {b.type for b in line.bcs if b.bc}
        bcs = [BC_CN[c] for c in sorted(bc_codes, key=lambda c: BC_ORDER.get(c, 99))]
        rows.append({
            "线类型": prefix,
            "索引": line.index,
            "方向": "上涨" if line.type == "up" else "下跌",
            "开始时间": _fmt_date(line.start),
            "结束时间": _fmt_date(line.end),
            "最高价": round(line.high, 4) if line.high is not None else "",
            "最低价": round(line.low, 4) if line.low is not None else "",
            "是否完成": line.done,
            "买卖点": "|".join(mmds),
            "背驰": "|".join(bcs),
        })

    for bi in cl_data.bis:
        add_row("笔", bi)
    for xd in cl_data.xds:
        add_row("线段", xd)

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8-sig")  # utf-8-sig 便于 Excel 直接打开不乱码
    return df


def main():
    print(f"数据源: {ARGS.source}  代码: {ARGS.code}  周期: {freq_label(ARGS.freq)}  {ARGS.adjust}")
    fetch = fetch_baostock if ARGS.source == "baostock" else fetch_akshare
    klines = fetch(ARGS.code, ARGS.freq, ARGS.start, ARGS.end, ARGS.adjust)
    print(f"获取 K线: {len(klines)} 根  ({klines['date'].min().date()} ~ {klines['date'].max().date()})")

    # 缠论配置：老笔、段内中枢、实际高低点、允许分型包含成笔
    cl_config = {"bi_type": "old", "no_bi": False, "zs_type": "dn", "zs_qj": "hl", "fx_baohan": True}
    code_label = f"{ARGS.code} ({'沪' if ARGS.code[0] in '69' else '深'})"
    cl_data = cl.CL(code_label, freq_label(ARGS.freq), cl_config).process_klines(klines)

    print(f"分型: {len(cl_data.fxs)}  笔: {len(cl_data.bis)}  线段: {len(cl_data.xds)}  "
          f"笔中枢: {len(cl_data.bi_zss)}  线段中枢: {len(cl_data.xd_zss)}")

    # 输出最近的买卖点与背驰信号
    if cl_data.bis:
        last_bi = cl_data.bis[-1]
        print(f"最后一笔: {last_bi}")
        print(f"  盘整背驰: {last_bi.bc_exists(['pz'])}  趋势背驰: {last_bi.bc_exists(['qs'])}")
        mmds = last_bi.line_mmds()
        if mmds:
            print(f"  最近买卖点: {[m for m in mmds]}")

    out = render_standalone_html(f"{code_label} - {freq_label(ARGS.freq)}", cl_data)
    print(f"图表已生成: {out.resolve()}")

    # 导出买卖点 / 背驰信号到 CSV
    sig_df = export_signals_csv(cl_data, ARGS.csv)
    signal_rows = sig_df[(sig_df["买卖点"] != "") | (sig_df["背驰"] != "")]
    print(f"信号已导出: {pathlib.Path(ARGS.csv).resolve()}  "
          f"(共 {len(sig_df)} 条线，含信号 {len(signal_rows)} 条)")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="A股缠论分析：拉取K线 -> 缠论计算 -> 图表")
    p.add_argument("--code", default="600519", help="6位A股代码")
    p.add_argument("--freq", default="d", help="周期: d/w/m 或 5/15/30/60")
    p.add_argument("--start", default="2023-01-01", help="开始日期 YYYY-MM-DD")
    p.add_argument("--end", default="2024-06-30", help="结束日期 YYYY-MM-DD")
    p.add_argument("--adjust", default="前复权", choices=["前复权", "后复权", "不复权"])
    p.add_argument("--source", default="baostock", choices=["baostock", "akshare"])
    p.add_argument("--out", default="chart.html", help="输出HTML文件名")
    p.add_argument("--csv", default="signals.csv", help="买卖点/背驰信号输出CSV文件名")
    ARGS = p.parse_args()

    if not (ARGS.code.isdigit() and len(ARGS.code) == 6):
        sys.exit("错误：--code 应为 6 位数字代码，例如 600519")

    main()
