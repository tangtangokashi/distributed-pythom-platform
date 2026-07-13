from __future__ import annotations

from nicegui import ui

from app.services.deepseek import explain
from app.services.ml import MLService
from app.services.realtime import realtime

NAV = [("总览", "/"), ("金融中心", "/finance"), ("电商中心", "/ecommerce"), ("模型与数据流", "/models"), ("AI 分析助手", "/assistant")]

ui.add_head_html('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
body { min-height:100vh; background:radial-gradient(circle at 14% -10%,#164c6c 0,transparent 30%),radial-gradient(circle at 100% 0,#22245b 0,transparent 30%),#07101d; color:#eef7ff; font-family:Manrope,"Microsoft YaHei",sans-serif; }
body:before { content:""; position:fixed; inset:0; pointer-events:none; opacity:.23; background-image:linear-gradient(rgba(90,170,214,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(90,170,214,.06) 1px,transparent 1px); background-size:38px 38px; mask-image:linear-gradient(to bottom,black,transparent 72%); }
.nicegui-content { max-width:1510px; margin:0 auto; padding:24px 30px 48px; position:relative; }
.topbar { backdrop-filter:blur(20px); background:rgba(10,28,48,.72); border:1px solid rgba(100,186,225,.24); border-radius:20px; padding:12px 16px; box-shadow:0 18px 48px rgba(0,0,0,.25); }
.brand-mark { display:grid; place-items:center; width:42px; height:42px; border-radius:13px; font-family:"DM Mono"; font-weight:700; font-size:13px; color:#dffbff; background:linear-gradient(135deg,#12c6bb,#396cf5); box-shadow:0 8px 24px #10a9bf55; }.title { font-size:18px; font-weight:800; letter-spacing:.2px; }.sub { color:#829cb9; font-size:12px; }.eyebrow { color:#54d8d0; font-family:"DM Mono"; font-size:11px; letter-spacing:1.4px; text-transform:uppercase; }
.live-badge { color:#8effca; background:rgba(22,192,130,.12); border:1px solid rgba(70,224,162,.28); border-radius:99px; padding:6px 10px; font:11px "DM Mono"; }.live-dot { color:#51e3a3; text-shadow:0 0 10px #51e3a3; }
.navlink { color:#8da9c7; text-decoration:none; padding:8px 11px; border-radius:9px; font-size:13px; font-weight:600; transition:.2s; }.navlink:hover { background:#183b59; color:white; }.nav-active { color:#f5fdff; background:linear-gradient(135deg,#1c566f,#293d81); box-shadow:inset 0 0 0 1px #64d8e544; }
.hero { overflow:hidden; position:relative; background:linear-gradient(112deg,rgba(21,74,97,.72),rgba(27,38,100,.62)); border:1px solid rgba(109,210,236,.26); border-radius:20px; padding:24px 26px; box-shadow:0 18px 42px #0003; }.hero:after { content:""; position:absolute; width:260px; height:260px; right:-75px; top:-115px; background:radial-gradient(circle,#42e3de77,transparent 65%); }.hero-title { font-size:28px; line-height:1.25; font-weight:800; letter-spacing:-.5px; }.hero-copy { color:#a5c3db; max-width:670px; font-size:13px; line-height:1.75; }
.metric { position:relative; overflow:hidden; background:linear-gradient(145deg,rgba(17,45,71,.94),rgba(9,23,40,.96)); border:1px solid rgba(89,156,197,.24); border-radius:17px; padding:17px; min-width:185px; flex:1; box-shadow:0 12px 30px #02091444; }.metric:before { content:""; position:absolute; width:120px; height:120px; right:-55px; top:-65px; border-radius:50%; background:#2bd0c416; }.metric-icon { display:grid; place-items:center; width:31px; height:31px; border-radius:10px; background:#37d8c51b; color:#55e5d9; }.metric-label { color:#91adc7; font-size:12px; }.metric-value { font:700 27px "DM Mono",monospace; margin-top:9px; color:#f5fbff; letter-spacing:-1px; }
.panel { background:linear-gradient(145deg,rgba(12,34,55,.92),rgba(8,22,38,.94)); border:1px solid rgba(79,143,182,.25); border-radius:17px; padding:18px; box-shadow:0 12px 32px #02091436; }.panel-title { font-weight:700; font-size:14px; margin-bottom:12px; color:#e8f7ff; }.panel-title:before { content:""; display:inline-block; width:4px; height:15px; vertical-align:-2px; margin-right:8px; border-radius:5px; background:linear-gradient(#4fe1d4,#4383fb); }
.ok { color:#53dfa9; }.warn { color:#ffc46c; }.danger { color:#ff8091; }.muted { color:#8ba8c8; }.feed-row { border-top:1px solid rgba(88,143,177,.18); padding:10px 1px; font-size:12px; }.feed-row:first-child { border-top:0; }.mono { font-family:"DM Mono",monospace; }
.chip { padding:5px 8px; background:#52d5c218; border:1px solid #55e4d335; border-radius:7px; color:#8ff4e9; font:11px "DM Mono"; }.stream-card { background:linear-gradient(135deg,#0d3850,#142e61); }
</style>''')


def shell(active: str):
    with ui.column().classes("w-full gap-5"):
        with ui.row().classes("topbar w-full items-center justify-between"):
            with ui.row().classes("items-center gap-3"):
                ui.label("DIP").classes("brand-mark")
                with ui.column().classes("gap-0"):
                    ui.label("分布式实时智能决策平台").classes("title")
                    ui.label("KAFKA · SPARK · MACHINE LEARNING · DEEPSEEK").classes("sub mono")
            with ui.row().classes("items-center gap-1"):
                for title, path in NAV:
                    ui.link(title, path).classes("navlink" + (" nav-active" if active == path else ""))
                ui.label("● LIVE").classes("live-badge")
        return ui.column().classes("w-full gap-5")


def metric(label: str, value: str, detail: str = "实时更新", icon: str = "insights"):
    with ui.column().classes("metric"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(label).classes("metric-label")
            ui.icon(icon).classes("metric-icon")
        ui.label(value).classes("metric-value")
        ui.label(detail).classes("sub")


def line_options(ticks: list[dict]) -> dict:
    aapl = [x for x in ticks if x["symbol"] == "AAPL"]
    return {"backgroundColor": "transparent", "tooltip": {"trigger": "axis"}, "grid": {"left": 42, "right": 18, "top": 28, "bottom": 30}, "xAxis": {"type": "category", "data": [x["time"] for x in aapl], "axisLabel": {"color": "#8ba8c8"}}, "yAxis": {"type": "value", "scale": True, "axisLabel": {"color": "#8ba8c8"}, "splitLine": {"lineStyle": {"color": "#173550"}}}, "series": [{"name": "AAPL", "type": "line", "smooth": True, "showSymbol": False, "data": [x["price"] for x in aapl], "lineStyle": {"color": "#42d3a4", "width": 3}, "areaStyle": {"color": "rgba(66,211,164,.12)"}}]}


@ui.page("/")
def overview() -> None:
    root = shell("/")
    snapshot = realtime.snapshot()
    with root:
        with ui.row().classes("hero w-full items-center justify-between"):
            with ui.column().classes("gap-2"):
                ui.label("DECISION INTELLIGENCE / LIVE OPS").classes("eyebrow")
                ui.label("实时洞察，让每一次决策\n都有数据依据。 ").classes("hero-title")
                ui.label("跨金融市场与电商订单流，统一呈现实时指标、模型信号和集群健康状态。 ").classes("hero-copy")
                with ui.row().classes("items-center gap-2 mt-2"):
                    ui.label("● 流式引擎运行中").classes("live-badge")
                    ui.label("3 NODES CONNECTED").classes("chip")
            with ui.column().classes("items-end gap-1 z-10"):
                ui.label("PROCESSING LATENCY").classes("eyebrow")
                ui.label("36 ms").classes("text-4xl font-bold mono text-cyan-2")
                ui.label("Spark Structured Streaming").classes("sub")
        with ui.row().classes("w-full gap-4 flex-wrap"):
            order_label = ui.label()
            gmv_label = ui.label()
            user_label = ui.label()
            alert_label = ui.label()
            for label, holder, icon, detail in [("实时订单", order_label, "receipt_long", "Kafka 实时写入"), ("累计 GMV", gmv_label, "payments", "分布式聚合结果"), ("活跃用户", user_label, "group", "RFM 用户画像"), ("风险告警", alert_label, "shield", "Isolation Forest 检测")]:
                with ui.column().classes("metric"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(label).classes("metric-label")
                        ui.icon(icon).classes("metric-icon")
                    holder.classes("metric-value")
                    ui.label(detail).classes("sub")
        with ui.row().classes("w-full gap-5 items-stretch flex-wrap"):
            with ui.column().classes("panel flex-[2] min-w-[560px]"):
                ui.label("AAPL 实时行情").classes("panel-title")
                chart = ui.echart(line_options(snapshot["ticks"])).classes("w-full h-80")
            with ui.column().classes("panel flex-1 min-w-[300px]"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("三节点集群状态").classes("panel-title")
                    ui.label("HEALTHY").classes("chip")
                nodes = ui.column().classes("w-full gap-1")
        with ui.row().classes("w-full gap-5 flex-wrap"):
            with ui.column().classes("panel stream-card flex-1 min-w-[420px]"):
                ui.label("最新告警").classes("panel-title")
                alerts = ui.column().classes("w-full")
            with ui.column().classes("panel flex-1 min-w-[420px]"):
                ui.label("数据流运行指标").classes("panel-title")
                stream_label = ui.label().classes("text-lg")
                running_label = ui.label().classes("sub")
                with ui.row().classes("mt-3"):
                    ui.button("启动回放", icon="play_arrow", on_click=lambda: realtime.start(1)).props("color=positive unelevated")
                    ui.button("暂停", icon="pause", on_click=realtime.stop).props("outline color=warning")
                    ui.button("单步推进", icon="skip_next", on_click=realtime.emit_once).props("outline")

        def refresh() -> None:
            data = realtime.snapshot()
            kpis = data["kpis"]
            order_label.set_text(str(kpis["orders"]))
            gmv_label.set_text(f"¥ {kpis['gmv']:,.0f}")
            user_label.set_text(str(kpis["active_users"]))
            alert_label.set_text(str(kpis["alerts"]))
            chart.options.clear()
            chart.options.update(line_options(data["ticks"]))
            chart.update()
            nodes.clear()
            with nodes:
                for item in data["nodes"]:
                    with ui.row().classes("w-full items-center justify-between feed-row"):
                        ui.label(f"● {item['name']}").classes("ok")
                        ui.label(item["role"]).classes("sub")
            alerts.clear()
            with alerts:
                for item in data["alerts"][:5]:
                    css = "danger" if item["severity"] == "高" else "warn"
                    ui.label(f"[{item['time']}] {item['title']} — {item['detail']}").classes(f"feed-row {css}")
                if not data["alerts"]:
                    ui.label("暂无异常，系统正在持续监测。 ").classes("muted")
            stream_label.set_text(f"Kafka 已接收 {data['stream']['kafka_messages']} 条消息 · Spark 批处理延迟 {data['stream']['spark_latency']} ms")
            running_label.set_text("● 回放器运行中" if data["running"] else "● 回放器已暂停")

        refresh()
        ui.timer(1.5, refresh)


@ui.page("/finance")
def finance_page() -> None:
    root = shell("/finance")
    with root:
        with ui.row().classes("w-full items-end justify-between"):
            with ui.column().classes("gap-1"):
                ui.label("FINANCE RISK MONITOR").classes("eyebrow")
                ui.label("金融风险中心").classes("text-3xl font-bold")
                ui.label("实时行情、短期预测与机器学习风险信号。 ").classes("muted")
            ui.label("● MARKET STREAM LIVE").classes("live-badge")
        chart = ui.echart(line_options(realtime.snapshot()["ticks"])).classes("panel w-full h-96")
        cards = ui.row().classes("w-full gap-4 flex-wrap")
        alerts = ui.column().classes("panel w-full")

        def refresh() -> None:
            data = realtime.snapshot()
            chart.options.clear()
            chart.options.update(line_options(data["ticks"]))
            chart.update()
            cards.clear(); alerts.clear()
            latest = {s: next((x for x in reversed(data["ticks"]) if x["symbol"] == s), None) for s in realtime.symbols}
            with cards:
                for symbol, tick in latest.items():
                    if tick:
                        forecast = realtime.ml.forecast(realtime.tick_count + 1, tick["price"])
                        with ui.column().classes("metric"):
                            ui.label(symbol).classes("metric-label")
                            ui.label(f"${tick['price']:.2f}").classes("metric-value")
                            ui.label(f"预测 ${forecast:.2f} · 涨跌 {tick['change_pct']:+.2f}%").classes("sub")
            with alerts:
                ui.label("风险预警（Isolation Forest + 波动率规则）").classes("panel-title")
                for alert in [a for a in data["alerts"] if a["domain"] == "finance"]:
                    ui.label(f"{alert['time']} · {alert['title']} · {alert['detail']}").classes("feed-row danger")
        refresh(); ui.timer(1.5, refresh)


@ui.page("/ecommerce")
def ecommerce_page() -> None:
    root = shell("/ecommerce")
    with root:
        with ui.row().classes("w-full items-end justify-between"):
            with ui.column().classes("gap-1"):
                ui.label("COMMERCE OPERATIONS").classes("eyebrow")
                ui.label("电商运营中心").classes("text-3xl font-bold")
                ui.label("实时订单、异常风控、用户分群和商品推荐。 ").classes("muted")
            ui.label("● ORDER EVENTS LIVE").classes("live-badge")
        with ui.row().classes("w-full gap-5 flex-wrap"):
            orders = ui.column().classes("panel flex-[2] min-w-[560px]")
            recommend = ui.column().classes("panel flex-1 min-w-[330px]")

        def refresh() -> None:
            data = realtime.snapshot()
            orders.clear(); recommend.clear()
            with orders:
                ui.label("实时订单流 · Isolation Forest 风控").classes("panel-title")
                for order in data["orders_feed"][:10]:
                    flag = "  ⚠ 异常" if order["is_anomaly"] else ""
                    ui.label(f"{order['time']}  {order['order_code']}  {order['product']}  ¥{order['amount']:,.2f}  {order['region']}{flag}").classes("feed-row " + ("danger" if order["is_anomaly"] else ""))
            with recommend:
                ui.label("用户分群与推荐（K-Means / ALS）").classes("panel-title")
                for user, spend, count in [("U1012", 1680, 8), ("U1048", 590, 4), ("U1090", 2890, 13)]:
                    ui.label(f"{user} · {realtime.ml.segment(spend, count)}").classes("feed-row ok")
                    ui.label("推荐：无线耳机、智能手表、咖啡机").classes("sub")
        refresh(); ui.timer(1.5, refresh)


@ui.page("/models")
def models_page() -> None:
    root = shell("/models")
    with root:
        ui.label("MODEL REGISTRY & DATA PIPELINE").classes("eyebrow")
        ui.label("模型与数据流管理").classes("text-3xl font-bold")
        with ui.row().classes("w-full gap-4 flex-wrap"):
            for model in MLService.catalogue():
                with ui.column().classes("metric"):
                    ui.label(model["name"]).classes("metric-label")
                    ui.label(model["status"]).classes("metric-value " + ("ok" if model["status"] == "在线" else "warn"))
                    ui.label(model["purpose"]).classes("sub")
                    ui.label(model["metric"]).classes("sub")
        ui.label("生产环境中，训练任务由 Spark MLlib / PySpark 提交至主节点，模型文件写入 MinIO，并由计算节点完成在线推理。").classes("panel muted")


@ui.page("/assistant")
def assistant_page() -> None:
    root = shell("/assistant")
    with root:
        ui.label("AI INSIGHT COPILOT").classes("eyebrow")
        ui.label("DeepSeek 智能分析助手").classes("text-3xl font-bold")
        ui.label("只提交经过后端聚合的指标摘要，不发送原始订单或用户隐私数据。现在由 DeepSeek 提供解释。 ").classes("muted")
        question = ui.textarea(label="向平台提问", placeholder="例如：为什么刚才 AAPL 的风险升高？").classes("w-full")
        answer = ui.markdown("等待问题…").classes("panel w-full")

        async def ask() -> None:
            text = question.value.strip()
            if not text:
                ui.notify("请输入问题", type="warning"); return
            answer.set_content("正在分析…")
            snapshot = realtime.snapshot()
            result = await explain(f"问题：{text}。指标：订单 {snapshot['kpis']['orders']}，GMV {snapshot['kpis']['gmv']}，告警 {snapshot['kpis']['alerts']}。")
            answer.set_content(f"**{result['source']}**\n\n{result['answer']}")
        ui.button("生成分析", on_click=ask).props("color=primary")
