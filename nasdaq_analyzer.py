"""
محلل الناسداك - بيتحدث كل 15 دقيقة
التشغيل:
    pip install yfinance pandas
    python nasdaq_analyzer.py
لإيقافه: Ctrl+C
تنبيه: أداة تعليمية، مش توصية تداول.
"""
import time
from datetime import datetime

import pandas as pd

TICKER = "^NDX"      # ناسداك 100 (ممكن تغيرها لـ NQ=F للعقود أو QQQ)
INTERVAL = "15m"
REFRESH_MIN = 15


def fetch(ticker=TICKER):
    import yfinance as yf
    df = yf.download(ticker, period="5d", interval=INTERVAL,
                     progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    # شيل الشمعة الأخيرة لو لسه ما اتقفلتش (عشان الإشارات ما تتغيرش)
    if len(df) > 1:
        last_start = df.index[-1]
        bar = pd.Timedelta(minutes=15)
        now = pd.Timestamp.now(tz=last_start.tz) if last_start.tzinfo else pd.Timestamp.now()
        if now < last_start + bar:
            df = df.iloc[:-1]
    return df


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


def atr(df, n=14):
    pc = df["Close"].shift()
    tr = pd.concat([df["High"] - df["Low"],
                    (df["High"] - pc).abs(),
                    (df["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    vol = df["Volume"].replace(0, 1)  # مؤشرات ^NDX غالبًا حجمها صفر
    day = df.index.date
    return (tp * vol).groupby(day).cumsum() / vol.groupby(day).cumsum()


def analyze(df):
    c = df["Close"]
    df = df.copy()
    df["ema9"], df["ema21"], df["ema50"] = ema(c, 9), ema(c, 21), ema(c, 50)
    df["rsi"] = rsi(c)
    macd = ema(c, 12) - ema(c, 26)
    df["macd_hist"] = macd - ema(macd, 9)
    df["atr"] = atr(df)
    df["vwap"] = vwap(df)

    r, p = df.iloc[-1], df.iloc[-2]
    score, notes = 0, []

    # الاتجاه
    if r.ema9 > r.ema21 > r.ema50:
        score += 2; notes.append("اتجاه صاعد (EMA9 > 21 > 50)")
    elif r.ema9 < r.ema21 < r.ema50:
        score -= 2; notes.append("اتجاه هابط (EMA9 < 21 < 50)")
    else:
        notes.append("المتوسطات متداخلة (اتجاه غير واضح)")

    # VWAP
    if r.Close > r.vwap:
        score += 1; notes.append("السعر فوق VWAP")
    else:
        score -= 1; notes.append("السعر تحت VWAP")

    # الزخم MACD
    if r.macd_hist > 0 and r.macd_hist > p.macd_hist:
        score += 1; notes.append("زخم صاعد يقوى (MACD)")
    elif r.macd_hist < 0 and r.macd_hist < p.macd_hist:
        score -= 1; notes.append("زخم هابط يقوى (MACD)")

    # RSI
    if r.rsi > 70:
        score -= 1; notes.append(f"RSI={r.rsi:.0f} تشبع شرائي (احتمال تصحيح)")
    elif r.rsi < 30:
        score += 1; notes.append(f"RSI={r.rsi:.0f} تشبع بيعي (احتمال ارتداد)")
    else:
        notes.append(f"RSI={r.rsi:.0f} محايد")

    # الإشارة
    if score >= 3:
        signal = "شراء 🟢"
    elif score <= -3:
        signal = "بيع 🔴"
    else:
        signal = "انتظار ⚪ (مفيش إشارة واضحة)"

    a = r.atr
    levels = {}
    if score >= 3:
        levels = {"SL": r.Close - 1.5 * a, "TP1": r.Close + 1.5 * a, "TP2": r.Close + 3 * a}
    elif score <= -3:
        levels = {"SL": r.Close + 1.5 * a, "TP1": r.Close - 1.5 * a, "TP2": r.Close - 3 * a}

    recent = df.tail(32)  # آخر 8 ساعات تقريبًا
    return {
        "time": df.index[-1], "price": float(r.Close), "score": score,
        "signal": signal, "notes": notes, "levels": levels,
        "support": float(recent.Low.min()), "resistance": float(recent.High.max()),
        "atr": float(a),
    }


def show(res):
    print("\n" + "=" * 44)
    print(f"آخر شمعة مقفولة: {res['time']}")
    print(f"السعر: {res['price']:,.1f}   |   ATR: {res['atr']:.1f}")
    print(f"الإشارة: {res['signal']}   (النقاط: {res['score']:+d} من ±5)")
    for n in res["notes"]:
        print("  •", n)
    print(f"دعم (آخر 8 ساعات): {res['support']:,.1f}   |   مقاومة: {res['resistance']:,.1f}")
    if res["levels"]:
        l = res["levels"]
        print(f"وقف خسارة: {l['SL']:,.1f}  |  هدف1: {l['TP1']:,.1f}  |  هدف2: {l['TP2']:,.1f}")
    print("⚠️ تعليمي فقط - مش توصية. جرب على حساب تجريبي الأول.")
    print("=" * 44)


def seconds_to_next_bar():
    now = datetime.now()
    mins = REFRESH_MIN - (now.minute % REFRESH_MIN)
    return mins * 60 - now.second + 5  # +5 ثواني عشان الشمعة تتقفل


def main():
    while True:
        try:
            show(analyze(fetch()))
        except Exception as e:
            print("خطأ في جلب/تحليل البيانات:", e)
        wait = seconds_to_next_bar()
        print(f"التحديث الجاي بعد {wait // 60} دقيقة...")
        time.sleep(wait)


if __name__ == "__main__":
    main()
