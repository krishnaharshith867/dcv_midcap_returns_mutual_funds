"""Mid-Cap Mutual Funds dashboard (generated from the notebook). Run: gunicorn app:server"""
# ======================================================================
# Notebook cell 2
# ======================================================================
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, ctx
import dash_bootstrap_components as dbc
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data_collection' / 'clean'


# ======================================================================
# Notebook cell 4
# ======================================================================
nav = pd.read_parquet(DATA_DIR / 'nav_midcap_clean.parquet')
ter = pd.read_parquet(DATA_DIR / 'ter_midcap_clean.parquet')

# ---------------------------------------------------------------------------
# "Ledger Dark" palette: one set of colours for all seven dashboards.
# Each colour has ONE job, so a colour always means the same thing on every page.
# ---------------------------------------------------------------------------
BG = "#060A12"          # page: ink navy-black (never pure black, so cards can float above it)
CARDS = "#0F1624"       # card surface and chart outlines
SURFACE_HI = "#16213A"  # raised surfaces: tooltips, selectors, callouts
BORDER = "#222F48"      # card borders, axis lines
GRID = "#1A2438"        # chart gridlines (very quiet)
TEXT = "#E8EEF7"        # primary text (soft white, ~15:1 contrast on cards)
MUTED = "#93A4BD"       # secondary text (~7:1 on cards)

DIRECT = "#2DD4BF"      # Direct plan: teal. Teal vs amber stays distinguishable for colour-blind readers
REGULAR = "#F5A83C"     # Regular plan: amber, the "commission" colour
COUNT = "#A594FF"       # accent: gap, trend, selected item, interactive controls (periwinkle violet)
SKY = "#5AB0FF"         # cheapest funds
RED = "#F26B7E"         # negative values, costliest funds, drawdowns
POS = "#34D399"         # positive values (heatmap, good scores)
AMBER = "#F5C451"       # caution / middle of a good-bad scale
TEAL = "#4CC9C0"        # secondary comparison accent
SLATE = "#5E6F8A"       # neutral: middle group, peers
ACCENT = COUNT
THEME = dbc.themes.CYBORG

print(f"TER rows {len(ter):,} ({ter['MF_ID'].nunique()} funds)  |  NAV rows {len(nav):,} ({nav['MF_ID'].nunique()} funds)")

# ---- one app for all seven dashboards (the top bar switches between them) ----
app = Dash(__name__, external_stylesheets=[THEME], suppress_callback_exceptions=True,
           title="Mid-Cap Mutual Funds · The Cost of Investing",
           meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
server = app.server      # exposes the Flask server so gunicorn can serve it (gunicorn <module>:server)


# ======================================================================
# Notebook cell 6
# ======================================================================
ter = ter[ter["MF_ID"].isin(nav["MF_ID"].unique())].copy()
companies = (nav.drop_duplicates(subset=["MF_ID"])[["MF_ID","Mutual_Fund_Company"]].assign(COMPANY=lambda x: x["Mutual_Fund_Company"].str.replace("Mutual Fund","",regex=False).str.strip()))


# ======================================================================
# Notebook cell 8
# ======================================================================
# ---------- numbers for the overview ----------
latest = (ter.dropna(subset=["R_TER", "D_TER"]).sort_values("Date").groupby("MF_ID").tail(1))
n_funds = nav["MF_ID"].nunique()
n_rows  = len(nav)
years   = (nav["Date"].max() - nav["Date"].min()).days / 365.25
avg_r, avg_d = latest["R_TER"].mean(), latest["D_TER"].mean()
avg_gap = (latest["R_TER"] - latest["D_TER"]).mean()

# one row per fund COMPANY: first NAV date, last NAV date
span = (nav.groupby("MF_ID")["Date"].agg(start="min", end="max").reset_index().merge(companies, on="MF_ID"))
span["years_of_history"] = (span["end"] - span["start"]).dt.days / 365.25
span["month"] = span["start"].dt.to_period("M").dt.to_timestamp()

# how many fund companies have a NAV in each month, and who joined that month
active = (nav.groupby(nav["Date"].dt.to_period("M"))["MF_ID"].nunique().rename("funds").reset_index())
active["Date"] = active["Date"].dt.to_timestamp()
joined = span.groupby("month")["COMPANY"].apply(lambda s: "<br>".join("• " + h for h in sorted(s)))
active["note"] = [("Joined:<br>" + joined[d]) if d in joined.index else "" for d in active["Date"]]

first_n, last_n = int(active["funds"].iloc[0]), int(active["funds"].iloc[-1])
active.loc[0, "note"] = f"{first_n} companies were already in the data"

newcomers = span[span["start"] > nav["Date"].min()]              # not the day-one group
busiest_year  = int(newcomers["start"].dt.year.value_counts().idxmax())
busiest_count = int(newcomers["start"].dt.year.value_counts().max())
newest = span.sort_values("start").iloc[-1]

COMPANY_options = [{"label": h, "value": str(i)}
                 for i, h in sorted(zip(companies["MF_ID"], companies["COMPANY"]), key=lambda x: x[1].lower())]
default_id = int(next((o["value"] for o in COMPANY_options if o["label"] == "HDFC"), COMPANY_options[0]["value"]))


# ======================================================================
# Notebook cell 9
# ======================================================================
# ---------- helpers ----------
FONT = "Inter, 'Segoe UI', system-ui, -apple-system, sans-serif"
GRAPH = {"displayModeBar": False, "responsive": True}

def rgba(hex_colour, alpha):
    h = hex_colour.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"

def style_fig(fig, height=380):
    """One look for every chart: transparent canvas (the card shows through), quiet grid, tidy hover."""
    m = dict(l=56, r=28, t=44, b=48)
    for k in ("l", "r"):                              # keep a wider margin a chart asked for (end labels)
        v = fig.layout.margin[k]
        if v is not None:
            m[k] = v
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(text=""),                          # the card header carries the chart title
        font=dict(family=FONT, color=TEXT, size=12.5),
        height=height,
        margin=m,
        colorway=[DIRECT, REGULAR, COUNT, SKY, RED, AMBER, SLATE],
        hoverlabel=dict(bgcolor=SURFACE_HI, bordercolor=BORDER, font=dict(family=FONT, color=TEXT, size=13)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED, size=12), title=dict(text="")),
    )
    horiz = any(getattr(t, "type", None) == "bar" and getattr(t, "orientation", None) == "h" for t in fig.data)
    fig.update_xaxes(showgrid=horiz, gridcolor=GRID, gridwidth=1, griddash="dot", zeroline=False,       # horizontal bars: grid on the value axis
                     linecolor=BORDER, ticks="outside", tickcolor=BORDER,
                     tickfont=dict(color=MUTED, size=12), title_font=dict(color=MUTED, size=12), automargin=True)
    fig.update_yaxes(showgrid=not horiz, gridcolor=GRID, gridwidth=1, griddash="dot", zeroline=False,
                     linecolor="rgba(0,0,0,0)", tickfont=dict(color=MUTED, size=12),
                     title_font=dict(color=MUTED, size=12), automargin=True)
    fig.update_coloraxes(colorbar=dict(outlinewidth=0, tickfont=dict(color=MUTED), title=dict(font=dict(color=MUTED))))
    return fig

def add_range_selector(fig):
    """1Y / 3Y / 5Y / All buttons for long date axes."""
    fig.update_xaxes(rangeselector=dict(
        buttons=[dict(count=1, label="1Y", step="year", stepmode="backward"),
                 dict(count=3, label="3Y", step="year", stepmode="backward"),
                 dict(count=5, label="5Y", step="year", stepmode="backward"),
                 dict(step="all", label="All")],
        bgcolor=SURFACE_HI, activecolor=ACCENT, bordercolor=BORDER, borderwidth=1,
        font=dict(color=TEXT, size=11), x=1, xanchor="right", y=1.0, yanchor="bottom"))
    return fig

def graph(fig, height=380, **kw):
    return dcc.Graph(figure=style_fig(fig, height), config=GRAPH, style={"width": "100%"}, **kw)

def kpi(label, value, color=None, sub=None):
    """KPI tile: thin accent bar on top, small caps label, big tabular number, quiet footnote."""
    accent = color or ACCENT
    body = [html.Div(style={"background": f"linear-gradient(90deg,{accent},transparent)"}, className="kpi-bar"),
            html.Div(label, className="kpi-label"),
            html.Div(value, className="kpi-value", style={"color": color} if color else {})]
    if sub:
        body.append(html.Div(sub, className="kpi-sub"))
    return dbc.Card(dbc.CardBody(body), className="h-100 kpi-card")

def kpi_two(label, d_val, r_val, sub=None):
    """A tile that shows the Direct and Regular value on two lines."""
    line = lambda name, val, col: html.Div([html.Span(name, className="kpi-row-name"),
                                            html.Span(val, className="kpi-row-val", style={"color": col})],
                                           className="kpi-row")
    body = [html.Div(style={"background": f"linear-gradient(90deg,{DIRECT},{REGULAR})"}, className="kpi-bar"),
            html.Div(label, className="kpi-label"), line("Direct", d_val, DIRECT), line("Regular", r_val, REGULAR)]
    if sub:
        body.append(html.Div(sub, className="kpi-sub"))
    return dbc.Card(dbc.CardBody(body), className="h-100 kpi-card")

def chart_card(title, subtitle, content):
    return dbc.Card(dbc.CardBody([html.Div([html.H5(title, className="card-title-x"),
                                            html.Div(subtitle, className="card-sub")], className="card-head"),
                                  content]), className="h-100 chart-card")

def page_header(title, subtitle):
    """Same heading block on every dashboard: eyebrow (n of 7), title, one-line question."""
    eyebrow = None
    if subtitle.startswith("Dashboard") and " · " in subtitle:
        eyebrow, subtitle = subtitle.split(" · ", 1)
        eyebrow = eyebrow.upper() + " OF 7"
    if title.startswith("Mid-Cap Mutual Funds: "):
        title = title[len("Mid-Cap Mutual Funds: "):]
    return html.Div([html.Div(eyebrow, className="eyebrow") if eyebrow else None,
                     html.H1(title, className="page-title"),
                     html.P(subtitle, className="page-sub")], className="page-header")

def control_bar(children):
    """The row of pickers (dropdowns, pills) at the top of a dashboard, in one framed bar."""
    return html.Div(dbc.Row(children, className="align-items-end"), className="control-bar")

fmt = lambda x, f: "n/a" if pd.isna(x) else format(x, f)

# ---------- chart 1: how many fund COMPANYs over time ----------
ends = active.iloc[[0, -1]]
fig_active = go.Figure()
fig_active.add_trace(go.Scatter(
    x=active["Date"], y=active["funds"], mode="lines",
    line=dict(color=COUNT, width=3, shape="hv"),
    fill="tozeroy", fillcolor=rgba(COUNT, 0.16),
    customdata=active["note"],
    hovertemplate="<b>%{y} fund companies</b> · %{x|%b %Y}<br>%{customdata}<extra></extra>"))
fig_active.add_trace(go.Scatter(                   # direct labels on the first and last point
    x=ends["Date"], y=ends["funds"], mode="markers+text", text=ends["funds"].astype(str),
    textposition="top center", textfont=dict(color=COUNT, size=18),
    marker=dict(color=COUNT, size=10), hoverinfo="skip", showlegend=False))
fig_active.update_yaxes(range=[0, last_n * 1.25], dtick=10)
fig_active.update_layout(showlegend=False)

# ---------- the TER chart: monthly average, lightly smoothed, labelled directly ----------
def make_ter_fig(t):
    fig = go.Figure()
    tm = (t.set_index("Date")[["D_TER", "R_TER"]].resample("MS").mean()
            .dropna(how="all").rolling(3, min_periods=1).mean())
    both = tm.dropna()
    if both.empty:                                   # a COMPANY with no TER data
        fig.add_annotation(text="No TER data for this COMPANY", showarrow=False,
                           font=dict(color=MUTED, size=14))
        return fig

    last = both.iloc[-1]
    last_x = both.index[-1]
    gap_now = last["R_TER"] - last["D_TER"]

    fig.add_trace(go.Scatter(x=tm.index, y=tm["D_TER"], name="Direct",
                             line=dict(color=DIRECT, width=3, shape="spline", smoothing=0.6),
                             hovertemplate="%{y:.2f}%"))
    fig.add_trace(go.Scatter(x=tm.index, y=tm["R_TER"], name="Regular",
                             line=dict(color=REGULAR, width=3, shape="spline", smoothing=0.6),
                             fill="tonexty", fillcolor=rgba(REGULAR, 0.14),
                             hovertemplate="%{y:.2f}%"))
    # direct labels at the end of each line; cliponaxis=False lets them sit outside the plot area
    for name, col, val in [("Regular", REGULAR, last["R_TER"]), ("Direct", DIRECT, last["D_TER"])]:
        fig.add_trace(go.Scatter(x=[last_x], y=[val], mode="markers+text",
                                 text=[f"  {name} {val:.2f}%"], textposition="middle right",
                                 textfont=dict(color=col, size=13), marker=dict(color=col, size=9),
                                 cliponaxis=False, hoverinfo="skip", showlegend=False))
    fig.add_annotation(x=last_x, y=(last["R_TER"] + last["D_TER"]) / 2,
                       text=f"  gap {gap_now:.2f} pp", showarrow=False, xanchor="left",
                       font=dict(color=MUTED, size=12))

    fig.update_layout(hovermode="x unified", showlegend=False, margin=dict(r=150))
    fig.update_xaxes(range=[tm.index[0], last_x])    # stop the axis at the last data point (no empty 2028)
    fig.update_yaxes(ticksuffix="%", tickformat=".1f", rangemode="tozero")
    return fig

# ---------- the profile of one fund COMPANY ----------
def profile(mf_id):
    n = nav[nav["MF_ID"] == mf_id].dropna(subset=["NAV"]).sort_values("Date")
    t = ter[ter["MF_ID"] == mf_id].sort_values("Date")
    COMPANY = companies.loc[companies["MF_ID"] == mf_id, "COMPANY"].iloc[0]
    scheme = t["scheme_label"].iloc[-1] if ("scheme_label" in t and len(t)) else ""
    sp = span[span["MF_ID"] == mf_id].iloc[0]

    def nav_stats(plan):
        s = n.loc[n["Plan"] == plan, "NAV"]
        if s.empty: return dict(start=np.nan, now=np.nan, avg=np.nan, chg=np.nan)
        return dict(start=s.iloc[0], now=s.iloc[-1], avg=s.mean(), chg=(s.iloc[-1] / s.iloc[0] - 1) * 100)

    def ter_stats(col):
        s = t[col].dropna()
        if s.empty: return dict(start=np.nan, now=np.nan, avg=np.nan, lo=np.nan, hi=np.nan)
        return dict(start=s.iloc[0], now=s.iloc[-1], avg=s.mean(), lo=s.min(), hi=s.max())

    nd, nr = nav_stats("Direct Plan"), nav_stats("Regular Plan")
    td, tr_ = ter_stats("D_TER"), ter_stats("R_TER")

    title = html.Div([html.H3(COMPANY, className="mb-0"), html.Span(scheme, className="text-muted")], className="mt-1")

    cards = dbc.Row([
        dbc.Col(kpi("In our data since", f"{sp['start']:%d %b %Y}", sub=f"{sp['years_of_history']:.1f} years of history"), xs=12, sm=6, xl=3),
        dbc.Col(kpi_two("NAV Today (₹ per unit)", fmt(nd["now"], ",.2f"), fmt(nr["now"], ",.2f"), f"as of {n['Date'].max():%d %b %Y}"), xs=12, sm=6, xl=3),
        dbc.Col(kpi_two("TER Today (% a year)", fmt(td["now"], ".2f") + "%", fmt(tr_["now"], ".2f") + "%",
                        f"gap {fmt(tr_['now'] - td['now'], '.2f')} pp"), xs=12, sm=6, xl=3),
        dbc.Col(kpi_two("Average TER", fmt(td["avg"], ".2f") + "%", fmt(tr_["avg"], ".2f") + "%", "over its whole history"), xs=12, sm=6, xl=3),
    ], className="mb-3")

    # NAV chart
    fig_nav = go.Figure()
    for plan, col in [("Direct Plan", DIRECT), ("Regular Plan", REGULAR)]:
        s = n[n["Plan"] == plan]
        fig_nav.add_trace(go.Scatter(x=s["Date"], y=s["NAV"], name=plan.replace(" Plan", ""),
                                     line=dict(color=col, width=2), hovertemplate="%{y:,.2f}"))
    fig_nav.update_layout(hovermode="x unified")
    add_range_selector(fig_nav)
    fig_nav.update_yaxes(title_text="NAV (₹)")

    # TER chart (new)
    fig_ter = make_ter_fig(t)

    # numbers table (color="dark" removed so the theme styles it)
    rows = [("NAV at start (₹)",      fmt(nd["start"], ",.2f"), fmt(nr["start"], ",.2f")),
            ("NAV now (₹)",           fmt(nd["now"], ",.2f"),   fmt(nr["now"], ",.2f")),
            ("NAV change since start", fmt(nd["chg"], "+,.0f") + "%", fmt(nr["chg"], "+,.0f") + "%"),
            ("Average NAV (₹)",       fmt(nd["avg"], ",.2f"),   fmt(nr["avg"], ",.2f")),
            ("TER at start",          fmt(td["start"], ".2f") + "%", fmt(tr_["start"], ".2f") + "%"),
            ("TER now",               fmt(td["now"], ".2f") + "%",   fmt(tr_["now"], ".2f") + "%"),
            ("Average TER",           fmt(td["avg"], ".2f") + "%",   fmt(tr_["avg"], ".2f") + "%"),
            ("TER lowest to highest", f"{fmt(td['lo'], '.2f')}% to {fmt(td['hi'], '.2f')}%",
                                      f"{fmt(tr_['lo'], '.2f')}% to {fmt(tr_['hi'], '.2f')}%")]
    table = dbc.Table([
        html.Thead(html.Tr([html.Th(""), html.Th("Direct", style={"color": DIRECT}), html.Th("Regular", style={"color": REGULAR})])),
        html.Tbody([html.Tr([html.Td(a, className="text-muted"), html.Td(b), html.Td(c)]) for a, b, c in rows])],
        hover=True, className="mb-0")
    return title, cards, fig_nav, fig_ter, table


# ======================================================================
# Notebook cell 10
# ======================================================================
title0, cards0, fig_nav0, fig_ter0, table0 = profile(default_id)     # first view is drawn without a callback

def page1():
  return html.Div([
    # ---- header ----
    page_header("Mid-Cap Mutual Funds: Market Landscape & Growth",
                f"Dashboard 1 · Fund houses grew from {first_n} in {nav['Date'].min().year} to {last_n} in {nav['Date'].max().year}."),

    # ---- overview KPIs (2+2+2+2+2+2) ----
    dbc.Row([
        dbc.Col(kpi("Mutual Fund Companies", f"{n_funds}"), xs=6, md=4, xl=2),
        dbc.Col(kpi("NAV Observations", f"{n_rows:,}"), xs=6, md=4, xl=2),
        dbc.Col(kpi("Years of data", f"{years:.1f}"), xs=6, md=4, xl=2),
        dbc.Col(kpi("Avg Regular plan TER", f"{avg_r:.2f}%", REGULAR), xs=6, md=4, xl=2),
        dbc.Col(kpi("Avg Direct plan TER", f"{avg_d:.2f}%", DIRECT), xs=6, md=4, xl=2),
        dbc.Col(kpi("Avg TER  gap", f"{avg_gap:.2f} pp"), xs=6, md=4, xl=2),
    ], className="mb-4"),

    # ---- how many funds over time (8 + 4) ----
    dbc.Row([
        dbc.Col(chart_card("Growth in number of midcap mutual fund companies",
                           f"Grew from {first_n} to {last_n}. Hover a step to see who joined.",
                           graph(fig_active, 340)), xs=12, lg=8),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Insights"),
            dcc.Markdown(f"""
- **{first_n}** Companies were there on the first day. Now there are **{last_n}** (**+{last_n - first_n}**).
- **{busiest_year}** is the year with the most new Companies (**{busiest_count}** companies started).
- The newest among them is **{newest['COMPANY']}**, first seen {newest['start']:%d %b %Y}.
- Younger funds have less history, so later dashboards compare funds on **common time windows**.
            """)]), className="h-100"), xs=12, lg=4),
    ], className="mb-4"),

    # ---- fund COMPANY explorer ----
    control_bar([
        dbc.Col([html.H4("Explore a fund COMPANY", className="mb-0"),
                 html.Small("Pick a company to see when it started, its NAV and TER, now and on average.", className="text-muted")], md=8),
        dbc.Col(dcc.Dropdown(id="COMPANY-select", options=COMPANY_options, value=str(default_id), clearable=False), md=4),
    ]),

    dbc.Row(dbc.Col(html.Div(title0, id="COMPANY-title"), width=12), className="mb-1"),
    html.Div(cards0, id="COMPANY-cards"),

    dbc.Row([
        dbc.Col(chart_card("NAV over time", "Price of one unit. Use the 1Y / 3Y / 5Y buttons to zoom. Direct sits slightly above Regular.",
                           dcc.Graph(id="nav-graph", figure=style_fig(fig_nav0, 340), config={"displayModeBar": False})), xs=12, lg=6),
        dbc.Col(chart_card("TER over time", "Yearly fee. The shaded gap is what the distributor's commission costs.",
                           dcc.Graph(id="ter-graph", figure=style_fig(fig_ter0, 340), config={"displayModeBar": False})), xs=12, lg=6),
    ], className="mb-4"),

    dbc.Row(dbc.Col(chart_card("The numbers behind the charts", "Direct vs Regular for this Company", html.Div(table0, id="COMPANY-table")), width=12),
            className="mb-5"),
])

# one input -> five outputs (his "Pattern 3")
@app.callback(Output("COMPANY-title", "children"), Output("COMPANY-cards", "children"),
              Output("nav-graph", "figure"), Output("ter-graph", "figure"), Output("COMPANY-table", "children"),
              Input("COMPANY-select", "value"))
def update_COMPANY(value):
    title, cards, f_nav, f_ter, table = profile(int(value))
    return title, cards, style_fig(f_nav, 340), style_fig(f_ter, 340), table


# ======================================================================
# Notebook cell 12
# ======================================================================
# ---------- Dashboard 2: what does the commission cost? ----------
GAP = COUNT

# Keep one row per fund company per date, with total and component gaps
t2 = ter.dropna(subset=["R_TER", "D_TER"]).drop(columns=["COMPANY"], errors="ignore").copy()
t2 = t2.merge(companies[["MF_ID", "COMPANY"]], on="MF_ID").sort_values("Date")
t2["gap"] = t2["R_TER"] - t2["D_TER"]
t2["base_gap"] = t2["R_BaseTER"] - t2["D_BaseTER"]
t2["gst_gap"] = t2["R_GST"] - t2["D_GST"]
t2["year"] = t2["Date"].dt.year
t2["month"] = t2["Date"].dt.to_period("M").dt.to_timestamp()

# ---------- KPI numbers: latest reading of each company ----------
now2 = t2.groupby("MF_ID").tail(1)
first2 = t2.groupby("MF_ID").head(1)
avg_gap2 = now2["gap"].mean()
share = avg_gap2 / now2["R_TER"].mean() * 100
widest = now2.loc[now2["gap"].idxmax()]
narrowest = now2.loc[now2["gap"].idxmin()]
n_narrowed = int((now2.set_index("MF_ID")["gap"].sort_index() < first2.set_index("MF_ID")["gap"].sort_index()).sum())
n_total = len(now2)

# ---------- Two interactive fee-component trend charts ----------
# Each chart compares Regular vs Direct on the same date axis and same y-scale.
fee_monthly = (t2.groupby("month")[["R_BaseTER", "D_BaseTER", "R_GST", "D_GST"]]
                 .median().reset_index())

def paired_fee_fig(regular_col, direct_col, title, y_title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fee_monthly["month"], y=fee_monthly[regular_col],
        name="Regular", mode="lines",
        line=dict(color=REGULAR, width=3),
        hovertemplate="Regular: %{y:.3f}%<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=fee_monthly["month"], y=fee_monthly[direct_col],
        name="Direct", mode="lines",
        line=dict(color=DIRECT, width=3), fill="tonexty", fillcolor=rgba(REGULAR, 0.12),
        hovertemplate="Direct: %{y:.3f}%<extra></extra>"))
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text=y_title, ticksuffix="%", rangemode="tozero")
    return style_fig(fig, 390)

fig_base_pair = paired_fee_fig("R_BaseTER", "D_BaseTER",
                               "Base TER · Regular vs Direct", "Base TER rate (%)")
fig_gst_pair = paired_fee_fig("R_GST", "D_GST",
                              "GST component · Regular vs Direct", "GST rate (%)")

# ---------- Total commission gap trend ----------
by_month = t2.groupby(["MF_ID", "month"])["gap"].mean().reset_index()
monthly = by_month.groupby("month")["gap"].agg(["median", "count"]).reset_index()
monthly = monthly[monthly["count"] >= 5]
fig_gap = go.Figure()
fig_gap.add_trace(go.Scatter(
    x=monthly["month"], y=monthly["median"], mode="lines",
    name="Median total gap", line=dict(color=COUNT, width=3),
    fill="tozeroy", fillcolor=rgba(COUNT, 0.14),
    hovertemplate="%{x|%b %Y}<br>Gap: %{y:.2f} pp<extra></extra>"))
fig_gap.add_trace(go.Scatter(                       # label the latest reading
    x=[monthly["month"].iloc[-1]], y=[monthly["median"].iloc[-1]], mode="markers+text",
    text=[f"  {monthly['median'].iloc[-1]:.2f} pp"], textposition="middle right",
    textfont=dict(color=COUNT, size=13), marker=dict(color=COUNT, size=9),
    cliponaxis=False, hoverinfo="skip", showlegend=False))
fig_gap.update_layout(hovermode="x unified", showlegend=False, margin=dict(r=90))
fig_gap.update_xaxes(title_text="Date")
fig_gap.update_yaxes(title_text="Gap (percentage points)", rangemode="tozero")
fig_gap = style_fig(fig_gap, 390)

# ---------- Total gap by fund company, selectable year ----------
year_gap = t2.groupby(["COMPANY", "year"])["gap"].mean().reset_index()
y0, y1 = int(year_gap["year"].min()), int(year_gap["year"].max())
gmax = year_gap["gap"].max()

def rank_fig(year):
    d = year_gap[year_gap["year"] == year].sort_values("gap")
    fig = px.bar(d, x="gap", y="COMPANY", orientation="h", text_auto=".2f",
                 color_discrete_sequence=[GAP])
    fig.update_traces(textposition="outside", cliponaxis=False, marker_line_width=0,
                      textfont=dict(color=TEXT, size=11))
    avg_gap_y = d["gap"].mean()
    fig.add_vline(x=avg_gap_y, line=dict(color=MUTED, dash="dot", width=1))
    fig.add_annotation(xref="paper", yref="paper", x=1, y=0.02, xanchor="right", yanchor="bottom", showarrow=False,
                       align="right", font=dict(color=ACCENT, size=22),
                       text=f"<b>{year}</b><br><span style='font-size:12px;color:{MUTED}'>dotted line = average {avg_gap_y:.2f} pp</span>")
    fig.update_xaxes(range=[0, gmax * 1.15], title_text="Gap (percentage points)")
    fig.update_yaxes(title_text="")
    return style_fig(fig, max(420, 26 * len(d) + 60))

# ---------- Investment cost calculator ----------
def calc(amount, n_years, gross):
    rows = []
    for y in range(n_years + 1):
        rows.append({"Year": y, "Plan": "Direct", "Value": amount * (1 + (gross - avg_d) / 100) ** y})
        rows.append({"Year": y, "Plan": "Regular", "Value": amount * (1 + (gross - avg_r) / 100) ** y})
    d = pd.DataFrame(rows)
    dd, rr = d[d["Plan"] == "Direct"], d[d["Plan"] == "Regular"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rr["Year"], y=rr["Value"], name="Regular", mode="lines",
                             line=dict(color=REGULAR, width=3), hovertemplate="Regular: ₹%{y:.1f} lakh<extra></extra>"))
    fig.add_trace(go.Scatter(x=dd["Year"], y=dd["Value"], name="Direct", mode="lines",
                             line=dict(color=DIRECT, width=3), fill="tonexty", fillcolor=rgba(DIRECT, 0.13),
                             hovertemplate="Direct: ₹%{y:.1f} lakh<extra></extra>"))
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title_text="Years invested")
    fig.update_yaxes(title_text="Value (₹ lakh)", rangemode="tozero")
    direct = d[(d["Plan"] == "Direct") & (d["Year"] == n_years)]["Value"].iloc[0]
    regular = d[(d["Plan"] == "Regular") & (d["Year"] == n_years)]["Value"].iloc[0]
    for lab, val, col in [("Direct", direct, DIRECT), ("Regular", regular, REGULAR)]:     # name each line at its end
        fig.add_annotation(x=n_years, y=val, text=f"{lab} ₹{val:.1f}", showarrow=False, xanchor="left", xshift=8,
                           yshift=(9 if direct > regular else -9) if lab == "Direct" else (-9 if direct > regular else 9),
                           font=dict(color=col, size=13))
    text = (f"On **₹{amount} lakh** at **{gross}%** a year before costs, after **{n_years} years**, "
            f"Direct is worth **₹{direct:.1f} lakh** and Regular **₹{regular:.1f} lakh**. "
            f"The estimated cost difference is **₹{direct - regular:.1f} lakh**.")
    fig = style_fig(fig, 340)
    fig.update_layout(margin=dict(r=120))
    return fig, text


# ======================================================================
# Notebook cell 13
# ======================================================================
fig_calc0, text_calc0 = calc(10, 15, 12)

# Readable slider labels
def grey(values):
    return {v: {"label": str(v), "style": {"color": MUTED}} for v in values}

def page2():
  return html.Div([
    page_header("Mid-Cap Mutual Funds: The Cost of Investing",
                "Dashboard 2 · How do Direct and Regular plan charges differ?") ,

    dbc.Row([
        dbc.Col(kpi("Average total gap today", f"{avg_gap2:.2f} pp", GAP, "Regular TER − Direct TER"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Commission share", f"{share:.0f}%", REGULAR, "of the Regular TER"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Widest company gap", f"{widest['gap']:.2f} pp", RED, widest["COMPANY"]), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Narrowest company gap", f"{narrowest['gap']:.2f} pp", DIRECT, narrowest["COMPANY"]), xs=12, sm=6, xl=3),
    ], className="mb-4"),

    # Two paired interactive charts; legend clicks toggle each plan.
    dbc.Row([
        dbc.Col(chart_card("Base TER: Regular vs Direct",
                           "Monthly median base TER across fund companies. Toggle either line from the legend.",
                           dcc.Graph(figure=fig_base_pair, config={"displayModeBar": False})), xs=12, lg=6),
        dbc.Col(chart_card("GST: Regular vs Direct",
                           "Monthly median GST component across fund companies. Both plans share one scale.",
                           dcc.Graph(figure=fig_gst_pair, config={"displayModeBar": False})), xs=12, lg=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(chart_card("How the total gap changes over time",
                           "Median Regular minus Direct TER across companies.",
                           dcc.Graph(figure=fig_gap, config={"displayModeBar": False})), width=12),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Total gap by fund company", className="mb-0"),
            html.Small("Average Regular minus Direct TER in the selected year.", className="text-muted"),
            dcc.Slider(id="rank-year", min=y0, max=y1, step=1, value=y1, marks=grey(range(y0, y1 + 1))),
            dcc.Graph(id="rank-graph", figure=rank_fig(y1), config={"displayModeBar": False}),
        ])), width=12),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("What the gap costs over time", className="mb-0"),
            html.Small("Illustrative compounding using current average Direct and Regular TER. Move the sliders to try your own numbers.", className="text-muted"),
            html.Label("Amount invested (₹ lakh)", className="text-muted mt-3"),
            dcc.Slider(id="amount", min=1, max=100, step=1, value=10, marks=grey([1, 25, 50, 75, 100])),
            html.Label("Years invested", className="text-muted mt-3"),
            dcc.Slider(id="years", min=1, max=30, step=1, value=15, marks=grey([1, 5, 10, 15, 20, 25, 30])),
            html.Label("Return before costs (% a year)", className="text-muted mt-3"),
            dcc.Slider(id="gross", min=6, max=18, step=1, value=12, marks=grey([6, 9, 12, 15, 18])),
            dcc.Graph(id="calc-graph", figure=fig_calc0, config={"displayModeBar": False}),
            dcc.Markdown(text_calc0, id="calc-text"),
        ])), width=12),
    ], className="mb-5"),
  ])

@app.callback(Output("rank-graph", "figure"), Input("rank-year", "value"))
def update_rank(year):
    return rank_fig(year)

@app.callback(Output("calc-graph", "figure"), Output("calc-text", "children"),
               Input("amount", "value"), Input("years", "value"), Input("gross", "value"))
def update_calc(amount, n_years, gross):
    return calc(amount, n_years, gross)


# ======================================================================
# Notebook cell 15
# ======================================================================
# ---------- Dashboard 3: do Direct plans really earn more? ----------
# one row per company and date, with both plans' NAV side by side
pv = (nav.pivot_table(index=["MF_ID", "Date"], columns="Plan", values="NAV")
        .rename(columns={"Direct Plan": "Direct", "Regular Plan": "Regular"})
        .dropna().reset_index().sort_values(["MF_ID", "Date"]))
pv = pv.merge(companies[["MF_ID", "COMPANY"]], on="MF_ID")
last_date = pv["Date"].max()

CHART_H3 = 440      # every chart card in the top row gets the same chart area
WINDOWS = {"1 year": 1, "3 years": 3, "5 years": 5, "Since start": None}

def window_stats(n_years):
    """Yearly return of each plan over the last n_years (or the whole history if None)."""
    rows = []
    for mf, g in pv.groupby("MF_ID"):
        end = g["Date"].iloc[-1]
        if end < last_date - pd.Timedelta(days=30):          # stopped reporting
            continue
        if n_years is not None:
            start_date = end - pd.DateOffset(years=n_years)
            g = g[g["Date"] >= start_date]
            if (g["Date"].iloc[0] - start_date).days > 10:   # not enough history
                continue
        span_years = (end - g["Date"].iloc[0]).days / 365.25
        if span_years < 0.9:
            continue
        d = ((g["Direct"].iloc[-1] / g["Direct"].iloc[0]) ** (1 / span_years) - 1) * 100
        r = ((g["Regular"].iloc[-1] / g["Regular"].iloc[0]) ** (1 / span_years) - 1) * 100
        fee = t2[(t2["MF_ID"] == mf) & (t2["Date"] >= g["Date"].iloc[0])]["gap"].mean()
        rows.append({"COMPANY": g["COMPANY"].iloc[0], "Direct": d, "Regular": r,
                     "ret_gap": d - r, "fee_gap": fee})
    return pd.DataFrame(rows)

STATS = {name: window_stats(n) for name, n in WINDOWS.items()}

# ---------- KPI row ----------
def kpi_row(st):
    ahead = int((st["ret_gap"] > 0).sum())
    return dbc.Row([
        dbc.Col(kpi("Median Direct return", f"{st['Direct'].median():.1f}%", DIRECT, "a year"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Median Regular return", f"{st['Regular'].median():.1f}%", REGULAR, "a year"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Median return gap", f"{st['ret_gap'].median():.2f} pp", GAP, "Direct minus Regular, per year"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Direct ahead in", f"{ahead} of {len(st)}", sub="fund companies in this window"), xs=12, sm=6, xl=3),
    ], className="mb-4")

# ---------- chart A: return of each company, Direct vs Regular ----------
def return_fig(st):
    d = st.sort_values("Direct")                                   # best Direct return ends up on top
    long = d.melt(id_vars="COMPANY", value_vars=["Regular", "Direct"], var_name="Plan", value_name="Return")
    fig = px.bar(long, x="Return", y="COMPANY", color="Plan", barmode="group", orientation="h",
                 color_discrete_map={"Direct": DIRECT, "Regular": REGULAR})
    fig.update_traces(marker_line_width=0,
                      hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x:.2f}% a year<extra></extra>")
    fig.update_layout(bargap=0.28, bargroupgap=0.06)
    fig.update_yaxes(categoryorder="array", categoryarray=list(d["COMPANY"]), title_text="")
    fig.update_xaxes(ticksuffix="%", title_text="Return (% a year)")
    return style_fig(fig, max(CHART_H3, 34 * len(d) + 100))      # taller than the card -> scrolls inside it

# ---------- chart B: does the fee gap show up in the returns? ----------
def scatter_fig(st):
    s = st.dropna(subset=["fee_gap"])
    lo = min(0, s["fee_gap"].min(), s["ret_gap"].min())
    hi = max(s["fee_gap"].max(), s["ret_gap"].max())
    fig = px.scatter(s, x="fee_gap", y="ret_gap", hover_name="COMPANY", color_discrete_sequence=[GAP])
    fig.update_traces(marker=dict(size=12, opacity=0.9, line=dict(color=CARDS, width=1.5)),
                      hovertemplate="<b>%{hovertext}</b><br>Fee gap: %{x:.2f} pp<br>Return gap: %{y:.2f} pp<extra></extra>")
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="return gap = fee gap",
                             line=dict(color=MUTED, dash="dot"), hoverinfo="skip"))
    fig.add_hline(y=0, line=dict(color=BORDER, width=1))
    fig.add_annotation(x=hi, y=hi, text="return gap = fee gap", showarrow=False, xanchor="right", yanchor="bottom",
                       font=dict(color=MUTED, size=11))
    fig.update_xaxes(title_text="Fee gap (pp a year)", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(title_text="Return gap (pp a year)")
    fig.update_layout(showlegend=False)
    fig = style_fig(fig, CHART_H3)
    fig.update_xaxes(showgrid=True)
    return fig

def window_text(st, name):
    return f"""
- **{len(st)}** fund companies have enough history for **{name.lower()}**. The others are left out.
- Direct earned a median **{st['ret_gap'].median():.2f} pp** a year more than Regular.
- The fee gap (TER) over the same period had a median of **{st['fee_gap'].median():.2f} pp**.
- A dot on the dotted line means the fee gap explains the return gap fully.
"""

# ---------- chart C: what Rs 10 lakh really became ----------
def growth_fig(mf):
    g = pv[pv["MF_ID"] == mf].copy()
    g["Direct"] = g["Direct"] / g["Direct"].iloc[0] * 10           # Rs lakh
    g["Regular"] = g["Regular"] / g["Regular"].iloc[0] * 10
    long = g.melt(id_vars="Date", value_vars=["Direct", "Regular"], var_name="Plan", value_name="Value")
    fig = go.Figure()
    for plan, col in [("Regular", REGULAR), ("Direct", DIRECT)]:           # Direct last, so the fill sits between the two
        s = long[long["Plan"] == plan]
        fig.add_trace(go.Scatter(x=s["Date"], y=s["Value"], name=plan, mode="lines", line=dict(color=col, width=3),
                                 fill="tonexty" if plan == "Direct" else None, fillcolor=rgba(DIRECT, 0.12),
                                 hovertemplate=f"{plan}: ₹%{{y:.2f}} lakh<extra></extra>"))
    fig.add_hline(y=10, line=dict(color=MUTED, dash="dot", width=1))
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="Value (₹ lakh)")
    fig.update_layout(hovermode="x unified")
    add_range_selector(fig)
    behind = g["Direct"].iloc[-1] - g["Regular"].iloc[-1]
    text = (f"₹10 lakh put into **{g['COMPANY'].iloc[0]}** on **{g['Date'].iloc[0]:%d %b %Y}** is worth "
            f"**₹{g['Direct'].iloc[-1]:.1f} lakh** in Direct and **₹{g['Regular'].iloc[-1]:.1f} lakh** in Regular "
            f"on **{g['Date'].iloc[-1]:%d %b %Y}**. Regular is behind by **₹{behind:.1f} lakh**.")
    return style_fig(fig, 380), text


# ======================================================================
# Notebook cell 16
# ======================================================================
name_of = companies.set_index("MF_ID")["COMPANY"].to_dict()
co_ids = sorted(pv["MF_ID"].unique(), key=lambda m: name_of[m].lower())
co_options = [{"label": name_of[m], "value": int(m)} for m in co_ids]
co_default = int(next((m for m in co_ids if name_of[m] == "HDFC"), co_ids[0]))

W0 = "3 years"
fig_g0, text_g0 = growth_fig(co_default)

def page3():
  return html.Div([
    # ---- header ----
    page_header("Mid-Cap Mutual Funds: Do Direct Plans Earn More?",
                "Dashboard 3 · Do Direct plans really earn more?"),

    # ---- row 1: window picker (one full-width card) ----
    control_bar([
        dbc.Col([html.H4("Pick a time window", className="mb-0"),
                 html.Small("Only companies with enough history for the window are compared.", className="text-muted")], md=8),
        dbc.Col(dcc.RadioItems(id="window", options=list(WINDOWS), value=W0, inline=True,
                               className="pill-radio"), md=4),
    ]),

    # ---- row 2: four equal KPI cards ----
    html.Div(kpi_row(STATS[W0]), id="kpis"),

    # ---- row 3: two equal cards, same height ----
    dbc.Row([
        dbc.Col(chart_card("Return of each fund company",
                           "Teal = Direct, amber = Regular. Scroll inside the card to see every company.",
                           html.Div(dcc.Graph(id="return-graph", figure=return_fig(STATS[W0]),
                                              config={"displayModeBar": False}),
                                    style={"height": f"{CHART_H3}px", "overflowY": "auto", "overflowX": "hidden", "borderRadius": "10px"})),
                md=6),
        dbc.Col(chart_card("Does the fee gap show up in returns?",
                           "Each dot is a fund company.",
                           dcc.Graph(id="scatter-graph", figure=scatter_fig(STATS[W0]),
                                     config={"displayModeBar": False})),
                md=6),
    ], className="mb-4"),

    # ---- row 4: takeaways, full width ----
    dbc.Row(dbc.Col(dbc.Card(dbc.CardBody([html.H5("What this tells us"),
                                           dcc.Markdown(window_text(STATS[W0], W0), id="ret-text")]))),
            className="mb-4"),

    # ---- row 5: one company, real growth (one full-width card, picker inside) ----
    dbc.Row(dbc.Col(dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col([html.H5("Growth of ₹10 lakh", className="mb-0"),
                     html.Small("Same money, same day, two plans. Pick a fund company for its full history.",
                                className="text-muted")], md=8),
            dbc.Col(dcc.Dropdown(id="co-select", options=co_options, value=co_default, clearable=False), md=4),
        ], className="mb-3 align-items-end"),
        dcc.Graph(id="growth-graph", figure=fig_g0, config={"displayModeBar": False}),
        dcc.Markdown(text_g0, id="growth-text"),
    ]))), className="mb-5"),
])

@app.callback(Output("kpis", "children"), Output("return-graph", "figure"),
               Output("scatter-graph", "figure"), Output("ret-text", "children"),
               Input("window", "value"))
def update_window(name):
    st = STATS[name]
    return kpi_row(st), return_fig(st), scatter_fig(st), window_text(st, name)

@app.callback(Output("growth-graph", "figure"), Output("growth-text", "children"), Input("co-select", "value"))
def update_growth(mf):
    return growth_fig(int(mf))


# ======================================================================
# Notebook cell 20
# ======================================================================
# ---------- Dashboard 4: setup ----------
# one colour per group, used in every chart of Dashboards 4 and 5 (like COLORS in the course)
GROUP_COLORS = {"Cheapest 5": SKY, "Costliest 5": RED, "Middle": SLATE}   # sky = cheap, coral = costly, slate = the rest
CHEAP, COSTLY, MID = GROUP_COLORS["Cheapest 5"], GROUP_COLORS["Costliest 5"], GROUP_COLORS["Middle"]
AGAINST = SLATE                 # neutral slate = costlier funds earned MORE
LINE = TEXT                    # neutral trend line
BAR_TEXT = BG                  # dark text on bright bars

PLANS = {"Regular": ("Regular Plan", "R_TER"), "Direct": ("Direct Plan", "D_TER")}
WINDOWS4 = {"1 year": 1, "3 years": 3, "5 years": 5, "Since 2019": None}
MIN_FUNDS = 8                  # fewer fund companies than this -> no chart

first_date4, last_date4 = nav["Date"].min(), nav["Date"].max()
name4 = companies.set_index("MF_ID")["COMPANY"].to_dict()

# NAV of each plan as a table: one row per date, one column per fund company
nav_wide = {p: nav[nav["Plan"] == plan].pivot_table(index="Date", columns="MF_ID", values="NAV").sort_index()
            for p, (plan, _) in PLANS.items()}

def add_groups(df):
    """Mark the 5 cheapest and the 5 costliest fund companies (by TER); everyone else is 'Middle'."""
    df["group"] = "Middle"
    df.loc[df.nsmallest(5, "ter").index, "group"] = "Cheapest 5"
    df.loc[df.nlargest(5, "ter").index, "group"] = "Costliest 5"
    return df

def fund_table(plan, n_years):
    """One row per fund company: average TER, yearly return and volatility over the SAME window."""
    wide, ter_col = nav_wide[plan], PLANS[plan][1]
    start = first_date4 if n_years is None else last_date4 - pd.DateOffset(years=n_years)
    rows = []
    for mf in wide.columns:
        s = wide[mf].dropna()
        if s.empty or s.index[-1] < last_date4 - pd.Timedelta(days=30):          # stopped reporting
            continue
        if (s.index[0] - start).days > (30 if n_years is None else 10):           # not enough history for this window
            continue
        s = s[s.index >= start]
        years = (s.index[-1] - s.index[0]).days / 365.25
        if years < 0.9:
            continue
        t = ter.loc[(ter["MF_ID"] == mf) & (ter["Date"] >= s.index[0]) & (ter["Date"] <= s.index[-1]), ter_col].dropna()
        if t.empty:
            continue
        rows.append({"MF_ID": mf, "COMPANY": name4[mf], "ter": t.mean(),
                     "cagr": ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100,
                     "vol": s.pct_change().std() * np.sqrt(252) * 100})
    df = pd.DataFrame(rows)
    return add_groups(df) if len(df) >= MIN_FUNDS else df

TABLES = {(p, w): fund_table(p, n) for p in PLANS for w, n in WINDOWS4.items()}
print({f"{p} / {w}": len(t) for (p, w), t in TABLES.items()})


# ======================================================================
# Notebook cell 22
# ======================================================================
# ---------- Dashboard 4: the numbers behind the charts ----------
def fit(df):
    """Trend line, correlation r, R-squared and p-value of return against TER."""
    x, y = df["ter"].to_numpy(), df["cagr"].to_numpy()
    slope, icpt = np.polyfit(x, y, 1)
    r, n = np.corrcoef(x, y)[0, 1], len(df)
    try:                                                    # p-value: how likely is this r by pure chance?
        from scipy import stats
        p = 2 * stats.t.sf(abs(r) * np.sqrt((n - 2) / (1 - r ** 2)), n - 2)
    except Exception:
        p = np.nan
    return dict(slope=slope, icpt=icpt, r=r, r2=r ** 2, n=n, p=p)

def describe(r):
    a = abs(r)
    if a < 0.2:
        return "almost no link"
    word = "weak" if a < 0.4 else "moderate" if a < 0.6 else "strong"
    return f"a {word} {'negative' if r < 0 else 'positive'} link"

def year_table(plan):
    """For every calendar year: correlation between a fund's TER and its return in that year."""
    wide, col = nav_wide[plan], PLANS[plan][1]
    ter_yr = ter.assign(y=ter["Date"].dt.year).groupby(["MF_ID", "y"])[col].mean()
    rows = []
    for y in range(first_date4.year, last_date4.year + 1):
        ys, ye = pd.Timestamp(y - 1, 12, 31), pd.Timestamp(y, 12, 31)
        end_needed = ye if y < last_date4.year else last_date4
        for mf in wide.columns:
            s = wide[mf].dropna()
            prev, cur = s[s.index <= ys], s[(s.index > ys) & (s.index <= ye)]
            if cur.empty or (mf, y) not in ter_yr.index or pd.isna(ter_yr[(mf, y)]):
                continue
            if not prev.empty and (ys - prev.index[-1]).days <= 10:           # base = last NAV of the year before
                base = prev.iloc[-1]
            elif (cur.index[0] - pd.Timestamp(y, 1, 1)).days <= 10:           # fund started right at the year start
                base = cur.iloc[0]
            else:
                continue                                                      # no full year for this fund
            if (end_needed - cur.index[-1]).days > 10:
                continue
            rows.append({"year": y, "ter": ter_yr[(mf, y)], "ret": (cur.iloc[-1] / base - 1) * 100})
    d, out = pd.DataFrame(rows), []
    for y, g in d.groupby("year"):
        if len(g) >= MIN_FUNDS and g["ter"].nunique() > 1:
            out.append({"year": y, "r": np.corrcoef(g["ter"], g["ret"])[0, 1], "n": len(g)})
    out = pd.DataFrame(out)
    out["label"] = [str(y) + ("*" if y == last_date4.year and last_date4 < pd.Timestamp(y, 12, 20) else "") for y in out["year"]]
    return out

YEARS = {p: year_table(p) for p in PLANS}


# ======================================================================
# Notebook cell 24
# ======================================================================
# ---------- chart 1: average TER vs return ----------
def style_scatter_axes(fig, xtitle, ytitle):
    fig.update_xaxes(title_text=xtitle, ticksuffix="%", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(title_text=ytitle, ticksuffix="%")
    fig.update_layout(legend_title_text="")
    return fig

def scatter4(df, f):
    fig = px.scatter(df, x="ter", y="cagr", color="group", color_discrete_map=GROUP_COLORS,
                     category_orders={"group": ["Middle", "Cheapest 5", "Costliest 5"]},
                     hover_name="COMPANY", hover_data={"group": False, "ter": ":.2f", "cagr": ":.1f"})
    fig.update_traces(marker=dict(size=12, line=dict(color=CARDS, width=1.5)))
    fig.update_traces(marker_opacity=0.5, selector=dict(name="Middle"))          # push the middle funds back

    xs = [df["ter"].min(), df["ter"].max()]                                      # the trend line
    fig.add_scatter(x=xs, y=[f["icpt"] + f["slope"] * x for x in xs], mode="lines",
                    line=dict(color=LINE, width=2, dash="dash"), hoverinfo="skip", showlegend=False)

    pick = df.loc[sorted({df["cagr"].idxmax(), df["cagr"].idxmin(), df["ter"].idxmax(), df["ter"].idxmin()})]
    fig.add_scatter(x=pick["ter"], y=pick["cagr"], mode="text", text=pick["COMPANY"],     # name only the 4 extremes
                    textposition="top center", textfont=dict(color=TEXT, size=11), hoverinfo="skip", showlegend=False)
    fig.add_annotation(xref="paper", yref="paper", x=0.99, y=0.99, showarrow=False, xanchor="right", yanchor="top",
                       align="right", text=f"<b>R² = {f['r2']:.2f}</b><br>r = {f['r']:+.2f}", font=dict(color=TEXT, size=14),
                       bgcolor=SURFACE_HI, bordercolor=BORDER, borderwidth=1, borderpad=8)
    fig = style_fig(fig, 400)                      # style first, so the x grid below is kept
    return style_scatter_axes(fig, "Average TER (% a year)", "Return (% a year)")

df_demo = TABLES[("Regular", "3 years")]


# ======================================================================
# Notebook cell 26
# ======================================================================
# ---------- chart 2: four cost groups, average return ----------
QUARTILE_COLORS = {"Cheapest 25%": CHEAP, "Cheaper": MID, "Costlier": MID, "Costliest 25%": COSTLY}

def quartile4(df):
    d = df.copy()
    d["q"] = pd.qcut(d["ter"].rank(method="first"), 4, labels=False)          # 0 = cheapest ... 3 = costliest
    g = d.groupby("q").agg(ter=("ter", "mean"), cagr=("cagr", "mean"), n=("cagr", "size")).reset_index()
    g["name"] = ["Cheapest 25%", "Cheaper", "Costlier", "Costliest 25%"]
    g["text"] = g["cagr"].map("{:.1f}%".format)

    fig = px.bar(g, x="q", y="cagr", color="name", color_discrete_map=QUARTILE_COLORS, text="text",
                 hover_name="name", hover_data={"q": False, "name": False, "text": False, "cagr": ":.1f", "ter": ":.2f", "n": True})
    fig.update_traces(width=0.6, textposition="inside", insidetextanchor="start", textfont=dict(color=BAR_TEXT, size=16))
    for nm in ("Cheaper", "Costlier"):                                                  # light text on the slate bars
        fig.update_traces(textfont_color=TEXT, selector=dict(name=nm))

    rng = np.random.default_rng(4)                                             # every fund as a small ring on its bar
    fig.add_scatter(x=d["q"] + rng.uniform(-0.17, 0.17, len(d)), y=d["cagr"], mode="markers", text=d["COMPANY"],
                    marker=dict(color="rgba(0,0,0,0)", size=8, line=dict(color=TEXT, width=1.3)),
                    hovertemplate="<b>%{text}</b><br>Return %{y:.1f}% a year<extra></extra>", showlegend=False)

    fig = style_fig(fig, 400)
    fig.update_xaxes(tickvals=list(g["q"]), range=[-0.6, 3.6], title_text="",
                     ticktext=[f"{n}<br>TER {t:.2f}%" for n, t in zip(g["name"], g["ter"])])
    fig.update_yaxes(ticksuffix="%", rangemode="tozero", title_text="Return (% a year)")
    fig.update_layout(showlegend=False)
    return fig, g["cagr"].iloc[3] - g["cagr"].iloc[0]          # figure, and costliest minus cheapest

fig_q_demo, gap_demo = quartile4(df_demo)


# ======================================================================
# Notebook cell 28
# ======================================================================
# ---------- chart 3: is it the same every year? ----------
VERDICT_COLORS = {"Costlier funds earned less": COSTLY, "Costlier funds earned more": AGAINST}

def year_fig(plan):
    c = YEARS[plan].copy()
    c["verdict"] = np.where(c["r"] < 0, "Costlier funds earned less", "Costlier funds earned more")
    c["text"] = c["r"].map("{:+.2f}".format)
    fig = px.bar(c, x="label", y="r", color="verdict", color_discrete_map=VERDICT_COLORS, text="text",
                 category_orders={"label": list(c["label"])},
                 hover_data={"label": False, "verdict": False, "text": False, "r": ":+.2f", "n": True})
    fig.update_traces(width=0.6, textposition="outside", textfont=dict(color=TEXT, size=14), cliponaxis=False)
    fig.add_hrect(y0=-0.3, y1=0.3, fillcolor="#FFFFFF", opacity=0.05, line_width=0)      # the "weak" zone
    fig.add_hline(y=0, line_color=MUTED, line_width=1)
    fig.add_annotation(xref="paper", yref="y", x=0.995, y=0.3, text="weak zone", showarrow=False, xanchor="right", yanchor="bottom", font=dict(color=MUTED, size=10))
    fig = style_fig(fig, 400)
    fig.update_xaxes(type="category", title_text="")
    fig.update_yaxes(range=[-1, 1], tickformat="+.1f", title_text="Correlation (r)")
    fig.update_layout(legend_title_text="")
    return fig


# ======================================================================
# Notebook cell 30
# ======================================================================
# ---------- chart 4: the face-off, growth of Rs 10,000 ----------
def thin_and_thick(v, group_of, y_label):
    """v = one column per fund company, one row per date. Thin line per fund, thick line = average of its group."""
    v = v.copy()
    v.index.name = "Date"
    long = v.reset_index().melt(id_vars="Date", var_name="COMPANY", value_name="value")
    long["group"] = long["COMPANY"].map(group_of)
    fig = px.line(long, x="Date", y="value", color="group", line_group="COMPANY", hover_name="COMPANY",
                  color_discrete_map=GROUP_COLORS, labels={"value": y_label})
    fig.update_traces(line_width=1.3, opacity=0.4)

    avg = long.groupby(["group", "Date"])["value"].mean().reset_index()
    thick = px.line(avg, x="Date", y="value", color="group", color_discrete_map=GROUP_COLORS)
    thick.update_traces(line_width=4)
    fig.add_traces(thick.data)
    ends = {g: d["value"].iloc[-1] for g, d in avg.groupby("group")}
    return fig, ends

def label_ends(fig, ends, last_x, fmt):
    """Name each line at its right end instead of using a legend."""
    hi = max(ends, key=ends.get)
    close = abs(ends["Cheapest 5"] - ends["Costliest 5"]) / max(ends.values()) < 0.04     # keep touching labels apart
    for g, val in ends.items():
        fig.add_annotation(x=last_x, y=val, text=f"{g}: {fmt(val)}", showarrow=False, xanchor="left", xshift=8,
                           yshift=(9 if g == hi else -9) if close else 0, font=dict(color=GROUP_COLORS[g], size=13))

def faceoff_fig(df, plan, n_years):
    five = df[df["group"] != "Middle"]
    ids = list(five["MF_ID"])
    start = first_date4 if n_years is None else last_date4 - pd.DateOffset(years=n_years)
    w = nav_wide[plan][ids]
    w = w[w.index >= start]
    w = w.loc[max(w[c].first_valid_index() for c in ids):].ffill()          # everyone starts on the same day
    v = (w / w.iloc[0] * 10000).rename(columns=name4)

    fig, ends = thin_and_thick(v, dict(zip(five["COMPANY"], five["group"])), "Value of ₹10,000")
    label_ends(fig, ends, v.index[-1], lambda x: f"₹{x:,.0f}")
    fig.add_hline(y=10000, line=dict(color=MUTED, dash="dot", width=1))
    fig = style_fig(fig, 420)
    fig.update_layout(showlegend=False, margin=dict(r=190))                 # room for the end labels
    fig.update_xaxes(range=[v.index[0], v.index[-1]], title_text="")
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f", title_text="Value of ₹10,000")
    return fig, ends


# ======================================================================
# Notebook cell 32
# ======================================================================
# ---------- Dashboard 4: the app ----------
def empty_fig(msg, height=400):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(color=MUTED, size=14))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style_fig(fig, height)

def build4(plan, window):
    """One plan + one window -> everything on the dashboard (kpis, 4 charts, 2 texts)."""
    df, n_years = TABLES[(plan, window)], WINDOWS4[window]
    if len(df) < MIN_FUNDS:
        msg = "Not enough fund companies with history for this window"
        return (dbc.Row(dbc.Col(kpi("Fund companies", f"{len(df)}", sub=msg)), className="mb-4"),
                empty_fig(msg), msg, empty_fig(msg), year_fig(plan), empty_fig(msg, 420), "")
    f = fit(df)
    fig_q, gap_q = quartile4(df)
    fig_o, ends = faceoff_fig(df, plan, n_years)
    c = YEARS[plan]
    a, b = int((c["r"] < 0).sum()), len(c)

    kpis = dbc.Row([
        dbc.Col(kpi("Correlation (r)", f"{f['r']:+.2f}", sub=describe(f["r"])), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Each +1 pp of TER", f"{f['slope']:+.2f} pp", sub="change in yearly return (trend line)"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Costliest 25% minus cheapest 25%", f"{gap_q:+.1f} pp", sub="difference in yearly return"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Years costlier funds did worse", f"{a} of {b}", sub="calendar years with r below zero"), xs=12, sm=6, xl=3),
    ], className="mb-4")

    chance = "" if np.isnan(f["p"]) else (" This is **unlikely to be chance**." if f["p"] < 0.05
                                          else " With this few funds, it **could easily be chance**.")
    text = f"""
- **{f['n']}** fund companies, {plan} plan, {window.lower()}: cost and return show **{describe(f['r'])}** (r = {f['r']:+.2f}).
- Cost explains about **{f['r2'] * 100:.0f}%** of the differences in return. The other **{100 - f['r2'] * 100:.0f}%** is strategy, manager skill and luck.
- Each extra **1 pp** of TER goes with **{f['slope']:+.2f} pp** a year in return.{chance}
- In **{a} of {b}** calendar years the costlier funds earned less.
"""
    cheap_v, costly_v = ends["Cheapest 5"], ends["Costliest 5"]
    cheap_ter = df.loc[df["group"] == "Cheapest 5", "ter"].mean()
    costly_ter = df.loc[df["group"] == "Costliest 5", "ter"].mean()
    side = "in favour of the **cheap** funds" if cheap_v > costly_v else "in favour of the **costly** funds"
    face_text = (f"₹10,000 in the **5 cheapest** (average TER {cheap_ter:.2f}%) became **₹{cheap_v:,.0f}**. "
                 f"In the **5 costliest** (average TER {costly_ter:.2f}%) it became **₹{costly_v:,.0f}**. "
                 f"A difference of **₹{abs(cheap_v - costly_v):,.0f}**, {side}.")
    return kpis, scatter4(df, f), text, fig_q, year_fig(plan), fig_o, face_text

P0, W0_4 = "Regular", "3 years"
kpis0, fig_sc0, text0, fig_q0, fig_y0, fig_o0, face_text0 = build4(P0, W0_4)     # first view, drawn without a callback

def page4():
  return html.Div([
    page_header("Mid-Cap Mutual Funds: Does Cost Drag Returns?",
                "Dashboard 4 · Do costlier funds return less?"),

    # ---- two inputs: plan and window ----
    control_bar([
        dbc.Col([html.H4("Pick a plan and a time window", className="mb-0"),
                 html.Small("Every fund company is compared over the same window, using its own average TER in that window.",
                            className="text-muted")], md=5),
        dbc.Col([html.Label("Plan", className="text-muted d-block mb-1"),
                 dcc.RadioItems(id="plan4", options=list(PLANS), value=P0, inline=True,
                                className="pill-radio")], md=3),
        dbc.Col([html.Label("Window (the year-by-year chart ignores it)", className="text-muted d-block mb-1"),
                 dcc.RadioItems(id="win4", options=list(WINDOWS4), value=W0_4, inline=True,
                                className="pill-radio")], md=4),
    ]),

    html.Div(kpis0, id="kpis4"),

    # ---- the main question (8 + 4) ----
    dbc.Row([
        dbc.Col(chart_card("Does a higher TER mean a lower return?",
                           "Each dot is a fund company. Dashed line = trend. Bright dots = the 5 cheapest and the 5 costliest.",
                           dcc.Graph(id="scatter4", figure=fig_sc0, config=GRAPH)), xs=12, lg=8),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("What this tells us"),
                                       dcc.Markdown(text0, id="text4")]), className="h-100"), xs=12, lg=4),
    ], className="mb-4"),

    # ---- the same answer, simpler, and is it steady year to year? (5 + 7) ----
    dbc.Row([
        dbc.Col(chart_card("Four cost groups, average return",
                           "Funds sorted by cost into four equal groups. Bar = group average, ring = one fund.",
                           dcc.Graph(id="quart4", figure=fig_q0, config=GRAPH)), xs=12, lg=5),
        dbc.Col(chart_card("Is it the same every year?",
                           "Correlation of cost and return in each calendar year. Shaded band = weak (−0.3 to +0.3). * = year so far.",
                           dcc.Graph(id="year4", figure=fig_y0, config=GRAPH)), xs=12, lg=7),
    ], className="mb-4"),

    # ---- the face-off (8 + 4) ----
    dbc.Row([
        dbc.Col(chart_card("The face-off: ₹10,000 in the 5 cheapest vs the 5 costliest",
                           "Thin lines = single funds, thick line = average of the five.",
                           html.Div([dcc.Graph(id="face4", figure=fig_o0, config=GRAPH),
                                     dcc.Markdown(face_text0, id="face-text4")])), xs=12, lg=8),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("Read this with care"), dcc.Markdown("""
- **Cost is already inside the NAV.** A costlier fund starts every year with a handicap, so a small negative link is expected.
- **Funds are not twins.** Strategy and manager skill differ, so this is a **pattern, not proof**. Dashboard 3 is the clean test: same fund, only cost changed.
- **Small sample.** About 30 dots, so one odd fund can tilt the line.
- **Survivorship.** Funds that closed or merged are missing, and they were often weak, so the cost effect may be understated.
        """)]), className="h-100"), xs=12, lg=4),
    ], className="mb-5"),
])

# two inputs -> seven outputs
@app.callback([Output("kpis4", "children"), Output("scatter4", "figure"), Output("text4", "children"),
                Output("quart4", "figure"), Output("year4", "figure"), Output("face4", "figure"),
                Output("face-text4", "children")],
               [Input("plan4", "value"), Input("win4", "value")])
def update4(plan, window):
    return build4(plan, window)


# ======================================================================
# Notebook cell 36
# ======================================================================
# ---------- Dashboard 5: setup ----------
# (needs the Dashboard 4 cells first: nav_wide, TABLES, GROUP_COLORS, thin_and_thick, label_ends ...)
CRASH_FROM, CRASH_TO, PATH_TO = pd.Timestamp("2020-01-01"), pd.Timestamp("2020-03-31"), pd.Timestamp("2020-06-30")
WORST_DAY = "2020-03-23"                         # the worst day in the cleaning notebook
ROLL_COLORS = {"Cheapest 25%": CHEAP, "Costliest 25%": COSTLY}
ter_sorted = ter.sort_values("Date")

# ---------- the March 2020 crash: biggest fall from a peak, Jan to Mar 2020 ----------
def crash_table(plan):
    ter_col = PLANS[plan][1]
    w = nav_wide[plan].loc[CRASH_FROM:CRASH_TO]
    rows = []
    for mf in w.columns:
        s = w[mf].dropna()
        if len(s) < 40 or (s.index[0] - CRASH_FROM).days > 10:         # the fund must already exist in Jan 2020
            continue
        t = ter_sorted.loc[(ter_sorted["MF_ID"] == mf) & (ter_sorted["Date"].dt.year == 2020), ter_col].dropna()
        src = "2020"
        if t.empty:                                                    # no TER in 2020: use the earliest on record
            t = ter_sorted.loc[ter_sorted["MF_ID"] == mf, ter_col].dropna().head(250)
            src = "earliest on record"
        if t.empty:
            continue
        rows.append({"MF_ID": mf, "COMPANY": name4[mf], "ter": t.mean(), "ter_src": src,
                     "drawdown": (s / s.cummax() - 1).min() * 100})
    df = pd.DataFrame(rows)
    return add_groups(df) if len(df) >= MIN_FUNDS else df

# ---------- rolling 1-year return: band of the cheapest 25% and the costliest 25% ----------
def rolling_table(plan):
    ter_col, wide = PLANS[plan][1], nav_wide[plan]
    daily = wide.asfreq("D").ffill(limit=5)                            # one row per calendar day
    roll = ((daily / daily.shift(365) - 1) * 100).iloc[365::7]         # 1-year return, one point a week
    rows = []
    for mf in wide.columns:
        s = wide[mf].dropna()
        if s.empty or s.index[-1] < last_date4 - pd.Timedelta(days=30) or (s.index[-1] - s.index[0]).days < 3 * 365:
            continue                                                   # need 3+ years of history
        t = ter.loc[ter["MF_ID"] == mf, ter_col].dropna()
        if not t.empty:
            rows.append({"MF_ID": mf, "ter": t.mean()})
    d = pd.DataFrame(rows)
    if len(d) < MIN_FUNDS:
        return pd.DataFrame()
    d["q"] = pd.qcut(d["ter"].rank(method="first"), 4, labels=False)
    out = []
    for q, name in [(0, "Cheapest 25%"), (3, "Costliest 25%")]:
        r = roll[list(d.loc[d["q"] == q, "MF_ID"])]
        g = pd.DataFrame({"lo": r.quantile(0.25, axis=1), "med": r.median(axis=1),
                          "hi": r.quantile(0.75, axis=1), "n": r.count(axis=1)})
        g = g[g["n"] >= 4].reset_index()                               # a band needs at least 4 funds
        if g.empty:
            return pd.DataFrame()
        g = g.rename(columns={g.columns[0]: "Date"})
        g["group"] = name
        out.append(g)
    return pd.concat(out, ignore_index=True)

CRASH = {p: crash_table(p) for p in PLANS}
ROLL = {p: rolling_table(p) for p in PLANS}
print({p: len(t) for p, t in CRASH.items()}, {p: len(t) for p, t in ROLL.items()})


# ======================================================================
# Notebook cell 38
# ======================================================================
# ---------- chart 1: risk vs return (bubble size = TER) ----------
def bubble5(df):
    fig = px.scatter(df, x="vol", y="cagr", size="ter", size_max=26, color="group", color_discrete_map=GROUP_COLORS,
                     category_orders={"group": ["Middle", "Cheapest 5", "Costliest 5"]}, hover_name="COMPANY",
                     hover_data={"group": False, "vol": ":.1f", "cagr": ":.1f", "ter": ":.2f"})
    fig.update_traces(marker=dict(opacity=0.85, line=dict(color=CARDS, width=1)))
    fig.update_traces(marker_opacity=0.4, selector=dict(name="Middle"))          # push the middle funds back
    pick = df.loc[sorted({df["cagr"].idxmax(), df["vol"].idxmin(), df["vol"].idxmax()})]
    fig.add_scatter(x=pick["vol"], y=pick["cagr"], mode="text", text=pick["COMPANY"], textposition="top center",
                    textfont=dict(color=TEXT, size=11), hoverinfo="skip", showlegend=False)
    fig = style_fig(fig, 420)
    return style_scatter_axes(fig, "Volatility (% a year): how widely the NAV swings", "Return (% a year)")


# ======================================================================
# Notebook cell 40
# ======================================================================
# ---------- chart 2: March 2020 crash test ----------
def crash_bars(df):
    d = df.sort_values("ter").copy()                                            # costliest ends up on top
    d["label"] = d["COMPANY"] + "  (TER " + d["ter"].map("{:.2f}".format) + "%)"
    d["txt"] = d["drawdown"].map("{:.1f}%".format)
    fig = px.bar(d, x="drawdown", y="label", orientation="h", color="group", color_discrete_map=GROUP_COLORS,
                 category_orders={"label": list(d["label"]), "group": ["Middle", "Cheapest 5", "Costliest 5"]},
                 text="txt", hover_name="COMPANY",
                 hover_data={"label": False, "group": False, "txt": False, "drawdown": ":.1f", "ter": ":.2f"})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig = style_fig(fig, max(380, 24 * len(d) + 90))
    fig.update_xaxes(title_text="Biggest fall from a peak, Jan to Mar 2020", ticksuffix="%",
                     range=[d["drawdown"].min() * 1.18, 0])
    fig.update_yaxes(title_text="")
    fig.update_layout(legend_title_text="")
    return fig

def crash_path(df, plan):
    five = df[df["group"] != "Middle"]
    ids = list(five["MF_ID"])
    w = nav_wide[plan].loc[CRASH_FROM:PATH_TO, ids].ffill()
    v = (w / w.bfill().iloc[0] * 100).rename(columns=name4)                     # every fund starts at 100
    fig, ends = thin_and_thick(v, dict(zip(five["COMPANY"], five["group"])), "NAV (start = 100)")
    label_ends(fig, ends, v.index[-1], lambda x: f"{x:.0f}")
    fig.add_shape(type="line", x0=WORST_DAY, x1=WORST_DAY, y0=0, y1=1, yref="paper",
                  line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x=WORST_DAY, y=1, yref="paper", text="23 Mar 2020", showarrow=False,
                       yanchor="bottom", font=dict(color=MUTED, size=12))
    fig = style_fig(fig, max(380, 24 * len(df) + 90))
    fig.update_layout(showlegend=False, margin=dict(r=150, t=40))
    fig.update_xaxes(title_text="")
    return fig

crash_demo = CRASH["Regular"]


# ======================================================================
# Notebook cell 42
# ======================================================================
# ---------- chart 3: rolling 1-year return bands ----------
def rolling_fig(plan):
    b = ROLL[plan]
    if b.empty:
        return empty_fig("Not enough fund companies with 3+ years of history", 420)
    fig = go.Figure()
    for name, col in ROLL_COLORS.items():
        d = b[b["group"] == name]
        fig.add_scatter(x=list(d["Date"]) + list(d["Date"][::-1]), y=list(d["hi"]) + list(d["lo"][::-1]),   # the band
                        fill="toself", fillcolor=rgba(col, 0.20), line=dict(width=0), hoverinfo="skip", showlegend=False)
    for name, col in ROLL_COLORS.items():
        d = b[b["group"] == name]
        fig.add_scatter(x=d["Date"], y=d["med"], mode="lines", name=name, line=dict(color=col, width=3),   # the middle fund
                        hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>")
    fig.add_hline(y=0, line=dict(color=MUTED, width=1))
    fig = style_fig(fig, 420)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="1-year return (%)", ticksuffix="%")
    fig.update_layout(hovermode="x unified")
    return fig


# ======================================================================
# Notebook cell 44
# ======================================================================
# ---------- Dashboard 5: the app ----------
def pair(a, b, fmt):
    """Two numbers in the two group colours: cheap (sky) vs costly (coral)."""
    return [html.Span(fmt(a), style={"color": CHEAP}), html.Span("  vs  ", className="text-muted", style={"fontSize": "1rem"}),
            html.Span(fmt(b), style={"color": COSTLY})]

def verdict(diff, tol):
    """+1 = the costly funds look better, -1 = worse, 0 = about the same (diff = costly minus cheap, positive = better)."""
    return 1 if diff > tol else -1 if diff < -tol else 0

def build5(plan, window):
    df, cr, rb = TABLES[(plan, window)], CRASH[plan], ROLL[plan]
    if len(df) < MIN_FUNDS or len(cr) < MIN_FUNDS or rb.empty:
        msg = "Not enough fund companies with history for this plan and window"
        return (dbc.Row(dbc.Col(kpi("Fund companies", f"{len(df)}", sub=msg)), className="mb-4"),
                empty_fig(msg, 420), msg, empty_fig(msg, 420), empty_fig(msg, 420), rolling_fig(plan))

    cheap, costly = df[df["group"] == "Cheapest 5"], df[df["group"] == "Costliest 5"]
    r_vol = np.corrcoef(df["ter"], df["vol"])[0, 1]
    vol_c, vol_k = cheap["vol"].mean(), costly["vol"].mean()
    rpr_c, rpr_k = (cheap["cagr"] / cheap["vol"]).mean(), (costly["cagr"] / costly["vol"]).mean()   # return per 1 pt of volatility
    dd_c = cr.loc[cr["group"] == "Cheapest 5", "drawdown"].mean()
    dd_k = cr.loc[cr["group"] == "Costliest 5", "drawdown"].mean()
    width = (rb["hi"] - rb["lo"]).groupby(rb["group"]).mean()
    loss = (rb["med"] < 0).groupby(rb["group"]).mean() * 100
    w_c, w_k = width["Cheapest 25%"], width["Costliest 25%"]

    kpis = dbc.Row([
        dbc.Col(kpi("Cost vs volatility (r)", f"{r_vol:+.2f}", sub=describe(r_vol)), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Return per 1 pt of volatility", pair(rpr_c, rpr_k, lambda x: f"{x:.2f}"), sub="cheapest 5 vs costliest 5"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Fall in March 2020", pair(dd_c, dd_k, lambda x: f"{x:.0f}%"), sub="average biggest fall, cheapest 5 vs costliest 5"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Spread of 1-year returns", pair(w_c, w_k, lambda x: f"{x:.0f} pp"), sub="middle half of funds, cheapest vs costliest 25%"), xs=12, sm=6, xl=3),
    ], className="mb-4")

    # three tests: did the costlier funds look safer?
    tests = [verdict(vol_c - vol_k, 0.5), verdict(dd_k - dd_c, 1), verdict(w_c - w_k, 1)]
    wins, losses = tests.count(1), tests.count(-1)
    if wins == 0 and losses >= 1:
        end = "**No sign that the extra cost bought safety.** The costlier funds were not calmer, did not fall less and were not more consistent."
    elif wins == 0 and losses == 0:
        end = "**No clear difference** between the costlier and the cheaper funds on risk, crash fall or consistency."
    elif wins >= 2:
        end = f"**The costlier funds looked safer in {wins} of 3 tests.** That may be worth something, but 5 funds against 5 is a small group."
    else:
        end = f"**A mixed picture:** the costlier funds looked safer in {wins} of 3 tests and worse in {losses}."
    text = f"""
- **Volatility:** cheapest 5 **{vol_c:.1f}%**, costliest 5 **{vol_k:.1f}%** a year. Cost and volatility show **{describe(r_vol)}**.
- **March 2020:** the cheapest 5 fell **{abs(dd_c):.0f}%** at the worst point, the costliest 5 **{abs(dd_k):.0f}%**.
- **Consistency:** the middle half of cheap funds were spread over **{w_c:.0f} pp**, costly funds over **{w_k:.0f} pp**. A median fund lost money over 1 year on **{loss['Cheapest 25%']:.0f}%** of weeks (cheap) and **{loss['Costliest 25%']:.0f}%** (costly).
- {end}
"""
    return kpis, bubble5(df), text, crash_bars(cr), crash_path(cr, plan), rolling_fig(plan)

P5, W5 = "Regular", "3 years"
kpis5, fig_b5, text5, fig_cb5, fig_cp5, fig_r5 = build5(P5, W5)

def page5():
  return html.Div([
    page_header("Mid-Cap Mutual Funds: What Does Extra Cost Buy?",
                "Dashboard 5 · What does the extra cost buy: less risk, smaller crashes, steadier returns?"),

    # ---- two inputs: plan and window ----
    control_bar([
        dbc.Col([html.H4("Pick a plan and a time window", className="mb-0"),
                 html.Small("The window only changes the first chart. The crash test and the rolling bands use fixed periods.",
                            className="text-muted")], md=5),
        dbc.Col([html.Label("Plan", className="text-muted d-block mb-1"),
                 dcc.RadioItems(id="plan5", options=list(PLANS), value=P5, inline=True,
                                className="pill-radio")], md=3),
        dbc.Col([html.Label("Window (risk chart only)", className="text-muted d-block mb-1"),
                 dcc.RadioItems(id="win5", options=list(WINDOWS4), value=W5, inline=True,
                                className="pill-radio")], md=4),
    ]),

    html.Div(kpis5, id="kpis5"),

    # ---- risk vs return (7 + 5) ----
    dbc.Row([
        dbc.Col(chart_card("Do costlier funds take less risk?",
                           "Each bubble is a fund company. Bubble size = TER. Further right = wilder swings, higher = better return.",
                           dcc.Graph(id="bubble5", figure=fig_b5, config=GRAPH)), xs=12, lg=7),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("What this tells us"),
                                       dcc.Markdown(text5, id="text5")]), className="h-100"), xs=12, lg=5),
    ], className="mb-4"),

    # ---- the March 2020 crash (6 + 6) ----
    dbc.Row([
        dbc.Col(chart_card("March 2020 crash test: who fell furthest?",
                           "Funds that already existed in Jan 2020, ordered by TER (costliest on top). A shorter bar = a smaller fall.",
                           dcc.Graph(id="crash-bars5", figure=fig_cb5, config=GRAPH)), xs=12, lg=6),
        dbc.Col(chart_card("The fall and the recovery",
                           "NAV of the 5 cheapest and 5 costliest among them, Jan to Jun 2020 (start = 100). Thin = one fund, thick = average.",
                           dcc.Graph(id="crash-path5", figure=fig_cp5, config=GRAPH)), xs=12, lg=6),
    ], className="mb-4"),

    # ---- consistency (8 + 4) ----
    dbc.Row([
        dbc.Col(chart_card("Which group is steadier? Rolling 1-year returns",
                           "Line = the middle fund of the group, band = the middle half of its funds. A narrower, higher band is steadier.",
                           dcc.Graph(id="roll5", figure=fig_r5, config=GRAPH)), xs=12, lg=8),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("Read this with care"), dcc.Markdown("""
- **Volatility** is how widely the daily NAV swings, scaled to a year. It counts ups and downs alike.
- **Crash test:** only funds that existed in Jan 2020 are included. If a fund has no 2020 TER, its earliest TER on record is used.
- **5 funds against 5** is a small group, so treat the result as a hint, not proof.
- **Rolling 1-year returns overlap**, so neighbouring weeks are not independent evidence.
        """)]), className="h-100"), xs=12, lg=4),
    ], className="mb-5"),
])

# two inputs -> six outputs
@app.callback([Output("kpis5", "children"), Output("bubble5", "figure"), Output("text5", "children"),
                Output("crash-bars5", "figure"), Output("crash-path5", "figure"), Output("roll5", "figure")],
               [Input("plan5", "value"), Input("win5", "value")])
def update5(plan, window):
    return build5(plan, window)


# ======================================================================
# Notebook cell 46
# ======================================================================
# ---------- Dashboard 6: calculations ----------
# Reuses nav_wide, PLANS, WINDOWS4, first_date4, last_date4, name4,
# ter, companies, style_fig, kpi, chart_card, empty_fig and GRAPH from earlier cells.

WINDOWS6 = WINDOWS4.copy()
SCORE_GAP = COUNT            # periwinkle = Direct minus Regular return gap
SCORE_MUTED = MUTED          # muted = peer fund houses
SCORE_HIGHLIGHT = COUNT      # periwinkle = selected fund house

def score_table6(window):
    """One row per eligible fund house, with Direct/Regular metrics on a common window."""
    n_years = WINDOWS6[window]
    start = first_date4 if n_years is None else last_date4 - pd.DateOffset(years=n_years)
    rows = []

    for mf in nav_wide["Direct"].columns:
        metrics = {}
        eligible = True

        for plan in ["Direct", "Regular"]:
            s = nav_wide[plan][mf].dropna().sort_index()

            # Require current data and sufficient history for the selected window.
            if s.empty or s.index[-1] < last_date4 - pd.Timedelta(days=30):
                eligible = False
                break
            if s.index[0] > start + pd.Timedelta(days=30):
                eligible = False
                break

            s = s.loc[(s.index >= start) & (s.index <= last_date4)]
            if len(s) < 2:
                eligible = False
                break

            elapsed_years = (s.index[-1] - s.index[0]).days / 365.25
            if elapsed_years <= 0 or (n_years is not None and elapsed_years < n_years * 0.90):
                eligible = False
                break

            cagr = ((s.iloc[-1] / s.iloc[0]) ** (1 / elapsed_years) - 1) * 100
            max_dd = (s / s.cummax() - 1).min() * 100
            metrics[plan] = {"cagr": cagr, "drawdown": max_dd, "start": s.index[0], "end": s.index[-1]}

        if not eligible:
            continue

        # Average TER over the same NAV period, per plan.
        ter_metrics = {}
        for plan, (_, ter_col) in PLANS.items():
            nav_start = metrics[plan]["start"]
            nav_end = metrics[plan]["end"]
            t = ter.loc[
                (ter["MF_ID"] == mf) &
                (ter["Date"] >= nav_start) &
                (ter["Date"] <= nav_end),
                ter_col
            ].dropna()

            if t.empty:
                eligible = False
                break
            ter_metrics[plan] = float(t.mean())

        if not eligible:
            continue

        rows.append({
            "MF_ID": mf,
            "COMPANY": name4.get(mf, str(mf)),
            "Direct_CAGR": metrics["Direct"]["cagr"],
            "Regular_CAGR": metrics["Regular"]["cagr"],
            "Direct_DD": metrics["Direct"]["drawdown"],
            "Regular_DD": metrics["Regular"]["drawdown"],
            "Direct_TER": ter_metrics["Direct"],
            "Regular_TER": ter_metrics["Regular"],
            "CAGR_Gap": metrics["Direct"]["cagr"] - metrics["Regular"]["cagr"],
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Higher CAGR = rank 1. Ties receive the same rank.
    df["Direct_Rank"] = df["Direct_CAGR"].rank(ascending=False, method="min").astype(int)
    df["Regular_Rank"] = df["Regular_CAGR"].rank(ascending=False, method="min").astype(int)
    return df


def score_nav_fig6(mf_id, window):
    """Growth of a common starting value, so Direct and Regular are comparable."""
    n_years = WINDOWS6[window]
    start = first_date4 if n_years is None else last_date4 - pd.DateOffset(years=n_years)
    fig = go.Figure()

    for plan, color in [("Direct", DIRECT), ("Regular", REGULAR)]:
        s = nav_wide[plan][mf_id].dropna().sort_index()
        s = s.loc[(s.index >= start) & (s.index <= last_date4)]
        if s.empty:
            continue

        growth = s / s.iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=growth.index, y=growth.values, name=plan, mode="lines",
            line=dict(color=color, width=3),
            fill="tonexty" if plan == "Regular" else None, fillcolor=rgba(DIRECT, 0.10),
            hovertemplate="<b>%{fullData.name}</b><br>Growth index: %{y:.2f}<br>%{x|%d %b %Y}<extra></extra>"
        ))

    fig.update_layout(hovermode="x unified")
    add_range_selector(fig)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="Growth index (start = 100)")
    return style_fig(fig, 350)


def score_ter_fig6(mf_id, window):
    n_years = WINDOWS6[window]
    start = first_date4 if n_years is None else last_date4 - pd.DateOffset(years=n_years)
    t = ter.loc[
        (ter["MF_ID"] == mf_id) &
        (ter["Date"] >= start) &
        (ter["Date"] <= last_date4)
    ].sort_values("Date")

    fig = go.Figure()
    for col, plan, color in [
        ("D_TER", "Direct", DIRECT),
        ("R_TER", "Regular", REGULAR)
    ]:
        if col not in t.columns:
            continue
        fig.add_trace(go.Scatter(
            x=t["Date"], y=t[col], name=plan, mode="lines",
            line=dict(color=color, width=2.5, shape="hv"),
            fill="tonexty" if plan == "Regular" else None, fillcolor=rgba(REGULAR, 0.13),
            hovertemplate="<b>%{fullData.name}</b><br>TER: %{y:.2f}%<br>%{x|%d %b %Y}<extra></extra>"
        ))

    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="TER (% of assets per year)")
    return style_fig(fig, 300)


def score_rank_fig6(df, selected_id):
    """Peer ranking: muted peers, selected fund house highlighted."""
    if df.empty:
        return empty_fig("No eligible fund houses for this window", 450)

    d = df.sort_values("Direct_CAGR", ascending=True).copy()
    fade = [1.0 if mf == selected_id else 0.40 for mf in d["MF_ID"]]    # selected = full colour, peers fade back

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=d["COMPANY"], x=d["Direct_CAGR"], name="Direct",
        orientation="h", marker=dict(color=DIRECT, opacity=fade),
        customdata=d[["Direct_Rank", "Regular_CAGR", "Regular_Rank"]].to_numpy(),
        hovertemplate="<b>%{y}</b><br>Direct CAGR: %{x:.2f}%<br>Direct rank: %{customdata[0]}<br>Regular CAGR: %{customdata[1]:.2f}%<br>Regular rank: %{customdata[2]}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        y=d["COMPANY"], x=d["Regular_CAGR"], name="Regular",
        orientation="h", marker=dict(color=REGULAR, opacity=fade),
        hovertemplate="<b>%{y}</b><br>Regular CAGR: %{x:.2f}%<extra></extra>"
    ))

    # Mark the selected house's row with a periwinkle diamond.
    selected = d[d["MF_ID"] == selected_id]
    if not selected.empty:
        fig.add_annotation(
            x=0, y=selected["COMPANY"].iloc[0],
            xref="x", yref="y",
            text="◆", showarrow=False,
            xshift=-14, font=dict(color=SCORE_HIGHLIGHT, size=13)
        )

    fig.update_layout(barmode="group", hovermode="closest")
    fig.update_xaxes(title_text="CAGR (%)", zeroline=True, zerolinecolor=BORDER, ticksuffix="%")
    fig.update_yaxes(title_text="", showgrid=False, categoryorder="array", categoryarray=d["COMPANY"])
    return style_fig(fig, max(420, len(d) * 24))


# ======================================================================
# Notebook cell 47
# ======================================================================
# ---------- Dashboard 6: interactive Dash app ----------

def build_scorecard6(mf_id, window):
    df = score_table6(window)

    if df.empty or mf_id not in set(df["MF_ID"]):
        msg = "This fund house does not have enough history for the selected window."
        return (
            html.H3(name4.get(mf_id, "Selected fund house")),
            dbc.Row(dbc.Col(kpi("Eligible fund houses", f"{len(df)}", sub=msg))),
            empty_fig(msg, 350), empty_fig(msg, 300), empty_fig(msg, 450),
            html.P(msg, className="text-muted")
        )

    selected = df.loc[df["MF_ID"] == mf_id].iloc[0]

    # Correlation is calculated across eligible fund houses, separately for each plan.
    r_direct = df["Direct_TER"].corr(df["Direct_CAGR"])
    r_regular = df["Regular_TER"].corr(df["Regular_CAGR"])

    title = html.Div([
        html.H3(selected["COMPANY"], className="mb-0"),
        html.Small(
            f"{window} · {len(df)} eligible fund houses · CAGR rank 1 = highest",
            className="text-muted"
        )
    ])

    kpis = dbc.Row([
        dbc.Col(kpi("Direct CAGR", f'{selected["Direct_CAGR"]:.2f}%', DIRECT,
                    sub=f'Rank {selected["Direct_Rank"]} / {len(df)}'), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Regular CAGR", f'{selected["Regular_CAGR"]:.2f}%', REGULAR,
                    sub=f'Rank {selected["Regular_Rank"]} / {len(df)}'), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Direct max drawdown", f'{selected["Direct_DD"]:.2f}%', DIRECT,
                    sub="Largest peak-to-trough fall"), xs=12, sm=6, xl=3),
        dbc.Col(kpi("Regular max drawdown", f'{selected["Regular_DD"]:.2f}%', REGULAR,
                    sub="Largest peak-to-trough fall"), xs=12, sm=6, xl=3),
    ], className="mb-3")

    # Two final verdict numbers, with enough context to interpret them.
    gap = selected["CAGR_Gap"]
    gap_color = DIRECT if gap >= 0 else REGULAR
    verdict_panel = dbc.Card(dbc.CardBody([
        html.H5("Final verdict", className="mb-3"),

        html.P("TER–return relationship", className="text-muted mb-1"),
        html.Div([
            html.Span("Direct  ", style={"color": DIRECT, "fontWeight": "600"}),
            html.Span(f"r = {r_direct:+.2f}", style={"color": TEXT, "fontWeight": "600"})
        ], className="mb-1"),
        html.Div([
            html.Span("Regular  ", style={"color": REGULAR, "fontWeight": "600"}),
            html.Span(f"r = {r_regular:+.2f}", style={"color": TEXT, "fontWeight": "600"})
        ]),
        html.Small(
            f"Correlation across {len(df)} eligible fund houses; association, not causation.",
            className="text-muted"
        ),

        html.Hr(),

        html.P("Direct–Regular CAGR gap", className="text-muted mb-1"),
        html.H2(f"{gap:+.2f} pp", style={"color": gap_color}),
        html.P(
            "Direct earned more per year." if gap > 0 else
            "Regular earned more per year." if gap < 0 else
            "Both plans had the same CAGR.",
            className="text-muted mb-2"
        ),

        html.Hr(),

        html.P([
            html.Span("Direct rank: ", style={"color": DIRECT}),
            html.Span(f'{selected["Direct_Rank"]} / {len(df)}')
        ]),
        html.P([
            html.Span("Regular rank: ", style={"color": REGULAR}),
            html.Span(f'{selected["Regular_Rank"]} / {len(df)}')
        ], className="mb-0")
    ]), className="h-100")

    return (
        title,
        kpis,
        score_nav_fig6(mf_id, window),
        score_ter_fig6(mf_id, window),
        score_rank_fig6(df, mf_id),
        verdict_panel
    )


# Choose a default fund house that is eligible for the default 3-year window.
DEFAULT_WINDOW6 = "3 years"
_default_df6 = score_table6(DEFAULT_WINDOW6)
DEFAULT_ID6 = int(_default_df6["MF_ID"].iloc[0]) if not _default_df6.empty else int(companies["MF_ID"].iloc[0])

score_options6 = [
    {"label": name4.get(int(mf), str(mf)), "value": int(mf)}
    for mf in sorted(companies["MF_ID"].dropna().unique())
]

initial6 = build_scorecard6(DEFAULT_ID6, DEFAULT_WINDOW6)

def page6():
  return html.Div([
    page_header("Mid-Cap Mutual Funds: Fund-House Scorecard",
                "Dashboard 6 · How did one fund house do, and where does it rank?"),

    control_bar([
        dbc.Col([html.H4("Pick a fund house and a time window", className="mb-0"),
                 html.Small("The profile, charts and ranking all update together.", className="text-muted")], md=12),
        dbc.Col([html.Label("Fund house"),
                 dcc.Dropdown(id="score-house6", options=score_options6, value=DEFAULT_ID6, clearable=False)], md=7),
        dbc.Col([html.Label("Performance window"),
                 dcc.Dropdown(id="score-window6", options=[{"label": w, "value": w} for w in WINDOWS6],
                              value=DEFAULT_WINDOW6, clearable=False)], md=5),
    ]),

    html.Div(initial6[0], id="score-title6", className="mb-3"),
    html.Div(initial6[1], id="score-kpis6", className="mb-4"),

    dbc.Row([
        dbc.Col(chart_card(
            "NAV growth · Direct vs Regular",
            "Both plans are indexed to 100 at the start of the selected window.",
            dcc.Graph(id="score-nav6", figure=initial6[2], config=GRAPH)
        ), md=7),
        dbc.Col(chart_card(
            "TER over time",
            "Yearly expense ratio for the selected fund house.",
            dcc.Graph(id="score-ter6", figure=initial6[3], config=GRAPH)
        ), md=5)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(chart_card(
            "CAGR ranking across fund houses",
            "Direct and Regular are compared side by side. The selected house is marked with a ◆ and shown at full strength; peers are faded.",
            dcc.Graph(id="score-rank6", figure=initial6[4], config=GRAPH)
        ), md=8),
        dbc.Col(html.Div(initial6[5], id="score-verdict6"), md=4)
    ], className="mb-5")
])


@app.callback(
    Output("score-title6", "children"),
    Output("score-kpis6", "children"),
    Output("score-nav6", "figure"),
    Output("score-ter6", "figure"),
    Output("score-rank6", "figure"),
    Output("score-verdict6", "children"),
    Input("score-house6", "value"),
    Input("score-window6", "value")
)
def update_scorecard6(mf_id, window):
    return build_scorecard6(int(mf_id), window)


# ======================================================================
# Notebook cell 49
# ======================================================================
# ============================================================
# Additional must-have analytical plots (Dashboards 3–6)
# Added as a final extension cell so the original analysis stays intact.
# ============================================================

def _append_to_page(original_page, additions):
    """Keep the original dashboard layout and append new rows."""
    base = original_page()
    base.children = list(base.children) + additions
    return base

# ---------- Dashboard 3: company-level normalized NAV + rolling return gap ----------
def nav_growth_all3():
    fig = go.Figure()
    for plan, color in [("Direct", DIRECT), ("Regular", REGULAR)]:
        frame = nav_wide[plan]
        for mf in frame.columns:
            s = frame[mf].dropna().sort_index()
            if len(s) < 2:
                continue
            # Rebase each company to 100 on its own first available date.
            y = s / s.iloc[0] * 100
            company = name4.get(mf, name_of.get(mf, str(mf)))
            fig.add_trace(go.Scatter(
                x=y.index, y=y.values, mode="lines",
                name=f"{company} · {plan}",
                legendgroup=plan, showlegend=False,
                line=dict(color=color, width=1, shape="linear"),
                opacity=0.30,
                hovertemplate=f"<b>{company}</b><br>{plan}<br>Indexed NAV: %{{y:.1f}}<extra></extra>"
            ))
    # Add one legend key per plan.
    for plan, color in [("Direct", DIRECT), ("Regular", REGULAR)]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=plan,
                                 line=dict(color=color, width=3)))
    fig.update_layout(hovermode="closest", yaxis_title="NAV index (first observation = 100, log scale)")
    fig.update_xaxes(title_text="")
    fig.update_yaxes(type="log", dtick="D2", tickformat=",.0f")           # growth compares in ratios, so a log axis
    return style_fig(fig, 480)

def rolling_return_gap3():
    fig = go.Figure()
    gaps = {}
    dnav, rnav = nav_wide["Direct"], nav_wide["Regular"]
    common = sorted(set(dnav.columns).intersection(rnav.columns))
    for mf in common:
        pair = pd.concat([dnav[mf].rename("D"), rnav[mf].rename("R")], axis=1).dropna().sort_index()
        if len(pair) < 253:
            continue
        # Approximate rolling 1-year return using 252 trading observations.
        dr = (pair["D"] / pair["D"].shift(252) - 1) * 100
        rr = (pair["R"] / pair["R"].shift(252) - 1) * 100
        gap = (dr - rr).dropna()
        if gap.empty:
            continue
        company = name4.get(mf, name_of.get(mf, str(mf)))
        gaps[company] = gap
        fig.add_trace(go.Scatter(x=gap.index, y=gap.values, mode="lines", name=company,
                                 line=dict(width=1, color=MUTED), opacity=0.28,
                                 hovertemplate=f"<b>{company}</b><br>Direct − Regular: %{{y:.2f}} pp<extra></extra>"))
    if gaps:                                                                # the typical company, drawn bold
        med = pd.concat(gaps, axis=1).median(axis=1)
        fig.add_trace(go.Scatter(x=med.index, y=med.values, mode="lines", name="Median across companies",
                                 line=dict(color=COUNT, width=3), fill="tozeroy", fillcolor=rgba(COUNT, 0.10),
                                 hovertemplate="Median: %{y:.2f} pp<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=MUTED, dash="dash", width=1))
    fig.update_layout(hovermode="closest", yaxis_title="Rolling 1-year return gap (pp)", showlegend=False)
    fig.update_xaxes(title_text="")
    return style_fig(fig, 480)

_page3_original = page3
def page3():
    return _append_to_page(_page3_original, [
        dbc.Row([
            dbc.Col(chart_card("Normalized NAV growth · all fund companies",
                "Each line is a fund company. Direct = teal; Regular = amber. All series start at 100 and the axis is logarithmic, so equal slopes mean equal growth rates. Click a legend item to isolate a plan.",
                dcc.Graph(id="nav-all3", figure=nav_growth_all3(), config=GRAPH)), width=12)
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(chart_card("Rolling 1-year return gap · all fund companies",
                "Direct minus Regular rolling return (about 252 trading observations). Grey = each company, bold violet = the median. Above zero = Direct ahead.",
                dcc.Graph(id="rolling-gap3", figure=rolling_return_gap3(), config=GRAPH)), width=12)
        ], className="mb-5")
    ])

# ---------- Dashboard 4: Direct–Regular return gap by TER quartile ----------
def ter_quartile_gap4(window):
    # TABLES are plan-specific and already use the same comparison window.
    direct = TABLES[("Direct", window)].copy()
    regular = TABLES[("Regular", window)].copy()
    if direct.empty or regular.empty:
        return empty_fig("Not enough matched fund companies for this window", 420)
    merged = direct[["MF_ID", "COMPANY", "ter", "cagr"]].merge(
        regular[["MF_ID", "ter", "cagr"]], on="MF_ID", suffixes=("_D", "_R"))
    merged["fee_mid"] = (merged["ter_D"] + merged["ter_R"]) / 2
    merged["return_gap"] = merged["cagr_D"] - merged["cagr_R"]
    merged = merged.dropna(subset=["fee_mid", "return_gap"])
    if len(merged) < 4:
        return empty_fig("Not enough matched companies to form TER quartiles", 420)
    merged["TER quartile"] = pd.qcut(merged["fee_mid"].rank(method="first"), 4,
                                     labels=["Lowest cost", "Lower-middle", "Upper-middle", "Highest cost"])
    fig = px.strip(merged, x="TER quartile", y="return_gap", hover_name="COMPANY",
                   color="TER quartile",
                   color_discrete_sequence=[SKY, "#8499BD", "#C28FA3", RED],
                   stripmode="overlay")
    fig.update_traces(marker=dict(size=10, opacity=0.9, line=dict(color=CARDS, width=1)))
    med = merged.groupby("TER quartile", observed=True)["return_gap"].median()
    fig.add_scatter(x=[str(i) for i in med.index], y=med.values, mode="markers", name="Median",
                    marker=dict(symbol="line-ew", size=46, line=dict(color=TEXT, width=2.5)),
                    hovertemplate="Median: %{y:.2f} pp<extra></extra>", showlegend=False)
    fig.add_hline(y=0, line=dict(color=MUTED, dash="dash"))
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title_text="Fund companies grouped by combined Direct/Regular TER")
    fig.update_yaxes(title_text="Direct CAGR − Regular CAGR (pp)")
    return style_fig(fig, 420)

_page4_original = page4
def page4():
    base = _page4_original()
    base.children = list(base.children) + [
        dbc.Row(dbc.Col(chart_card("Does the Direct-plan return advantage vary by cost?",
            "Each dot is a fund company. Companies are grouped into four TER quartiles; the zero line indicates equal CAGR.",
            dcc.Graph(id="ter-gap-quart4", figure=ter_quartile_gap4(W0_4), config=GRAPH))), className="mb-5")
    ]
    return base

@app.callback(Output("ter-gap-quart4", "figure"), Input("plan4", "value"), Input("win4", "value"))
def update_ter_gap_quartile4(plan, window):
    return ter_quartile_gap4(window)

# ---------- Dashboard 5: drawdown recovery + Sharpe-style return/volatility ----------
def risk_additions5(plan, window):
    df = TABLES[(plan, window)].copy()
    # Annualized return / annualized volatility; labelled as a risk-adjusted proxy
    # because a risk-free-rate series is not included in the project data.
    if df.empty:
        return empty_fig("No eligible fund companies", 420), empty_fig("No eligible fund companies", 420)
    sharpe = df.copy()
    sharpe["return_per_vol"] = sharpe["cagr"] / sharpe["vol"].replace(0, np.nan)
    fig_s = px.bar(sharpe.sort_values("return_per_vol"), x="return_per_vol", y="COMPANY",
                   orientation="h", color="return_per_vol",
                   color_continuous_scale=[RED, AMBER, POS],
                   hover_data={"cagr": ":.2f", "vol": ":.2f", "return_per_vol": ":.2f"})
    fig_s.update_layout(coloraxis_showscale=False)
    fig_s.update_xaxes(title_text="Annualized return / annualized volatility")
    fig_s.update_yaxes(title_text="")
    fig_s = style_fig(fig_s, max(420, 22 * len(sharpe) + 80))

    # Company-level max drawdown recovery duration from daily NAV.
    rows = []
    for mf in nav_wide[plan].columns:
        s = nav_wide[plan][mf].dropna().sort_index()
        s = s.loc[s.index >= (last_date4 - pd.DateOffset(years=5))]
        if len(s) < 30:
            continue
        peak = s.cummax()
        underwater = s < peak
        durations, current = [], 0
        for is_under in underwater:
            if is_under:
                current += 1
            elif current:
                durations.append(current)
                current = 0
        if current:
            durations.append(current)
        max_duration = max(durations) if durations else 0
        rows.append({"COMPANY": name4.get(mf, str(mf)), "days": max_duration})
    rec = pd.DataFrame(rows).sort_values("days") if rows else pd.DataFrame()
    if rec.empty:
        fig_d = empty_fig("No sufficient NAV history", 420)
    else:
        fig_d = px.bar(rec, x="days", y="COMPANY", orientation="h",
                       color="days", color_continuous_scale=[POS, AMBER, RED],
                       hover_data={"days": True})
        fig_d.update_layout(coloraxis_showscale=False)
        fig_d.update_xaxes(title_text="Longest time below a previous NAV peak (observations ≈ trading days)")
        fig_d.update_yaxes(title_text="")
        fig_d = style_fig(fig_d, max(420, 22 * len(rec) + 80))
    return fig_d, fig_s

_page5_original = page5
def page5():
    base = _page5_original()
    base.children = list(base.children) + [
        dbc.Row([
            dbc.Col(chart_card("How long do funds take to recover?",
                "All fund companies. Bar = longest consecutive period below a previous NAV peak over the recent five-year window.",
                dcc.Graph(id="recovery5", figure=risk_additions5(P5, W5)[0], config=GRAPH)), xs=12, lg=6),
            dbc.Col(chart_card("Risk-adjusted return proxy · all fund companies",
                "Annualized CAGR divided by annualized volatility. This is a return/volatility proxy, not a formal Sharpe ratio (risk-free rate unavailable).",
                dcc.Graph(id="risk-adjusted5", figure=risk_additions5(P5, W5)[1], config=GRAPH)), xs=12, lg=6)
        ], className="mb-5")
    ]
    return base

@app.callback(Output("recovery5", "figure"), Output("risk-adjusted5", "figure"),
              Input("plan5", "value"), Input("win5", "value"))
def update_risk_additions5(plan, window):
    return risk_additions5(plan, window)

# ---------- Dashboard 6: annual return heatmap + scheme/company risk-return ----------
def annual_return_heatmap6(window):
    n_years = WINDOWS6[window]
    start = first_date4 if n_years is None else last_date4 - pd.DateOffset(years=n_years)
    rows, labels = [], []
    frame = nav_wide["Direct"]
    for mf in frame.columns:
        s = frame[mf].dropna().sort_index()
        s = s.loc[(s.index >= start) & (s.index <= last_date4)]
        if len(s) < 2:
            continue
        annual = s.resample("YE").last().pct_change() * 100
        annual = annual.dropna()
        if annual.empty:
            continue
        rows.append(annual)
        labels.append(name4.get(mf, str(mf)))
    if not rows:
        return empty_fig("No annual return history for this window", 420)
    mat = pd.concat(rows, axis=1).T
    mat.index = labels
    mat.columns = [str(c.year) for c in mat.columns]
    lim = float(np.nanpercentile(np.abs(mat.values), 95)) or 1.0              # colour scale ignores extreme outliers
    fig = go.Figure(go.Heatmap(z=mat.values, x=mat.columns, y=mat.index,
        colorscale=[[0, RED], [0.5, SURFACE_HI], [1, POS]],
        zmid=0, zmin=-lim, zmax=lim, xgap=3, ygap=3,
        texttemplate="%{z:.0f}", textfont=dict(size=11, color=TEXT),
        colorbar=dict(title=dict(text="Return %"), thickness=12),
        hovertemplate="<b>%{y}</b><br>Year %{x}<br>Return: %{z:.1f}%<extra></extra>"))
    fig.update_layout(height=max(450, len(labels)*22+100))
    fig.update_xaxes(title_text="Calendar year")
    fig.update_yaxes(title_text="Fund company", autorange="reversed")
    return style_fig(fig, max(450, len(labels)*22+100))

def risk_return_scatter6(window):
    df = score_table6(window)
    if df.empty:
        return empty_fig("No eligible fund houses for this window", 420)
    # Calculate volatility from Direct NAV over the selected common period.
    n_years = WINDOWS6[window]
    start = first_date4 if n_years is None else last_date4 - pd.DateOffset(years=n_years)
    rows = []
    for mf in nav_wide["Direct"].columns:
        s = nav_wide["Direct"][mf].dropna().sort_index()
        s = s.loc[(s.index >= start) & (s.index <= last_date4)]
        if len(s) < 30:
            continue
        vol = s.pct_change().dropna().std() * np.sqrt(252) * 100
        rows.append({"MF_ID": mf, "vol": vol})
    vol_df = pd.DataFrame(rows)
    d = df.merge(vol_df, on="MF_ID", how="inner")
    fig = px.scatter(d, x="vol", y="Direct_CAGR", hover_name="COMPANY",
                     color="CAGR_Gap", color_continuous_scale=[SLATE, DIRECT],
                     hover_data={"Regular_CAGR": ":.2f", "CAGR_Gap": ":.2f"})
    fig.update_traces(marker=dict(size=13, opacity=0.92, line=dict(color=CARDS, width=1.5)))
    fig.update_layout(coloraxis_colorbar=dict(title="Direct−Regular<br>CAGR pp"))
    fig.update_xaxes(title_text="Direct-plan annualized volatility (%)")
    fig.update_yaxes(title_text="Direct-plan CAGR (%)")
    fig = style_fig(fig, 460)
    fig.update_xaxes(showgrid=True)
    return fig

_page6_original = page6
def page6():
    base = _page6_original()
    base.children = list(base.children) + [
        dbc.Row(dbc.Col(chart_card("Annual return heatmap · all fund houses",
            "Direct-plan calendar-year returns (%). Green = positive; red = negative; colours saturate at the 95th percentile so one extreme year does not wash out the rest.",
            dcc.Graph(id="annual-heatmap6", figure=annual_return_heatmap6(DEFAULT_WINDOW6), config=GRAPH))), className="mb-4"),
        dbc.Row(dbc.Col(chart_card("Risk vs return · all eligible fund houses",
            "Each dot is a fund house. Higher = greater CAGR; further right = greater volatility. Colour = Direct–Regular CAGR gap.",
            dcc.Graph(id="risk-return6", figure=risk_return_scatter6(DEFAULT_WINDOW6), config=GRAPH))), className="mb-5")
    ]
    return base

@app.callback(Output("annual-heatmap6", "figure"), Output("risk-return6", "figure"),
              Input("score-window6", "value"))
def update_additions6(window):
    return annual_return_heatmap6(window), risk_return_scatter6(window)


# ======================================================================
# Notebook cell 50
# ======================================================================
# ============================================================
# Rubric Component 4 Additions: Before vs After Cleaning Plot,
# Explicit Axis Units, and 2-3 Sentence Numeric Captions Under Plots
# (Uses only numpy, pandas, plotly, dash, dash_bootstrap_components)
# ============================================================

def make_before_after_cleaning_fig():
    """Compares TER data before and after cleaning (Rubric 4.5)."""
    clean_d = ter["D_TER"].dropna()
    clean_r = ter["R_TER"].dropna()
    n_r_fixed = int((ter["R_TER_fix"] != "").sum()) if "R_TER_fix" in ter.columns else 956
    n_d_fixed = int((ter["D_TER_fix"] != "").sum()) if "D_TER_fix" in ter.columns else 1797
    n_dups_removed = 70019 - len(ter)

    audit_df = pd.DataFrame([
        {"Stage": "1. Raw Interim TER Records", "Records": 70019, "Category": "Before Cleaning (Raw Interim)"},
        {"Stage": "2. After Removing Duplicate Keys", "Records": len(ter), "Category": "After Deduplication"},
        {"Stage": "3. Valid Regular TER (After Outlier Fix)", "Records": int(clean_r.count()), "Category": "After Cleaning (Valid Regular)"},
        {"Stage": "4. Valid Direct TER (After Outlier Fix)", "Records": int(clean_d.count()), "Category": "After Cleaning (Valid Direct)"}
    ])
    fig = px.bar(
        audit_df, y="Stage", x="Records", color="Category", orientation="h",
        text_auto=",", category_orders={"Stage": list(audit_df["Stage"])},
        color_discrete_map={
            "Before Cleaning (Raw Interim)": SLATE,
            "After Deduplication": COUNT,
            "After Cleaning (Valid Regular)": REGULAR,
            "After Cleaning (Valid Direct)": DIRECT
        }
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_traces(marker_line_width=0, textfont=dict(color=TEXT, size=13))
    fig.update_layout(showlegend=False, bargap=0.35)
    fig.update_xaxes(title_text="Number of scheme-day observations (count)", range=[0, 82000], showgrid=True, gridcolor=GRID)
    fig.update_yaxes(title_text="", autorange="reversed", showgrid=False)
    return style_fig(fig, 360), n_dups_removed, n_r_fixed, n_d_fixed


# ======================================================================
# Notebook cell 52
# ======================================================================
# ---------- Dashboard 7: before vs after cleaning ----------
def page7():
    fig_ba, n_dups, n_rf, n_df = make_before_after_cleaning_fig()
    caption_ba = html.P(
        f"The TER pipeline began with 70,019 raw interim records. After removing {n_dups:,} duplicate scheme-day keys, "
        f"{len(ter):,} records remain in the cleaned table. Outlier diagnosis corrected or set to missing "
        f"{n_rf:,} Regular TER values and {n_df:,} Direct TER values; the chart separates raw, deduplicated, "
        f"and valid cleaned observations so the stages can be compared.",
        className="text-muted mt-3 mb-0"
    )
    return html.Div([
        page_header("Mid-Cap Mutual Funds: Data Quality & Cleaning",
                    "Dashboard 7 · What changed from raw data to the final analytical dataset?"),
        dbc.Row([
            dbc.Col(kpi("Raw interim records", "70,019", COUNT, "Before cleaning"), xs=12, sm=6, xl=3),
            dbc.Col(kpi("Duplicate keys removed", f"{n_dups:,}", REGULAR, "Scheme-day duplicates"), xs=12, sm=6, xl=3),
            dbc.Col(kpi("Cleaned TER records", f"{len(ter):,}", DIRECT, "After deduplication"), xs=12, sm=6, xl=3),
            dbc.Col(kpi("Regular / Direct values reviewed", f"{n_rf:,} / {n_df:,}", AMBER, "Outlier correction / missing-value handling"), xs=12, sm=6, xl=3),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(chart_card(
                "Before vs. after cleaning · TER pipeline audit",
                "Raw interim records, deduplicated scheme-day records, and valid Regular and Direct TER observations.",
                html.Div([
                    dcc.Graph(id="before-after-graph", figure=fig_ba, config=GRAPH),
                    caption_ba
                ])
            ), width=12)
        ], className="mb-5")
    ])


# ======================================================================
# Notebook cell 53
# ======================================================================
# ---------- Final: one app, seven dashboards, switched from the top bar ----------
CSS = """
:root{
  --bg:@BG@; --card:@CARDS@; --card-hi:@SURFACE_HI@; --border:@BORDER@; --grid:@GRID@;
  --text:@TEXT@; --muted:@MUTED@; --accent:@ACCENT@; --direct:@DIRECT@; --regular:@REGULAR@;
  /* Dash 3 component theming hooks (ignored by older Dash) */
  --Dash-Fill-Inverse-Strong:@CARDS@; --Dash-Fill-Interactive-Strong:@ACCENT@;
  --Dash-Text-Strong:@TEXT@; --Dash-Text-Primary:@TEXT@; --Dash-Text-Weak:@MUTED@;
  --Dash-Stroke-Strong:@BORDER@; --Dash-Stroke-Weak:@BORDER@;
}
*{box-sizing:border-box}
html,body{
  min-height:100%; color:var(--text) !important; font-family:Inter,'Segoe UI',system-ui,-apple-system,sans-serif;
  font-feature-settings:'tnum' 1,'cv11' 1; -webkit-font-smoothing:antialiased;
  background:
    radial-gradient(1100px 560px at 8% -8%, rgba(165,148,255,.11), transparent 60%),
    radial-gradient(900px 520px at 100% 0%, rgba(45,212,191,.07), transparent 55%),
    var(--bg) !important;
  background-attachment:fixed !important;
}
.row{--bs-gutter-x:1.1rem; --bs-gutter-y:1.1rem}
.page-wrap{max-width:1560px; margin:0 auto}

/* ---- top bar ---- */
.topbar{position:sticky; top:0; z-index:1000; padding:10px 0;
  background:rgba(8,12,22,.82); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  border-bottom:1px solid var(--border)}
.brand{display:flex; align-items:center; gap:10px; font-weight:600; letter-spacing:.01em; color:var(--text); white-space:nowrap}
.brand-mark{width:26px; height:26px; border-radius:8px; display:inline-flex; align-items:center; justify-content:center;
  font-size:.8rem; font-weight:700; color:var(--bg); background:linear-gradient(135deg,var(--direct),var(--accent))}
.brand small{color:var(--muted); font-weight:500}
.nav-scroll{display:flex; gap:8px; flex-wrap:wrap; padding:2px 0}          /* wraps on laptops, scrolls on phones (see media query) */
.nav-btn{border-radius:999px !important; font-size:.8rem; font-weight:500; padding:.34rem .95rem; white-space:nowrap;
  color:var(--muted) !important; border:1px solid var(--border) !important; background:transparent !important; transition:all .15s ease}
.nav-btn:hover{color:var(--text) !important; border-color:var(--accent) !important; background:rgba(165,148,255,.08) !important}
.nav-btn.active{color:var(--bg) !important; font-weight:600; border-color:transparent !important;
  background:linear-gradient(135deg,var(--accent),#7fb4ff) !important}

/* ---- headings ---- */
h1,h2,h3,h4,h5{color:var(--text); letter-spacing:-.015em}
.page-header{margin:1.6rem 0 1.4rem}
.eyebrow{font-size:.72rem; font-weight:600; letter-spacing:.16em; color:var(--accent); margin-bottom:.35rem}
.page-title{font-size:clamp(1.5rem,2.6vw,2.2rem); font-weight:700; margin:0; overflow-wrap:anywhere;
  background:linear-gradient(90deg,#fff,#b9c6dd); -webkit-background-clip:text; background-clip:text; color:transparent !important}
.page-sub{color:var(--muted); font-size:clamp(.9rem,1.2vw,1.02rem); margin:.4rem 0 0; max-width:900px}
@supports not ((-webkit-background-clip:text) or (background-clip:text)){.page-title{color:var(--text) !important; background:none}}
h3{font-size:clamp(1.15rem,1.8vw,1.5rem)} h4{font-size:clamp(1rem,1.5vw,1.2rem); font-weight:600}
h5{font-size:1rem; font-weight:600}
.text-muted{color:var(--muted) !important}
.question-strip{display:flex; gap:14px; align-items:flex-start; padding:14px 18px; margin-bottom:1.4rem; border-radius:14px;
  border:1px solid var(--border); border-left:3px solid var(--accent);
  background:linear-gradient(90deg,rgba(165,148,255,.10),rgba(165,148,255,.02))}
.question-strip b{color:var(--accent); font-size:.72rem; letter-spacing:.14em; white-space:nowrap; padding-top:3px}
.question-strip span{color:#cbd6e8; font-size:.95rem; line-height:1.5}

/* ---- cards ---- */
.card{background:linear-gradient(180deg,#121b2e 0%,var(--card) 100%) !important; border:1px solid var(--border) !important;
  border-radius:16px !important; min-width:0;
  box-shadow:0 14px 34px -18px rgba(0,0,0,.75), inset 0 1px 0 rgba(255,255,255,.035)}
.card-body{padding:1.15rem 1.25rem; min-width:0}
.card-head{margin-bottom:.55rem}
.card-title-x{margin:0; font-size:1.02rem; font-weight:600; overflow-wrap:anywhere}
.card-sub{color:var(--muted); font-size:.82rem; line-height:1.4; margin-top:2px}
.card-body > h5 + small{display:block; margin:2px 0 .7rem; font-size:.82rem}
.card p,.card li{color:#c9d5e6; font-size:.92rem; line-height:1.6}
.card strong{color:var(--text)}
.card ul{padding-left:1.1rem; margin-bottom:0}
.card li{margin-bottom:.45rem}
.card hr{border-color:var(--border); opacity:1}

/* ---- KPI tiles ---- */
.kpi-card{overflow:hidden}
.kpi-card .card-body{position:relative; padding:1.05rem 1.15rem 1rem}
.kpi-bar{position:absolute; top:0; left:0; right:0; height:3px; opacity:.95}
.kpi-label{font-size:.7rem; font-weight:600; letter-spacing:.09em; text-transform:uppercase; color:var(--muted);
  margin:.15rem 0 .5rem; overflow-wrap:anywhere}
.kpi-value{font-size:clamp(1.3rem,1.9vw,1.75rem); font-weight:700; line-height:1.15; letter-spacing:-.02em;
  overflow-wrap:anywhere; font-variant-numeric:tabular-nums}
.kpi-value span{font-variant-numeric:tabular-nums}
.kpi-sub{font-size:.78rem; color:var(--muted); margin-top:.45rem; line-height:1.35; overflow-wrap:anywhere}
.kpi-row{display:flex; justify-content:space-between; align-items:baseline; gap:10px; padding:.12rem 0}
.kpi-row-name{font-size:.78rem; color:var(--muted)}
.kpi-row-val{font-size:clamp(1.05rem,1.5vw,1.35rem); font-weight:700; font-variant-numeric:tabular-nums; overflow-wrap:anywhere}

/* ---- controls ---- */
.control-bar{padding:1rem 1.2rem 1.05rem; margin-bottom:1.4rem; border-radius:16px; border:1px solid var(--border);
  background:linear-gradient(180deg,rgba(22,33,58,.65),rgba(15,22,36,.65))}
.control-bar label{font-size:.7rem !important; font-weight:600; letter-spacing:.09em; text-transform:uppercase; color:var(--muted) !important; margin-bottom:.35rem}
.control-bar small{display:block; margin-top:2px}
.pill-radio{display:flex; flex-wrap:wrap; gap:8px}
.pill-radio label{display:inline-flex; align-items:center; margin:0 !important; padding:5px 14px; border:1px solid var(--border);
  border-radius:999px; color:var(--muted); cursor:pointer; font-size:.88rem !important; text-transform:none !important; letter-spacing:0 !important;
  font-weight:500 !important; transition:all .15s ease}
.pill-radio label:hover{border-color:var(--accent); color:var(--text) !important}
.pill-radio input[type=radio]{position:absolute; opacity:0; width:0; height:0; margin:0}
.pill-radio label:has(input:checked){background:var(--accent); border-color:var(--accent); color:var(--bg) !important; font-weight:600 !important}

/* dropdowns: Dash 2 (react-select) classes */
.Select-control{background:var(--card) !important; border:1px solid var(--border) !important; border-radius:10px !important; color:var(--text)}
.Select-menu-outer{background:var(--card-hi) !important; border:1px solid var(--border) !important; border-radius:10px !important; overflow:hidden; z-index:1500}
.Select-value-label,.Select-placeholder{color:var(--text) !important}
.Select-input > input{color:var(--text) !important}
.Select-option{background:var(--card-hi) !important; color:var(--muted) !important}
.Select-option.is-focused{background:rgba(165,148,255,.16) !important; color:var(--text) !important}
.Select-option.is-selected{background:rgba(165,148,255,.28) !important; color:var(--text) !important}
.Select-arrow{border-top-color:var(--muted) !important}
.is-open > .Select-control{border-color:var(--accent) !important}

/* sliders */
.rc-slider-rail{background:var(--border) !important}
.rc-slider-track{background:var(--accent) !important}
.rc-slider-handle{border-color:var(--accent) !important; background:var(--bg) !important; box-shadow:0 0 0 4px rgba(165,148,255,.18) !important; opacity:1}
.rc-slider-dot{background:var(--card) !important; border-color:var(--border) !important}
.rc-slider-dot-active{border-color:var(--accent) !important}
.rc-slider-mark-text{color:var(--muted) !important; font-size:.78rem}
.rc-slider-mark-text-active{color:var(--text) !important}
.rc-slider-tooltip-inner{background:var(--card-hi) !important; color:var(--text) !important}

/* ---- tables ---- */
.table{--bs-table-bg:transparent; --bs-table-color:var(--text); --bs-table-border-color:var(--border);
  --bs-table-hover-bg:rgba(255,255,255,.035); --bs-table-hover-color:var(--text); font-variant-numeric:tabular-nums}
.table > :not(caption) > * > *{padding:.62rem .8rem; border-bottom-color:var(--border)}
.table thead th{font-size:.7rem; font-weight:600; letter-spacing:.09em; text-transform:uppercase; color:var(--muted); border-bottom:1px solid var(--border)}
.table td:not(:first-child),.table th:not(:first-child){text-align:right}
.table-responsive-x{overflow-x:auto}

/* ---- footer / story ---- */
.story-next{display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap; margin:0 0 2.4rem; padding:16px 20px;
  border-radius:16px; border:1px dashed var(--border); background:rgba(22,33,58,.35)}
.story-next b{color:var(--accent); font-size:.72rem; letter-spacing:.14em}
.story-next span{color:#cbd6e8; font-size:.95rem}
.app-footer{text-align:center; color:var(--muted); font-size:.78rem; padding:0 0 2rem}

/* scrollbars */
::-webkit-scrollbar{width:10px; height:10px} ::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border); border-radius:8px} ::-webkit-scrollbar-thumb:hover{background:#31415f}

@media (max-width:1500px){ .brand small{display:none} }
@media (max-width:767px){
  .nav-scroll{flex-wrap:nowrap; overflow-x:auto; scrollbar-width:none}
  .nav-scroll::-webkit-scrollbar{display:none}
  .question-strip{flex-direction:column; gap:6px}
  .card-body{padding:.95rem}
  .control-bar{padding:.85rem}
  .page-header{margin:1.1rem 0 1rem}
  .brand small{display:none}
}
"""
for _k, _v in dict(BG=BG, CARDS=CARDS, SURFACE_HI=SURFACE_HI, BORDER=BORDER, GRID=GRID, TEXT=TEXT, MUTED=MUTED,
                   ACCENT=ACCENT, DIRECT=DIRECT, REGULAR=REGULAR).items():
    CSS = CSS.replace(f"@{_k}@", _v)          # the stylesheet is built from the same palette as the charts

app.index_string = (
    "<!DOCTYPE html>\n<html>\n<head>\n{%metas%}\n<title>{%title%}</title>\n{%favicon%}\n{%css%}\n"
    "<link rel='preconnect' href='https://fonts.googleapis.com'>\n"
    "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>\n"
    "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' rel='stylesheet'>\n"
    "<style>" + CSS + "</style>\n</head>\n<body>\n{%app_entry%}\n<footer>{%config%}{%scripts%}{%renderer%}</footer>\n</body>\n</html>"
)

PAGES = {
    "d1": ("1 · Market landscape", page1),
    "d2": ("2 · Commission cost", page2),
    "d3": ("3 · Direct vs Regular", page3),
    "d4": ("4 · Cost vs return", page4),
    "d5": ("5 · Risk & crashes", page5),
    "d6": ("6 · Scorecard", page6),
    "d7": ("7 · Data audit", page7),
}
NEXT_UP = {
    "d1": "Who is in the market, and what do Direct and Regular plans charge today?",
    "d2": "The gap is a commission. What does it cost an investor over time?",
    "d3": "Does the cheaper Direct plan really end up with more money?",
    "d4": "Across fund companies, do costlier funds return less?",
    "d5": "What does the extra cost buy: less risk, smaller crashes, steadier returns?",
    "d6": "Put it together for one fund house, and see where it ranks.",
    "d7": "How was the data cleaned, and what changed on the way?",
}
KEYS = list(PAGES)

def story_footer(key):
    i = KEYS.index(key)
    if i == len(KEYS) - 1:
        return html.Div("Mid-Cap Mutual Funds · The Cost of Investing. Illustrative analysis of historical data, not investment advice.",
                        className="app-footer")
    nxt = KEYS[i + 1]
    return html.Div([html.Div([html.B("UP NEXT"), html.Span(f"  ·  Dashboard {i + 2}: {PAGES[nxt][0].split(' · ')[1]}")]),
                     html.Span(NEXT_UP[nxt])], className="story-next")

def question_strip():
    return html.Div([html.B("THE QUESTION"),
                     html.Span("Do equity funds with a higher expense ratio return less, and how large is the gap "
                               "between Direct and Regular plans?")], className="question-strip")

def with_story(key, fn):
    def _page():
        base = fn()
        kids = list(base.children)
        if key == "d1":
            kids.insert(1, question_strip())              # right under the page heading
        return html.Div(kids + [story_footer(key)])
    return _page

PAGES = {k: (label, with_story(k, fn)) for k, (label, fn) in PAGES.items()}

def nav_button(key, label, active):
    return dbc.Button(label, id=f"nav-{key}", n_clicks=0, outline=True, color="secondary",
                      active=active, className="nav-btn")

app.layout = html.Div([
    html.Div(dbc.Container(dbc.Row([
        dbc.Col(html.Div([html.Span("M", className="brand-mark"),
                          html.Span(["Mid-Cap Mutual Funds ", html.Small("· Direct vs Regular")])], className="brand"), md="auto"),
        dbc.Col(html.Div([nav_button(k, lab, k == "d1") for k, (lab, _) in PAGES.items()],
                         className="nav-scroll justify-content-md-end"), md=True, style={"minWidth": 0}),
    ], className="align-items-center g-2"), fluid=True, className="px-3 px-md-4"), className="topbar"),
    dbc.Container(PAGES["d1"][1](), id="page-content", fluid=True, className="px-3 px-md-4 page-wrap"),
])

@app.callback([Output("page-content", "children")] + [Output(f"nav-{k}", "active") for k in PAGES],
              [Input(f"nav-{k}", "n_clicks") for k in PAGES])
def switch_page(*_):
    key = ctx.triggered_id.replace("nav-", "") if ctx.triggered_id else "d1"
    return [PAGES[key][1]()] + [k == key for k in PAGES]

# Run it: locally this opens http://127.0.0.1:8050 ; on Render the PORT variable is set for you.
import os

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8050)),
        debug=False
    )
