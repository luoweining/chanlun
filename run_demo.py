# -*- coding: utf-8 -*-
"""开源版 chanlun 运行验证脚本：加载示例数据 -> 计算缠论 -> 生成图表 HTML"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

import pandas as pd
from chanlun import cl
from chanlun import kcharts

code = 'SH.688122'
frequency = '30m'
cl_config = {'bi_type': 'old', 'no_bi': False, 'zs_type': 'dn', 'zs_qj': 'hl', 'fx_baohan': True}
chart_config = {'show_bi_zs': True, 'show_ma': False}

klines = pd.read_csv('./example/data/688122.csv')
print('K线条数:', len(klines))
print('列:', list(klines.columns))

cl_data = cl.CL(code, frequency, cl_config).process_klines(klines)

print('分型数:', len(cl_data.fxs))
print('笔数:', len(cl_data.bis))
print('线段数:', len(cl_data.xds))
print('笔中枢数:', len(cl_data.bi_zss))
print('线段中枢数:', len(cl_data.xd_zss))

# 打印所有笔中枢详情
print('=== 笔中枢 %d 个（有效 %d 个） ===' % (
    len(cl_data.bi_zss), len([z for z in cl_data.bi_zss if z.real])))
for z in cl_data.bi_zss:
    print('  #%s real=%s level=%s type=%s zg=%.2f zd=%.2f gg=%s dd=%s done=%s FX=%s~%s' % (
        z.index, z.real, z.level, z.type, z.zg, z.zd, z.gg, z.dd, z.done,
        z.start.k.date, z.end.k.date))

# 打印所有线段中枢详情
print('=== 线段中枢 %d 个（有效 %d 个） ===' % (
    len(cl_data.xd_zss), len([z for z in cl_data.xd_zss if z.real])))
for z in cl_data.xd_zss:
    print('  #%s real=%s level=%s type=%s zg=%s zd=%s gg=%s dd=%s done=%s FX=%s~%s' % (
        z.index, z.real, z.level, z.type, z.zg, z.zd, z.gg, z.dd, z.done,
        z.start.k.date, z.end.k.date))

# 最后几笔的买卖点 / 背驰信息
if cl_data.bis:
    last_bi = cl_data.bis[-1]
    print('最后一笔:', last_bi)
    print('最后一笔背驰(盘整/趋势):', last_bi.bc_exists(['pz']), last_bi.bc_exists(['qs']))

options_json = kcharts.render_charts('%s - %s' % (code, frequency), cl_data, show_num=len(klines), config=chart_config)

# 将 echarts 选项包装成独立可打开的 HTML 页面
html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>html, body {{ margin: 0; padding: 0; background: #100C2A; }}</style>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/theme/dark.js"></script>
</head>
<body>
<div id="chart" style="width:100%;height:100vh;"></div>
<script>
var chart = echarts.init(document.getElementById('chart'), 'dark');
chart.setOption({options});
window.addEventListener('resize', function() {{ chart.resize(); }});
</script>
</body>
</html>""".format(title='%s - %s' % (code, frequency), options=options_json)

out = pathlib.Path(__file__).parent / 'chart.html'
out.write_text(html, encoding='utf-8')
print('图表已生成:', out)
