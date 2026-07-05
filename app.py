# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Настройка страницы для строгого и функционального дизайна
st.set_page_config(page_title="Fundamental Analysis Core", layout="centered")

st.markdown("### Финансовый инжиниринг: Аналитический Терминал")
st.markdown("Инструмент гибридной оценки активов (DCF + Mean Reversion).")

# Строго одно поле ввода для тикера
ticker_symbol = st.text_input("Тикер актива (например: AAPL, GOOGL, MSFT):").strip().upper()

if st.button("Анализировать"):
    if not ticker_symbol:
        st.warning("Пожалуйста, введите тикер для начала анализа.")
    else:
        with st.spinner("Сбор данных и запуск гибридной модели оценки..."):
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
                
                # Защита от пустых ответов API
                if not info or ('symbol' not in info and 'shortName' not in info and 'regularMarketPrice' not in info):
                    st.error(f"Данные по тикеру '{ticker_symbol}' не найдены. Проверьте правильность написания.")
                else:
                    # 1. Current Price & Market Cap
                    current_price = info.get('currentPrice', info.get('regularMarketPrice'))
                    market_cap = info.get('marketCap')
                    
                    price_str = f"${current_price:,.2f}" if isinstance(current_price, (int, float)) else "Data Unavailable"
                        
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

                    # 2. P/E Ratio & Forward P/E
                    pe_ratio = info.get('trailingPE')
                    pe_str = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "Data Unavailable"

                    forward_pe = info.get('forwardPE')
                    forward_pe_str = f"{forward_pe:.2f}" if isinstance(forward_pe, (int, float)) else "Data Unavailable"
                    
                    # Получаем Forward EPS для гибридной модели
                    forward_eps = info.get('forwardEps')

                    # 3. Free Cash Flow (TTM)
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

                    # 4. АЛГОРИТМ ТРОЙНОГО ФИЛЬТРА ДЛЯ РОСТА
                    growth_str = "Data Unavailable"
                    try:
                        if hasattr(ticker, 'growth_estimates') and ticker.growth_estimates is not None and not ticker.growth_estimates.empty:
                            df_growth = ticker.growth_estimates.copy()
                            df_growth.index = df_growth.index.astype(str).str.lower()
                            target = df_growth[df_growth.index.str.contains('next year') | df_growth.index.str.contains('\+1y')]
                            if not target.empty:
                                val = target.iloc[0].iloc[0]
                                if pd.notna(val):
                                    growth_str = f"{float(val.replace('%', '').strip()):.2f}%" if isinstance(val, str) else (f"{float(val) * 100:.2f}%" if abs(val) < 1.0 else f"{float(val):.2f}%")
                        
                        if growth_str == "Data Unavailable":
                            if hasattr(ticker, 'earnings_estimate') and ticker.earnings_estimate is not None and not ticker.earnings_estimate.empty:
                                df_earn = ticker.earnings_estimate.copy()
                                df_earn.index = df_earn.index.astype(str).str.lower()
                                target = df_earn[df_earn.index.str.contains('next year') | df_earn.index.str.contains('\+1y')]
                                if not target.empty:
                                    val = target.iloc[0].iloc[0]
                                    if pd.notna(val):
                                        growth_str = f"{float(val.replace('%', '').strip()):.2f}%" if isinstance(val, str) else (f"{float(val) * 100:.2f}%" if abs(val) < 1.0 else f"{float(val):.2f}%")
                        
                        if growth_str == "Data Unavailable":
                            growth_estimate = info.get('earningsGrowth') 
                            if isinstance(growth_estimate, (int, float)):
                                growth_str = f"{growth_estimate * 100:.2f}%"
                    except:
                        growth_estimate = info.get('earningsGrowth') 
                        if isinstance(growth_estimate, (int, float)):
                            growth_str = f"{growth_estimate * 100:.2f}%"

                    # Отрисовка базовой таблицы
                    metrics_data = {
                        "Ключевая Метрика": [
                            "(1) Price & Market Cap",
                            "(2) P/E Ratio (TTM)",
                            "(3) Forward P/E",
                            "(4) Free Cash Flow (TTM)",
                            "(5) Next Year Growth Estimate"
                        ],
                        "Значение": [
                            price_and_cap, pe_str, forward_pe_str, fcf_str, growth_str
                        ]
                    }
                    st.dataframe(pd.DataFrame(metrics_data), hide_index=True, use_container_width=True)

                    # --- ГИБРИДНАЯ МАШИНА ДЛЯ ВЗВЕШИВАНИЯ ---
                    if isinstance(fcf, (int, float)) and fcf > 0 and isinstance(current_price, (int, float)) and current_price > 0:
                        st.markdown("---")
                        st.markdown("#### ⚖️ Гибридная оценка внутренней стоимости")
                        
                        # --- МОДЕЛЬ 1: Сухой DCF ---
                        beta = info.get('beta', 1.0) if isinstance(info.get('beta'), (int, float)) else 1.0
                        hurdle_rate = 4.0 + beta * 5.0 # Rf (4%) + Beta * ERP (5%)
                        
                        try:
                            base_growth = float(growth_str.replace('%', '')) if growth_str != "Data Unavailable" else 12.0
                        except:
                            base_growth = 12.0
                            
                        r_pct, g_pct, gt_pct = hurdle_rate / 100.0, base_growth / 100.0, 0.03
                        
                        discounted_fcf_sum, temp_fcf = 0, fcf
                        for year in range(1, 6):
                            temp_fcf *= (1 + g_pct)
                            discounted_fcf_sum += temp_fcf / ((1 + r_pct) ** year)
                            
                        terminal_value = (temp_fcf * (1 + gt_pct)) / (r_pct - gt_pct) if r_pct > gt_pct else 0
                        discounted_tv = terminal_value / ((1 + r_pct) ** 5)
                        
                        intrinsic_business_value = discounted_fcf_sum + discounted_tv
                        dcf_intrinsic_price = current_price * (intrinsic_business_value / market_cap) if market_cap else current_price

                        # --- МОДЕЛЬ 2: Историческая Медиана (Mean Reversion) ---
                        # Консервативный исторический P/E для технологических монополий / широкого рынка
                        median_pe = 25.0 
                        if isinstance(forward_eps, (int, float)) and forward_eps > 0:
                            pe_intrinsic_price = forward_eps * median_pe
                        else:
                            pe_intrinsic_price = current_price # Заглушка, если нет EPS

                        # --- ИТОГОВЫЙ БЛЕНД (Слияние моделей) ---
                        blended_intrinsic_price = (dcf_intrinsic_price + pe_intrinsic_price) / 2
                        margin_of_safety = 1.0 - (current_price / blended_intrinsic_price)
                        
                        st.write(f"• Оценка по кэшу (DCF): **${dcf_intrinsic_price:.2f}**")
                        st.write(f"• Оценка по рыночной медиане (P/E ~25): **${pe_intrinsic_price:.2f}**")
                        st.write(f"• Итоговая справедливая цена: **${blended_intrinsic_price:.2f}**")
                        
                        # Расширенные, жизненные триггеры для инвестора (Moat Premium до -15%)
                        if margin_of_safety >= 0.15:
                            st.success(f"Запас прочности (Margin of Safety): **{margin_of_safety * 100:.2f}%**")
                            st.write("🟢 **Статус:** Глубокая недооценка. Идеальная точка входа для наращивания позиции.")
                        elif -0.15 <= margin_of_safety < 0.15:
                            st.warning(f"Запас прочности (Margin of Safety): **{margin_of_safety * 100:.2f}%**")
                            st.write("🟡 **Статус:** Справедливая оценка (Допустимая Премия за Монополию). Рекомендовано плановое накопление малыми долями (DCA).")
                        else:
                            st.error(f"Запас прочности (Margin of Safety): **{margin_of_safety * 100:.2f}%**")
                            st.write("🔴 **Статус:** Актив математически переоценен. Вход крупным капиталом запрещен. Допускается только жесткий DCA для ядра портфеля.")

                    # --- БЛОК ДЛЯ СМАРТФОНОВ ---
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
                st.error(f"Системная ошибка при обработке данных API: {e}")
