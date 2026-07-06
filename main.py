from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from curl_cffi import requests as curl_requests

app = FastAPI(title="BIST AI Trader - Yahoo Finance Backend")

# Tarayıcıdaki HTML sayfasının bu API'ye istek atabilmesi için CORS'u herkese açıyoruz.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Yahoo Finance, bulut sunucularından (Render, AWS, vb.) gelen istekleri
# genellikle "bot" olarak algılayıp engeller. curl_cffi ile isteklerin
# gerçek bir Chrome tarayıcısından geliyormuş gibi görünmesini sağlıyoruz.
# Bu, engellenme ihtimalini büyük ölçüde azaltır (garanti etmez).
def make_session():
    return curl_requests.Session(impersonate="chrome")


@app.get("/")
def root():
    return {"status": "ok", "message": "BIST AI Trader Yahoo Finance backend calisiyor"}


@app.get("/quote/{symbol}")
def get_quote(symbol: str):
    """Tek bir hisse için fiyat döner. symbol örn: THYAO.IS"""
    try:
        session = make_session()
        t = yf.Ticker(symbol, session=session)
        info = t.fast_info
        price = info.get("last_price")
        prev_close = info.get("previous_close")
        volume = info.get("last_volume")

        if price is None:
            raise HTTPException(status_code=404, detail=f"{symbol} icin fiyat bulunamadi (Yahoo gecici olarak engellemis olabilir)")

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
    session = make_session()

    for sym in sym_list:
        try:
            t = yf.Ticker(sym, session=session)
            info = t.fast_info
            price = info.get("last_price")
            prev_close = info.get("previous_close")
            volume = info.get("last_volume")
            if price is None:
                results[sym] = {"error": "veri yok (Yahoo gecici olarak engellemis olabilir)"}
                continue
            change_pct = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0.0
            results[sym] = {
                "price": round(float(price), 2),
                "previous_close": round(float(prev_close), 2) if prev_close else None,
                "change_pct": change_pct,
                "volume": int(volume) if volume else 0,
            }
        except Exception as e:
            results[sym] = {"error": str(e)}

    return {"results": results}
