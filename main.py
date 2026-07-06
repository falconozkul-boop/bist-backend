from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf

app = FastAPI(title="BIST AI Trader - Yahoo Finance Backend")

# Tarayıcıdaki HTML sayfasının bu API'ye istek atabilmesi için CORS'u herkese açıyoruz.
# İstersen buraya sadece kendi sitenin adresini de yazabilirsin (daha güvenli).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "BIST AI Trader Yahoo Finance backend calisiyor"}


@app.get("/quote/{symbol}")
def get_quote(symbol: str):
    """Tek bir hisse için fiyat döner. symbol örn: THYAO.IS"""
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        price = info.get("last_price")
        prev_close = info.get("previous_close")
        volume = info.get("last_volume")

        if price is None:
            raise HTTPException(status_code=404, detail=f"{symbol} icin fiyat bulunamadi")

        change_pct = 0.0
        if prev_close:
            change_pct = round(((price - prev_close) / prev_close) * 100, 2)

        return {
            "symbol": symbol,
            "price": round(float(price), 2),
            "previous_close": round(float(prev_close), 2) if prev_close else None,
            "change_pct": change_pct,
            "volume": int(volume) if volume else 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quotes")
def get_quotes(symbols: str = Query(..., description="Virgulle ayrilmis semboller, orn: THYAO.IS,GARAN.IS")):
    """Birden fazla hisse icin toplu fiyat doner."""
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not sym_list:
        raise HTTPException(status_code=400, detail="En az bir sembol girin")

    results = {}
    # yfinance'in toplu indirme ozelligini kullaniyoruz (tek istekte daha hizli)
    try:
        data = yf.download(
            tickers=" ".join(sym_list),
            period="2d",
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Toplu veri alinamadi: {e}")

    for sym in sym_list:
        try:
            if len(sym_list) == 1:
                df = data
            else:
                df = data[sym]
            df = df.dropna()
            if df.empty:
                results[sym] = {"error": "veri yok"}
                continue
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            price = float(last["Close"])
            prev_close = float(prev["Close"])
            change_pct = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0.0
            results[sym] = {
                "price": round(price, 2),
                "previous_close": round(prev_close, 2),
                "change_pct": change_pct,
                "volume": int(last["Volume"]) if not df["Volume"].isna().all() else 0,
            }
        except Exception as e:
            results[sym] = {"error": str(e)}

    return {"results": results}
