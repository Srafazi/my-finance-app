import streamlit as st
import yfinance as yf
import pandas as pd

# 1. Настройка страницы (должна быть первой командой)
st.set_page_config(page_title="Fundamental Analysis Core", layout="centered")

# 2. Изолированная функция с кэшированием (защита от бана по IP и ускорение)
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_and_calculate_metrics(ticker_symbol):
    """Функция скачивает сырые данные, проводит расчеты и возвращает готовый словарь"""
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    
    # Жесткая проверка на существование тикера
    if not info or ('symbol' not in info and 'shortName' not in info and 'regularMarketPrice' not in info):
        return {"error": f"Данные по тикеру '{ticker_symbol}' не найдены. Проверьте правильность написания."}
        
    metrics = {}
    
    # --- (1) Current Price & Market Cap ---
    current_price = info.get('currentPrice', info.get('regularMarketPrice'))
    market_cap = info.get('marketCap')
    
    price_str = f"${current_price:,.2f}" if isinstance(current_price, (int, float)) else "N/A"
    
    if isinstance(market_cap, (int, float)) and market_cap > 0:
        if market_cap >= 1e12: cap_str = f"${market_cap / 1e12:.2f}T"
        elif market_cap >= 1e9: cap_str = f"${market_cap / 1e9:.2f}B"
        elif market_cap >= 1e6: cap_str = f"${market_cap / 1e6:.2f}M"
        else: cap_str = f"${market_cap:,.2f}"
    else:
        cap_str = "N/A"
        
    metrics['price_and_cap'] = f"{price_str} / {cap_str}" if price_str != "N/A" else "Data Unavailable"

    # --- (2) P/E Ratio (TTM) ---
    pe_ratio = info.get('trailingPE')
    metrics['pe_str'] = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "Data Unavailable"

    # --- (3) Forward P/E ---
    forward_pe = info.get('forwardPE')
    metrics['forward_pe_str'] = f"{forward_pe:.2f}" if isinstance(forward_pe, (int, float)) else "Data Unavailable"

    # --- (4) Истинный Free Cash Flow (TTM) ---
    fcf = None
    try:
        qcf = ticker.quarterly_cashflow
        if not qcf.empty:
            if 'Free Cash Flow' in qcf.index:
                fcf_data = qcf.loc['Free Cash Flow'].dropna()
                if len(fcf_data) >= 1:
                    fcf = fcf_data.head(4).sum()
            elif 'Operating Cash Flow' in qcf.index and 'Capital Expenditure' in qcf.index:
                ocf_data = qcf.loc['Operating Cash Flow'].dropna().head(4)
                capex_data = qcf.loc['Capital Expenditure'].dropna().head(4)
                if not ocf_data.empty and not capex_data.empty:
                    fcf = ocf_data.sum() + capex_data.sum()
    except Exception:
        pass

    if fcf is None or pd.isna(fcf):
        fcf = info.get('freeCashflow')

    if isinstance(fcf, (int, float)) and pd.notna(fcf):
        if abs(fcf) >= 1e9: metrics['fcf_str'] = f"${fcf / 1e9:.2f}B"
        elif abs(fcf) >= 1e6: metrics['fcf_str'] = f"${fcf / 1e6:.2f}M"
        else: metrics['fcf_str'] = f"${fcf:,.2f}"
    else:
        metrics['fcf_str'] = "Data Unavailable"

    # --- (5) Истинный прогноз роста (Next Year Consensus Estimate) ---
    growth_estimate = None
    
    # Попытка 1: Запрашиваем таблицу Growth Estimates (вкладка Analysis)
    try:
        ge = ticker.growth_estimates
        if ge is not None and not ge.empty:
            if '+1y' in ge.index:
                # Берем самую первую колонку (которая относится к самой акции)
                val = ge.loc['+1y'].iloc[0]
                if pd.notna(val):
                    growth_estimate = float(val)
    except Exception:
        pass

    # Попытка 2: Запрашиваем таблицу Earnings Estimate
    if growth_estimate is None:
        try:
            ee = ticker.earnings_estimate
            if ee is not None and not ee.empty:
                if '+1y' in ee.index and 'growth' in ee.columns:
                    val = ee.loc['+1y', 'growth']
                    if pd.notna(val):
                        growth_estimate = float(val)
        except Exception:
            pass

    # Попытка 3: Фолбэк на старый метод (info), если таблицы API недоступны
    if growth_estimate is None:
        growth_estimate = info.get('earningsGrowth')
        if not isinstance(growth_estimate, (int, float)):
            growth_estimate = info.get('revenueGrowth')
            
    metrics['growth_str'] = f"{growth_estimate * 100:.2f}%" if isinstance(growth_estimate, (int, float)) else "Data Unavailable"

    return metrics

# 3. Блок отрисовки интерфейса (UI)
st.markdown("### Финансовый инжиниринг: Фундаментальные метрики")
st.markdown("Инструмент аналитика для получения объективных данных (Опора 1 и Опора 2).")

with st.form(key='analysis_form'):
    ticker_symbol = st.text_input("Тикер актива (например: AAPL, GOOGL, MSFT):").strip().upper()
    submit_button = st.form_submit_button(label="Анализировать")

if submit_button:
    if not ticker_symbol:
        st.warning("Пожалуйста, введите тикер для начала анализа.")
    else:
        with st.spinner(f"Запрашиваем и верифицируем данные по {ticker_symbol}..."):
            result = fetch_and_calculate_metrics(ticker_symbol)
            
            if "error" in result:
                st.error(result["error"])
            else:
                metrics_data = {
                    "Ключевая Метрика": [
                        "(1) Current Price & Market Cap",
                        "(2) P/E Ratio (TTM)",
                        "(3) Forward P/E",
                        "(4) Free Cash Flow (TTM)",
                        "(5) Next Year Growth Estimate"
                    ],
                    "Значение": [
                        result['price_and_cap'],
                        result['pe_str'],
                        result['forward_pe_str'],
                        result['fcf_str'],
                        result['growth_str']
                    ]
                }
                
                df = pd.DataFrame(metrics_data)
                st.dataframe(df, hide_index=True, use_container_width=True)

                st.markdown("---")
                
                raw_text = (
                    f"📊 ФУНДАМЕНТАЛЬНЫЙ АНАЛИЗ: {ticker_symbol}\n"
                    f"• Price & Market Cap: {result['price_and_cap']}\n"
                    f"• P/E Ratio (TTM): {result['pe_str']}\n"
                    f"• Forward P/E: {result['forward_pe_str']}\n"
                    f"• Free Cash Flow (TTM): {result['fcf_str']}\n"
                    f"• Next Year Growth: {result['growth_str']}"
                )
                st.text_area("📋 Текст для копирования (зажмите и выделите всё):", value=raw_text, height=140)
