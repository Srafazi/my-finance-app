# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Настройка страницы для строгого и функционального дизайна (минимизация нагрузки)
st.set_page_config(page_title="Fundamental Analysis Core", layout="centered")

st.markdown("### Финансовый инжиниринг: Фундаментальные метрики")
st.markdown("Инструмент аналитика для получения объективных данных (Опора 1 и Опора 2).")

# Поле ввода для тикера
ticker_symbol = st.text_input("Тикер актива (например: AAPL, GOOGL, MSFT):").strip().upper()

# Кнопка для запуска анализа
if st.button("Анализировать"):
    if not ticker_symbol:
        st.warning("Пожалуйста, введите тикер для начала анализа.")
    else:
        with st.spinner("Запрос данных из yfinance со снятием ограничений..."):
            try:
                # --- ЗАЩИТНЫЙ БЛОК ОТ БЛОКИРОВОК (АНТИ-RATE LIMIT) ---
                # Создаем сессию и маскируемся под обычный домашний браузер
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                })
                
                # Передаем маскированную сессию в yfinance
                ticker = yf.Ticker(ticker_symbol, session=session)
                # ----------------------------------------------------
                
                info = ticker.info
                
                # Защита от несуществующих тикеров или пустых ответов API
                if not info or ('symbol' not in info and 'shortName' not in info and 'regularMarketPrice' not in info):
                    st.error(f"Данные по тикеру '{ticker_symbol}' не найдены. Проверьте правильность написания или доступность API.")
                else:
                    # 1. Current Price & Market Cap
                    current_price = info.get('currentPrice', info.get('regularMarketPrice'))
                    market_cap = info.get('marketCap')
                    
                    # Базовая математическая валидация аномалий
                    if isinstance(market_cap, (int, float)) and market_cap < 0:
                        st.warning("Внимание: Рыночная капитализация меньше нуля. Возможна аномалия в данных источника.")
                    if isinstance(current_price, (int, float)) and current_price < 0:
                        st.warning("Внимание: Текущая цена меньше нуля. Возможна аномалия в данных источника.")
                        
                    # Форматирование текущей цены
                    if isinstance(current_price, (int, float)):
                        price_str = f"${current_price:,.2f}"
                    else:
                        price_str = "Data Unavailable"
                        
                    # Форматирование рыночной капитализации для читаемости
                    if isinstance(market_cap, (int, float)):
                        if market_cap >= 1e12:
                            cap_str = f"${market_cap / 1e12:.2f}T"
                        elif market_cap >= 1e9:
                            cap_str = f"${market_cap / 1e9:.2f}B"
                        elif market_cap >= 1e6:
                            cap_str = f"${market_cap / 1e6:.2f}M"
                        else:
                            cap_str = f"${market_cap:,.2f}"
                    else:
                        cap_str = "Data Unavailable"
                        
                    price_and_cap = f"{price_str} / {cap_str}"
                    if price_str == "Data Unavailable" and cap_str == "Data Unavailable":
                        price_and_cap = "Data Unavailable"

                    # 2. P/E Ratio (TTM)
                    pe_ratio = info.get('trailingPE')
                    if isinstance(pe_ratio, (int, float)):
                        pe_str = f"{pe_ratio:.2f}"
                    else:
                        pe_str = "Data Unavailable"

                    # 3. Forward P/E
                    forward_pe = info.get('forwardPE')
                    if isinstance(forward_pe, (int, float)):
                        forward_pe_str = f"{forward_pe:.2f}"
                    else:
                        forward_pe_str = "Data Unavailable"

                    # 4. Free Cash Flow (TTM)
                    fcf = info.get('freeCashflow')
                    if isinstance(fcf, (int, float)):
                        if fcf >= 1e9 or fcf <= -1e9:
                            fcf_str = f"${fcf / 1e9:.2f}B"
                        elif fcf >= 1e6 or fcf <= -1e6:
                            fcf_str = f"${fcf / 1e6:.2f}M"
                        else:
                            fcf_str = f"${fcf:,.2f}"
                    else:
                        fcf_str = "Data Unavailable"

                    # 5. Next Year Growth Estimate
                    growth_estimate = info.get('earningsGrowth') 
                    if isinstance(growth_estimate, (int, float)):
                        growth_str = f"{growth_estimate * 100:.2f}%"
                    else:
                        growth_str = "Data Unavailable"

                    # Формирование итоговой структуры таблицы
                    metrics_data = {
                        "Ключевая Метрика": [
                            "(1) Current Price & Market Cap",
                            "(2) P/E Ratio (TTM)",
                            "(3) Forward P/E",
                            "(4) Free Cash Flow (TTM)",
                            "(5) Next Year Growth Estimate"
                        ],
                        "Значение": [
                            price_and_cap,
                            pe_str,
                            forward_pe_str,
                            fcf_str,
                            growth_str
                        ]
                    }
                    
                    df = pd.DataFrame(metrics_data)
                    
                    # Отрисовка чистой таблицы
                    st.dataframe(df, hide_index=True, use_container_width=True)

                    # БЛОК ДЛЯ СМАРТФОНОВ
                    st.markdown("---")
                    
                    # Генерация текста для удобного ручного копирования пальцем
                    raw_text = (
                        f"📊 ФУНДАМЕНТАЛЬНЫЙ АНАЛИЗ: {ticker_symbol}\n"
                        f"• Price & Market Cap: {price_and_cap}\n"
                        f"• P/E Ratio (TTM): {pe_str}\n"
                        f"• Forward P/E: {forward_pe_str}\n"
                        f"• Free Cash Flow (TTM): {fcf_str}\n"
                        f"• Next Year Growth: {growth_str}"
                    )
                    st.text_area("📋 Текст для копирования (зажмите и выделите всё):", value=raw_text, height=140)

            except Exception as e:
                st.error(f"Процесс прерван Yahoo Finance. Блокировка лимита. Системная ошибка: {e}")
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
