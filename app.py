import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

import nasdaq_analyzer as na

st.set_page_config(page_title="محلل الناسداك", page_icon="📈", layout="centered")

# تحديث الصفحة تلقائيًا كل 15 دقيقة
st_autorefresh(interval=15 * 60 * 1000, key="refresh15")

st.title("📈 محلل الناسداك 100 - فريم 15 دقيقة")


@st.cache_data(ttl=300)
def load():
    return na.fetch()


try:
    df = load()
    res = na.analyze(df)
except Exception as e:
    st.error(f"مشكلة في جلب البيانات: {e}")
    st.stop()

col1, col2 = st.columns(2)
col1.metric("السعر", f"{res['price']:,.1f}")
col2.metric("النقاط", f"{res['score']:+d} من ±5")

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
st.warning("⚠️ للتعليم فقط وليس توصية تداول. البيانات مجانية وقد تتأخر. جرّب على حساب تجريبي أولًا.")
import warnings
warnings.filterwarnings("ignore")
