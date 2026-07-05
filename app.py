# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Настройка страницы для строгого и функционального дизайна
st.set_page_config(page_title="Fundamental Analysis Core", layout="centered")

st.markdown("### Финансовый инжиниринг: Аналитический Терминал")
st.markdown("Инструмент комплексной оценки активов (Опора 1, Опора 2 и Опора 4).")

# Строго одно поле ввода для тикера
ticker_symbol = st.text_input("Тикер актива (например: AAPL, GOOGL, MSFT):").strip().upper()

if st.button("Анализировать"):
    if not ticker_symbol:
        st.warning("Пожалуйста, введите тикер для начала анализа.")
    else:
        with st.spinner("Запрос данных из yfinance и запуск Тройного Фильтра..."):
            try:
                # ЗАЩИТНЫЙ БЛОК ОТ БЛОКИРОВОК (АНТИ-RATE LIMIT)
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                })
                
                ticker = yf.Ticker(ticker_symbol, session=session)
                info = ticker.info
                
                # Защита от несуществующих тикеров или пустых ответов API
                if not info or ('symbol' not in info and 'shortName' not in info and 'regularMarketPrice' not in info):
                    st.error(f"Данные по тикеру '{ticker_symbol}' не найдены. Проверьте правильность написания или доступность API.")
                else:
                    # 1. Current Price & Market Cap
                    current_price = info.get('currentPrice', info.get('regularMarketPrice'))
                    market_cap = info.get('marketCap')
                    
                    if isinstance(current_price, (int, float)):
                        price_str = f"${current_price:,.2f}"
                    else:
                        price_str = "Data Unavailable"
                        
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

                    # 2. P/E Ratio (TTM)
                    pe_ratio = info.get('trailingPE')
                    pe_str = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "Data Unavailable"

                    # 3. Forward P/E
                    forward_pe = info.get('forwardPE')
                    forward_pe_str = f"{forward_pe:.2f}" if isinstance(forward_pe, (int, float)) else "Data Unavailable"

                    # 4. Free Cash Flow (TTM) - Контроль чистой наличности
                    fcf = info.get('freeCashflow')
                    if isinstance(fcf, (int, float)):
                        if fcf >= 1e9 or fcf <= -1e9:
                            fcf_str = f"${fcf / 1e9:.2f}B"
                        elif fcf >= 1e6 or fcf <= -1e6:
                            fcf_str = f"${fcf:,.2f}"
                    else:
                        fcf_str = "Data Unavailable"

                    # 5. АЛГОРИТМ ТРОЙНОГО ФИЛЬТРА ДЛЯ NEXT YEAR GROWTH ESTIMATE
                    growth_str = "Data Unavailable"
                    try:
                        # Фильтр 1: Таблица growth_estimates (Прямой консенсус аналитиков)
                        if hasattr(ticker, 'growth_estimates') and ticker.growth_estimates is not None and not ticker.growth_estimates.empty:
                            df_growth = ticker.growth_estimates.copy()
                            df_growth.index = df_growth.index.astype(str).str.lower()
                            target = df_growth[df_growth.index.str.contains('next year') | df_growth.index.str.contains('\+1y')]
                            if not target.empty:
                                val = target.iloc[0].iloc[0]
                                if pd.notna(val):
                                    if isinstance(val, str):
                                        growth_str = f"{float(val.replace('%', '').strip()):.2f}%"
                                    else:
                                        growth_str = f"{float(val) * 100:.2f}%" if abs(val) < 1.0 else f"{float(val):.2f}%"
                        
                        # Фильтр 2: Таблица earnings_estimate (Альтернативный консенсус)
                        if growth_str == "Data Unavailable":
                            if hasattr(ticker, 'earnings_estimate') and ticker.earnings_estimate is not None and not ticker.earnings_estimate.empty:
                                df_earn = ticker.earnings_estimate.copy()
                                df_earn.index = df_earn.index.astype(str).str.lower()
                                target = df_earn[df_earn.index.str.contains('next year') | df_earn.index.str.contains('\+1y')]
                                if not target.empty:
                                    val = target.iloc[0].iloc[0]
                                    if pd.notna(val):
                                        if isinstance(val, str):
                                            growth_str = f"{float(val.replace('%', '').strip()):.2f}%"
                                        else:
                                            growth_str = f"{float(val) * 100:.2f}%" if abs(val) < 1.0 else f"{float(val):.2f}%"
                        
                        # Фильтр 3: Базовый фолбэк на info.get (Если компания малая и таблиц аналитиков нет)
                        if growth_str == "Data Unavailable":
                            growth_estimate = info.get('earningsGrowth') 
                            if isinstance(growth_estimate, (int, float)):
                                growth_str = f"{growth_estimate * 100:.2f}%"
                    except:
                        growth_estimate = info.get('earningsGrowth') 
                        if isinstance(growth_estimate, (int, float)):
                            growth_str = f"{growth_estimate * 100:.2f}%"

                    # Отрисовка базовой таблицы мультипликаторов (Опора 1)
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
                    st.dataframe(df, hide_index=True, use_container_width=True)

                    # --- АВТОМАТИЧЕСКАЯ МАШИНА ДЛЯ ВЗВЕШИВАНИЯ (Опора 2: Модель DCF) ---
                    if isinstance(fcf, (int, float)) and fcf > 0 and isinstance(current_price, (int, float)) and current_price > 0:
                        st.markdown("---")
                        st.markdown("#### ⚖️ Расчет внутренней стоимости бизнеса (DCF Модель)")
                        
                        # Динамический расчет ставки дисконтирования (Hurdle Rate)
                        beta = info.get('beta', 1.0) if isinstance(info.get('beta'), (int, float)) else 1.0
                        rf = 4.0   # Безрисковая ставка 10-летних гособлигаций США
                        erp = 5.0  # Фиксированная премия за риск инвестиций в акции
                        hurdle_rate = rf + beta * erp
                        
                        st.write(f"**Требуемая доходность (Hurdle Rate):** {hurdle_rate:.2f}% (Rf: {rf}% + β: {beta:.2f} × ERP: {erp}%)")
                        
                        # Извлечение чистой процентной ставки роста из Тройного Фильтра
                        try:
                            base_growth = float(growth_str.replace('%', '')) if growth_str != "Data Unavailable" else 12.0
                        except:
                            base_growth = 12.0
                            
                        r_pct = hurdle_rate / 100.0
                        g_pct = base_growth / 100.0
                        gt_pct = 0.03 # Терминальный вечный рост на уровне инфляции
                        
                        # Прогнозирование и дисконтирование FCF на горизонте 5 лет
                        discounted_fcf_sum = 0
                        temp_fcf = fcf
                        for year in range(1, 6):
                            temp_fcf = temp_fcf * (1 + g_pct)
                            discounted_fcf_sum += temp_fcf / ((1 + r_pct) ** year)
                            
                        # Терминальная стоимость (Terminal Value) за пределами 5 лет
                        terminal_value = (temp_fcf * (1 + gt_pct)) / (r_pct - gt_pct) if r_pct > gt_pct else 0
                        discounted_tv = terminal_value / ((1 + r_pct) ** 5)
                        
                        # Общая внутренняя стоимость компании
                        intrinsic_business_value = discounted_fcf_sum + discounted_tv
                        
                        # Математический пересчет стоимости на одну акцию
                        if isinstance(market_cap, (int, float)) and market_cap > 0:
                            intrinsic_share_price = current_price * (intrinsic_business_value / market_cap)
                            margin_of_safety = 1.0 - (current_price / intrinsic_share_price)
                            
                            st.write(f"• Справедливая цена акции (Intrinsic Value): **${intrinsic_share_price:,.2f}**")
                            
                            # Проверка Запаса прочности (Margin of Safety)
                            if margin_of_safety >= 0.25:
                                st.success(f"• Запас прочности (Margin of Safety): **{margin_of_safety * 100:.2f}%**")
                                st.write("🟢 Критерий жесткого запаса прочности выполнен. Математический сигнал к покупке.")
                            elif 0 <= margin_of_safety < 0.25:
                                st.warning(f"• Запас прочности (Margin of Safety): **{margin_of_safety * 100:.2f}%**")
                                st.write("🟡 Цена близка к справедливой, но буфер безопасности ниже консервативного лимита в 25%.")
                            else:
                                st.error(f"• Запас прочности (Margin of Safety): **{margin_of_safety * 100:.2f}%** (Актив переоценен)")
                                st.write("🔴 Внимание: Рыночная цена опережает фундаментальную ценность. Крупный разовый вход запрещен. Для монополий AAA — накопление строго через плановое усреднение (DCA).")

                    # БЛОК ДЛЯ СМАРТФОНОВ
                    st.markdown("---")
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
                st.error(f"Системная ошибка при обработке API Yahoo Finance: {e}")

