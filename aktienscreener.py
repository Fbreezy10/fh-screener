import yfinance as yf
import pandas as pd

# Kriterien-Gewichtung basierend auf Peter Lynchs Checkliste
SCORING_WEIGHTS = {
    "KGV": 1,
    "GW": 1,
    "Langfristiges_GW": 1,
    "Verschuldungsgrad": 1,
    "PEG_Ratio": 1,
    "Umsatzanteil": 1,
    "Nettoliquidität": 1,
}

def calculate_cagr(initial_value, final_value, years):
    """Berechnet die durchschnittliche jährliche Wachstumsrate (CAGR)."""
    if initial_value is None or final_value is None or initial_value <= 0:
        return None
    return ((final_value / initial_value) ** (1 / years)) - 1

def get_stock_data(ticker):
    """Holt relevante Finanzkennzahlen einer Aktie von Yahoo Finance."""
    stock = yf.Ticker(ticker)
    info = stock.info

    # aktuelles KGV
    kgv = round(info.get("trailingPE"), 2) if info.get("trailingPE") else None

    #################
    # EPS berechnen #
    #################
    earnings_history = stock.financials.loc["Net Income", :]
    earnings_history2 = stock.quarterly_financials.loc["Net Income", :]
    eps_crnt_qrt = (
        round(stock.quarterly_financials.loc["Diluted EPS"].iloc[0], 2)
        if stock.quarterly_financials.loc["Diluted EPS"].iloc[0] >= 0
        or stock.quarterly_financials.loc["Diluted EPS"].iloc[0] < 0
        else None
    )
    eps_1y_qrt = (
        round(stock.quarterly_financials.loc["Diluted EPS"].iloc[4], 2)
        if stock.quarterly_financials.loc["Diluted EPS"].iloc[4] >= 0
        or stock.quarterly_financials.loc["Diluted EPS"].iloc[4] < 0
        else None
    )
    eps_fy = (
        round(stock.financials.loc["Diluted EPS"].iloc[0], 2)
        if stock.financials.loc["Diluted EPS"].iloc[0] >= 0
        or stock.financials.loc["Diluted EPS"].iloc[0] < 0
        else info.get("trailingEps")
    )
    eps_1y = (
        round(stock.financials.loc["Diluted EPS"].iloc[1], 2)
        if stock.financials.loc["Diluted EPS"].iloc[1] >= 0
        or stock.financials.loc["Diluted EPS"].iloc[1] < 0
        else None
    )
    eps_3_years_ago = (
        round(stock.financials.loc["Diluted EPS"].iloc[3], 3)
        if len(earnings_history) > 3
        else None
    )

    ##################
    # Gewinnwachstum #
    ##################
    # Initialisierung der Variablen
    long_gw = None
    gw_fy = None
    gw_yoy = None

    # Langfristiges Gewinnwachstum berechnen (CAGR des EPS über 3 Jahre)
    try:
        if eps_3_years_ago > 0:
            long_gw = round(calculate_cagr(eps_3_years_ago, eps_fy, 3) * 100, 2)
        elif eps_3_years_ago <= 0:
            eps_new = (eps_fy + ((eps_fy - eps_3_years_ago) / 3)) / eps_fy - 1
            long_gw = round(eps_new * 100, 2)
    except Exception:
        None

    # Gewinnwachstum aktuelles FY - letztes FY berechnen
    try:
        if eps_1y > 0 and isinstance(eps_1y, float):
            gw_fy = round(((eps_fy / eps_1y) - 1) * 100, 2)
        elif eps_1y <= 0 and isinstance(eps_1y, float):
            eps_new = (eps_fy + ((eps_fy - eps_1y))) / eps_fy - 1
            gw_fy = round(eps_new * 100, 2)
    except Exception:
        None

    # Gewinnwachstum Quartal YoY
    try:
        if eps_1y_qrt > 0 and isinstance(eps_crnt_qrt, float):
            gw_yoy = round(((eps_crnt_qrt / eps_1y_qrt) - 1) * 100, 2)
        elif eps_1y_qrt <= 0 and isinstance(eps_crnt_qrt, float):
            eps_new = (eps_crnt_qrt + ((eps_crnt_qrt - eps_1y_qrt))) / eps_crnt_qrt - 1
            gw_yoy = round(eps_new * 100, 2)
    except Exception:
        None

    ###################
    # Nettoliquidität #
    ###################
    fl_mittel = 0
    if "Cash Cash Equivalents And Short Term Investments" in stock.balance_sheet.index:
        fl_mittel = stock.balance_sheet.loc[
            "Cash Cash Equivalents And Short Term Investments"
        ].iloc[0]
    else:
        fl_mittel = (
            stock.balance_sheet.loc["Cash And Cash Equivalents"].iloc[0]
            + stock.balance_sheet.loc["Other Short Term Investments"].iloc[0]
        )

    verbindlichkeiten = (
        stock.balance_sheet.loc["Long Term Debt"].iloc[0]
        if stock.balance_sheet.loc["Long Term Debt"].iloc[0] >= 0
        or stock.balance_sheet.loc["Long Term Debt"].iloc[0] < 0
        else (
            stock.balance_sheet.loc["Long Term Debt"].iloc[1]
            if stock.balance_sheet.loc["Long Term Debt"].iloc[1] >= 0
            or stock.balance_sheet.loc["Long Term Debt"].iloc[1] < 0
            else None
        )
    )

    # Nettoliquidität
    netto_liq = fl_mittel - verbindlichkeiten

    # Ausstehende Aktien
    shares_outstanding = stock.info.get("sharesOutstanding")

    # Nettowert pro Aktie
    shares_net = round(netto_liq / shares_outstanding, 2)

    # Barreserven
    kgv_adj = round(
        (info.get("currentPrice") - shares_net) / info.get("trailingEps"), 2
    )

    ############################
    # Berechnung der PEG-Ratio #
    ############################
  #  peg_ratio = (
    peg_ratio = 0.0    
    if type(info.get("trailingPegRatio")) == float:
        peg_ratio  = info.get("trailingPegRatio")
    elif type(kgv) == float and type(gw_fy) == float:
        peg_ratio = (kgv / gw_fy)
    else: peg_ratio is None
   # )

    ##################################
    # Fortgeschrittene KGV Bewertung #
    ##################################
    div = info.get("dividendRate")
    # KGV_PRO_YOY
    if isinstance(gw_yoy, float) and isinstance(div, float):
        kgv_pro_yoy = round((gw_yoy + div) / kgv, 2)
    elif isinstance(gw_yoy, float) and not isinstance(div, float) and type(kgv) == float:
        kgv_pro_yoy = round(gw_yoy / kgv, 2)
    elif not isinstance(gw_yoy, float):
        kgv_pro_yoy = None

    # KGV_PRO_FY
    kgv_pro_fy = None
    if gw_fy != "None" and isinstance(div, float):
        kgv_pro_fy = round((gw_fy + div) / kgv, 2)
    elif type(gw_fy) == float and not isinstance(div, float) and type(kgv) == float:
        kgv_pro_fy = round(gw_fy / kgv, 2)
    elif gw_fy == "None":
        kgv_pro_fy = None

    # KGV_PRO_LONG
    kgv_pro_long = None
    if long_gw != "None" and isinstance(div, float):
        kgv_pro_long = round((long_gw + div) / kgv, 2)
    elif long_gw != "None" and not isinstance(div, float) and type(kgv) == float:
        kgv_pro_long = round(long_gw / kgv, 2)
    elif long_gw == "None":
        kgv_pro_long = None

    ##################################
    # Grades #
    ##################################
    def grade_value(value, thresholds):
        """Gibt eine Note basierend auf Schwellenwerten zurück."""
        for threshold, grade in thresholds:
            if value == 100:
                return None
            elif value >= threshold:
                return grade
        return 6

    def grade_value2(value, thresholds):
        """Gibt eine Note basierend auf Schwellenwerten zurück."""
        for threshold, grade in thresholds:
            if value <= threshold:
                return grade
        return 6

    ###########################
    # Benotung der Kennzahlen #
    ###########################
    # gw_kgv_yoy_note
    gw_kgv_yoy_note = grade_value(
        gw_yoy / kgv if gw_yoy and kgv else 100,
        [(2, 1), (1.7, 2), (1.4, 3), (1.2, 4), (0.85, 5)],
    )
    # gw_kgv_fy_note
    gw_kgv_fy_note = grade_value(
        gw_fy / kgv if gw_fy and kgv else 100,
        [(2, 1), (1.7, 2), (1.4, 3), (1.2, 4), (0.85, 5)],
    )
    # gw_kgv_long_note
    gw_kgv_long_note = grade_value(
        long_gw / kgv if long_gw and kgv else 100,
        [(2, 1), (1.7, 2), (1.4, 3), (1.2, 4), (0.85, 5)],
    )

    # kgv_pro_yoy_note
    kgv_pro_yoy_note = grade_value(
        kgv_pro_yoy if kgv_pro_yoy else 100,
        [(2, 1), (1.7, 2), (1.4, 3), (1.2, 4), (0.85, 5)],
    )
    # kgv_pro_yoy_note
    kgv_pro_fy_note = grade_value(
        kgv_pro_fy if type(kgv_pro_fy) == float else 100,
        [(2, 1), (1.7, 2), (1.4, 3), (1.2, 4), (0.85, 5)],
    )
    # kgv_pro_yoy_note
    kgv_pro_long_note = grade_value(
        kgv_pro_long if kgv_pro_long else 100,
        [(2, 1), (1.7, 2), (1.4, 3), (1.2, 4), (0.85, 5)],
    )

    # peg_ratio_note
    peg_ratio_note = grade_value2(
        peg_ratio if peg_ratio else 10,
        [(0.0, 6), (0.7, 1), (1, 2), (1.2, 3), (1.5, 4), (1.8, 5), (float("inf"), 6)],
    )

    ############################################
    # Berechnung der Durchschnittsnote "grade" #
    ############################################
    grades = [
        gw_kgv_yoy_note,
        gw_kgv_fy_note,
        gw_kgv_long_note,
        kgv_pro_yoy_note,
        kgv_pro_fy_note,
        kgv_pro_long_note,
        peg_ratio_note,
    ]
    valid_grades = [g for g in grades if g is not None]
    grade = round(sum(valid_grades) / len(valid_grades), 2) if valid_grades else None

    return {
        "Ticker": ticker,
        # "Kurs": info.get("currentPrice"),
        # "eps_fy": eps_fy,
        # "eps_3Y": eps_3_years_ago,
        # "eps_CRNT_QT": type(eps_crnt_qrt),
        # "eps_1Y_QRT": type(eps_1y_qrt),
        "KGV": kgv,
        "KGV-Adj": kgv_adj,
        "Div_%": info.get("dividendRate"),
        "GW_YOY": gw_yoy,
        "GW_FY": gw_fy,
        "Long_GW": long_gw,
        "GW-KGV-YOY": f"{round(gw_yoy / kgv, 2) if gw_yoy and kgv else None} ({gw_kgv_yoy_note})",
        "GW-KGV-FY": f"{round(gw_fy / kgv, 2) if gw_fy and kgv else None} ({gw_kgv_fy_note})",
        "GW-KGV-LONG": f"{round(long_gw / kgv, 2) if long_gw and kgv else None} ({gw_kgv_long_note})",
        "KGV_PRO_YOY": f"{kgv_pro_yoy} ({kgv_pro_yoy_note})",
        "KGV_PRO_FY": f"{kgv_pro_fy} ({kgv_pro_fy_note})",
        "KGV_PRO_LONG": f"{kgv_pro_long} ({kgv_pro_long_note})",
        "PEG_Ratio": f"{round(peg_ratio, 2)} ({peg_ratio_note})",
        #"GW-KGV-YOY-N": gw_kgv_yoy_note,
        #"GW-KGV-FY-N": gw_kgv_fy_note,
        #"GW-KGV-LONG-N": gw_kgv_long_note,
        #"KGV_PRO_YOY-N": kgv_pro_yoy_note,
       # "KGV_PRO_FY-N": kgv_pro_fy_note,
       # "KGV_PRO_LONG-N": kgv_pro_long_note,
       # "PEG_Ratio-N": peg_ratio_note,
        # "Nettoliqidität": netto_liq,
        #"Aktie_Net": shares_net,
        "Grade": grade,
    }

def analyze_stocks(tickers):
    results = [get_stock_data(ticker) for ticker in tickers if get_stock_data(ticker)]
    df = pd.DataFrame(results)
    return df.sort_values(by="Grade", ascending=True)

tickers = [
    "SMCI",
  #  "MSFT",
   # "AMZN",
    "NU",
    "SHOP",
  #  "CRWD",
  #  "ASML",
 #   "NVO",
  #  "TMDX",
    "MELI",
    "NVDA",
    "TSM",
    "NICE",
    "SABR",
    "DAVA",
    "ON",
    "ADBE",
    "FIS",
    "NXPI"

]
df = analyze_stocks(tickers)
print(df)
