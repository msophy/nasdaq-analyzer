import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd

st.set_page_config(page_title="محلل الناسداك", page_icon="📈", layout="centered")
st.title("📈 محلل الناسداك - فريم 15 دقيقة")

import nasdaq_analyzer as na

SYMBOLS = ["^NDX", "QQQ", "NQ=F"]


@st.cache_data(ttl=300, show_spinner=False)
def load():
    last_err = None
    for sym in SYMBOLS:
        try:
            df = na.fetch(sym)
            if len(df) > 60:
                return sym, df
            last_err = f"{sym}: بيانات قليلة ({len(df)} شمعة)"
        except Exception as e:
            last_err = f"{sym}: {e}"
    raise RuntimeError(last_err)


@st.fragment(run_every="15m")
def dashboard():
    with st.spinner("جاري تحميل البيانات..."):
        try:
            sym, df = load()
            res = na.analyze(df)
        except Exception as e:
            st.error(f"مشكلة في جلب البيانات: {e}")
            return

    st.caption(f"المصدر: {sym}")
    c1, c2 = st.columns(2)
    c1.metric("السعر", f"{res['price']:,.1f}")
    c2.metric("النقاط", f"{res['score']:+d} من ±5")

    if res["score"] >= 3:
        st.success(f"الإشارة: {res['signal']}")
    elif res["score"] <= -3:
        st.error(f"الإشارة: {res['signal']}")
    else:
        st.info(f"الإشارة: {res['signal']}")

    for n in res["notes"]:
        st.write("•", n)

    st.write(f"**دعم (آخر 8 ساعات):** {res['support']:,.1f}  |  **مقاومة:** {res['resistance']:,.1f}")
    if res["levels"]:
        l = res["levels"]
        st.write(f"**وقف خسارة:** {l['SL']:,.1f}  |  **هدف 1:** {l['TP1']:,.1f}  |  **هدف 2:** {l['TP2']:,.1f}")

    chart = pd.DataFrame({
        "السعر": df["Close"],
        "EMA21": na.ema(df["Close"], 21),
        "EMA50": na.ema(df["Close"], 50),
    }).tail(120)
    st.line_chart(chart)
    st.caption(f"آخر شمعة مقفولة: {res['time']}")


dashboard()
st.warning("⚠️ للتعليم فقط وليس توصية تداول. البيانات مجانية وقد تتأخر. جرّب على حساب تجريبي أولًا.")
