"""
Shared look and feel for the dashboard: page CSS and the top navbar.
Every page calls theme.apply(active=<page key>) right after st.set_page_config().
"""
import plotly.io as pio
import streamlit as st

NAVY, NAVY_2, BLUE = "#0b1f3a", "#143564", "#1b4a8a"
GOLD, TEAL, INK, MUTED = "#e9b949", "#124e44", "#15233a", "#5b6b85"

BRAND = "Where VUP misses the poor"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, .stApp, .stMarkdown, .stMetric, .stButton, .stDownloadButton, .stSelectbox, .stCheckbox, .stRadio,
.stTextInput, .stNumberInput, .stSlider, .stDataFrame, .stTabs, .stExpander, .stAlert, .stCaption,
p, h1, h2, h3, h4, h5, h6, li, td, th, label, button, input, select, textarea {
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
}

/* ---- page frame ---- */
.stApp { background: radial-gradient(1200px 500px at 10% -10%, #e4ebf7 0%, #f4f6fb 55%) fixed; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 4.4rem; padding-bottom: 3rem; max-width: 1480px; }

/* hide the anchor-link icon Streamlit adds next to every heading */
[data-testid="stHeaderActionElements"], .stHeadingWithActionElements a, h1 a, h2 a, h3 a, h4 a { display: none !important; }

h1, h2, h3 { color: #0b1f3a; font-weight: 700; letter-spacing: -0.01em; }
h2 { font-size: 1.55rem; }
h3 { font-size: 1.15rem; margin-top: .6rem; }
.vup-page-title { font-size: 1.9rem; font-weight: 800; color: #0b1f3a; margin: 0 0 .2rem 0; letter-spacing: -0.02em; }
.vup-lead { color: #5b6b85; font-size: .98rem; max-width: 70rem; margin-bottom: 1.4rem; }

/* ---- navbar ---- */
.st-key-vup-nav {
  background: linear-gradient(100deg, #0b1f3a 0%, #143564 55%, #1b4a8a 100%);
  border-radius: 20px; margin-bottom: 1.6rem;
  min-height: 4.75rem; padding: 0 1.6rem !important; box-sizing: border-box;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0 !important;
  box-shadow: 0 14px 34px rgba(11, 31, 58, .28);
  position: relative; overflow: hidden;
}
.st-key-vup-nav::after {
  content: ""; position: absolute; right: -80px; top: -120px; width: 320px; height: 320px; border-radius: 50%;
  background: radial-gradient(circle, rgba(233,185,73,.28) 0%, rgba(233,185,73,0) 70%); pointer-events: none;
}
/* flatten Streamlit's inner wrappers so nothing adds top or bottom space */
.st-key-vup-nav [data-testid="stVerticalBlock"], .st-key-vup-nav [data-testid="stElementContainer"],
.st-key-vup-nav [data-testid="stMarkdown"], .st-key-vup-nav [data-testid="stMarkdownContainer"] {
  width: 100%; margin: 0 !important; padding: 0 !important; gap: 0 !important; min-height: 0 !important;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.vup-title { color: #fff; font-weight: 800; font-size: 1.45rem; line-height: 1; letter-spacing: -0.01em; text-align: center; margin: 0 !important; padding: 0 !important; }
/* ---- sidebar ---- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b1f3a 0%, #0e2748 100%) !important;
  border-right: 1px solid rgba(255,255,255,.06);
}
[data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] a { color: #e8eef8; }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a { border-radius: 10px; margin: 2px 0; }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,.08); }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span { background: #17396a; color: #fff; }
/* ---- metric cards ---- */
[data-testid="stMetric"] {
  background: #fff; border: 1px solid #e3e9f3; border-radius: 16px; padding: 1rem 1.2rem 1rem 1.35rem;
  box-shadow: 0 8px 22px rgba(21, 35, 58, .06); position: relative; overflow: hidden; transition: transform .15s ease, box-shadow .15s ease;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(21, 35, 58, .10); }
[data-testid="stMetric"]::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 5px; background: linear-gradient(180deg, #e9b949, #1b4a8a); }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { font-size: .76rem !important; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: #5b6b85; }
[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 800; color: #0b1f3a; letter-spacing: -0.02em; }
[data-testid="stMetricDelta"] { font-weight: 600; }

/* ---- tabs (Streamlit >= 1.6x renders tabs with role="tablist" / data-testid="stTab") ---- */
[data-testid="stTabs"] [role="tablist"] { gap: .35rem; background: #e7edf6; padding: .3rem; border-radius: 999px; width: max-content; max-width: 100%; border-bottom: none !important; }
[data-testid="stTabs"] [role="tablist"]::after, [data-testid="stTabs"] [role="tablist"]::before { display: none; }
[data-testid="stTab"], [data-testid="stTabs"] [role="tab"] { border-radius: 999px; padding: .45rem 1.15rem; height: auto; background: transparent; border-bottom: none !important; outline: none; }
[data-testid="stTab"] p, [data-testid="stTabs"] [role="tab"] p { font-weight: 600; color: #4a5a74; }
[data-testid="stTab"][aria-selected="true"], [data-testid="stTab"][data-selected="true"], [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: #0b1f3a; box-shadow: 0 4px 12px rgba(11,31,58,.25); border-bottom: none !important; }
[data-testid="stTab"][aria-selected="true"] p, [data-testid="stTab"][data-selected="true"] p, [data-testid="stTabs"] [role="tab"][aria-selected="true"] p { color: #fff; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"], [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }
[data-testid="stTabPanel"], [data-testid="stTabs"] [role="tabpanel"] { padding-top: 1.2rem; }

/* ---- widgets and blocks ---- */
.stButton button, .stDownloadButton button, .stFormSubmitButton button { border-radius: 999px; font-weight: 600; padding: .45rem 1.2rem; }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] { background: linear-gradient(100deg, #143564, #1b4a8a); border: none; }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid #e3e9f3; box-shadow: 0 6px 18px rgba(21,35,58,.05); }
[data-testid="stExpander"] details { border-radius: 14px; border: 1px solid #e3e9f3; background: #fff; box-shadow: 0 6px 18px rgba(21,35,58,.04); }
[data-testid="stExpander"] summary { font-weight: 600; }
[data-testid="stAlert"] { border-radius: 14px; }
[data-testid="stCaptionContainer"] p { color: #6b7a93; }
hr { border-color: #e3e9f3; }
.vup-section { display: flex; align-items: center; gap: .6rem; margin: 1.2rem 0 .4rem 0; }
.vup-section .dot { width: 10px; height: 10px; border-radius: 3px; background: linear-gradient(135deg, #e9b949, #1b4a8a); }
.vup-section h3 { margin: 0; }

/* ---- multistep form (Screener) ---- */
.vup-steps { display: flex; gap: .5rem; margin: .4rem 0 1.2rem 0; flex-wrap: wrap; }
.vup-step { flex: 1 1 150px; display: flex; align-items: center; gap: .6rem; padding: .6rem .9rem; border-radius: 12px;
  background: #fff; border: 1px solid #e3e9f3; color: #6b7a93; font-weight: 600; font-size: .9rem; }
.vup-step .n { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; background: #e7edf6; color: #4a5a74; font-size: .8rem; font-weight: 700; flex: none; }
.vup-step.active { border-color: #1b4a8a; color: #0b1f3a; box-shadow: 0 6px 16px rgba(27,74,138,.15); }
.vup-step.active .n { background: #0b1f3a; color: #fff; }
.vup-step.done { color: #124e44; border-color: #cfe3dc; }
.vup-step.done .n { background: #e9b949; color: #0b1f3a; }
.vup-check ol { padding-left: 1.3rem; margin: .4rem 0 0 0; }
.vup-check li { margin: .35rem 0; line-height: 1.45; }
.vup-pass { color: #124e44; font-weight: 700; }
.vup-fail { color: #b42318; font-weight: 700; }
.vup-art { color: #6b7a93; font-size: .85rem; }
.stButton button[kind="tertiary"] { color: #1b4a8a; text-decoration: underline; padding-left: 0; font-weight: 600; }
</style>
"""


def _plotly_defaults():
    t = pio.templates["plotly_white"]
    t.layout.font = dict(family="Inter, Segoe UI, sans-serif", color=INK, size=13)
    t.layout.paper_bgcolor = "rgba(0,0,0,0)"
    t.layout.plot_bgcolor = "rgba(0,0,0,0)"
    t.layout.colorway = [BLUE, GOLD, TEAL, "#7fa89a", "#b5791a", "#8aa3c7"]
    t.layout.xaxis.gridcolor = "#e8edf5"
    t.layout.yaxis.gridcolor = "#e8edf5"
    pio.templates.default = "plotly_white"


def navbar():
    """Top bar: the title text only. Page navigation stays in the sidebar."""
    with st.container(key="vup-nav"):
        st.markdown(f'<div class="vup-title">{BRAND}</div>', unsafe_allow_html=True)


def section(title: str):
    """A heading with a small colour mark; use instead of st.subheader for the main blocks."""
    st.markdown(f'<div class="vup-section"><span class="dot"></span><h3>{title}</h3></div>', unsafe_allow_html=True)


def apply(active: str = ""):
    """Inject the CSS and draw the navbar. Call once per page, after st.set_page_config(). `active` is kept for compatibility."""
    st.markdown(CSS, unsafe_allow_html=True)
    _plotly_defaults()
    navbar()
