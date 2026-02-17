import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏠 Buy vs Rent — NPV Teaching Simulator")
st.caption("Developer: Dr. Shalini Velappan")

tab1, tab2 = st.tabs(["Simulator", "Student Guide"])

# =====================================================
# SIMULATOR
# =====================================================
with tab1:

    # ---------- INPUTS ----------
    st.sidebar.header("Property")

    price = st.sidebar.number_input("House price", value=1500000.0)
    down_pct = st.sidebar.number_input("Down payment %", value=20.0)
    loan_rate = st.sidebar.number_input("Loan interest %", value=3.0)
    tenure = st.sidebar.number_input("Loan tenure (years)", value=30)

    st.sidebar.header("Rent")
    rent0 = st.sidebar.number_input("Monthly rent", value=4000.0)
    rent_growth = st.sidebar.number_input("Rent growth %", value=0.0)

    st.sidebar.header("Market")
    house_growth = st.sidebar.number_input("House growth %", value=0.0)
    disc = st.sidebar.number_input("Discount rate %", value=3.0)

    st.sidebar.header("Exit")
    exit_year = st.sidebar.number_input("Sell after years", min_value=1, value=10)
    hold_to_end = st.sidebar.checkbox("Hold till loan end (no resale)")

    st.sidebar.header("Costs")
    buy_commission = st.sidebar.number_input("Buy commission %", value=1.0)
    sell_commission = st.sidebar.number_input("Sell commission %", value=1.0)
    monthly_costs = st.sidebar.number_input("Maintenance+tax+repairs", value=450.0)

    # ---------- EMI ----------
    downpayment = price * down_pct/100
    loan_amt = price - downpayment
    r = loan_rate/100/12
    n = tenure*12
    emi = loan_amt*r*(1+r)**n/((1+r)**n-1)

    st.metric("Monthly EMI", f"{emi:,.2f}")

    # =====================================================
    # CORE NPV FUNCTION
    # =====================================================
    def compute_npv(hg, rg, hold_mode=False, years_override=None):

        if years_override:
            months = int(years_override*12)
        elif hold_mode:
            months = int(tenure*12)
        else:
            months = int(exit_year*12)

        monthly_disc = disc/100/12

        # ---------- BUY ----------
        cf_buy = []
        initial = downpayment + price*buy_commission/100 + 0.03*price + 8000
        cf_buy.append(-initial)

        balance = loan_amt
        equity_track = []

        for m in range(1, months+1):
            interest = balance*r
            principal = emi - interest
            balance -= principal

            equity_track.append(price - balance)
            cf_buy.append(-(emi + monthly_costs))

        if not hold_mode and not years_override:
            sale_price = price*(1+hg/100)**exit_year
            sale_net = sale_price*(1-sell_commission/100) - balance
            cf_buy[-1] += sale_net

        # ---------- RENT ----------
        cf_rent = [0]
        rent = rent0

        for m in range(1, months+1):
            rent = rent*(1+rg/100/12)
            cf_rent.append(-rent)

        def npv(rate, cfs):
            return sum(cf/((1+rate)**i) for i, cf in enumerate(cfs))

        return npv(monthly_disc, cf_buy), npv(monthly_disc, cf_rent), equity_track

    # =====================================================
    # LIVE DECISION
    # =====================================================
    st.subheader("Live decision")

    buy_now, rent_now, equity_track = compute_npv(house_growth, rent_growth, hold_to_end)

    if buy_now > rent_now:
        st.success("Buying financially better")
    else:
        st.warning("Renting financially better")

    col1, col2 = st.columns(2)
    col1.metric("NPV Buy", f"{buy_now:,.0f}")
    col2.metric("NPV Rent", f"{rent_now:,.0f}")

    # =====================================================
    # COMPARISON TABLE
    # =====================================================
    st.subheader("Sell vs Hold comparison")

    buy_sell, rent_sell, _ = compute_npv(house_growth, rent_growth, False)
    buy_hold, rent_hold, _ = compute_npv(house_growth, rent_growth, True)

    comp_df = pd.DataFrame({
        "Scenario": ["Sell after chosen years", "Hold till loan end"],
        "NPV Buy": [buy_sell, buy_hold],
        "NPV Rent": [rent_sell, rent_hold],
        "Buy − Rent": [buy_sell-rent_sell, buy_hold-rent_hold]
    })

    st.dataframe(comp_df)

    # =====================================================
    # BREAK EVEN
    # =====================================================
    st.subheader("Break-even holding period")

    break_even = None
    for y in range(1, tenure+1):
        b, r, _ = compute_npv(house_growth, rent_growth, False, years_override=y)
        if b > r:
            break_even = y
            break

    if break_even:
        st.info(f"Buying becomes better after ~ {break_even} years")
    else:
        st.info("Renting better across full horizon")

    # =====================================================
    # NPV VS YEARS
    # =====================================================
    st.subheader("NPV vs holding period")

    years = list(range(1, tenure+1))
    buy_vals, rent_vals = [], []

    for y in years:
        b, r, _ = compute_npv(house_growth, rent_growth, False, years_override=y)
        buy_vals.append(b)
        rent_vals.append(r)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=buy_vals, name="Buy"))
    fig.add_trace(go.Scatter(x=years, y=rent_vals, name="Rent"))
    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # EQUITY CHART
    # =====================================================
    st.subheader("Equity buildup")

    eq_years = list(range(1, len(equity_track)//12 + 1))
    eq_vals = [equity_track[i*12-1] for i in eq_years]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=eq_years, y=eq_vals, name="Equity"))
    st.plotly_chart(fig2, use_container_width=True)

    # =====================================================
    # MONTE CARLO
    # =====================================================
    st.subheader("Monte Carlo simulation")

    sims = st.slider("Simulations", 100, 2000, 500)

    if st.button("Run Monte Carlo"):

        outcomes = []

        for _ in range(sims):
            hg = np.random.normal(house_growth, 1.5)
            rg = np.random.normal(rent_growth, 1.0)
            b, r, _ = compute_npv(hg, rg, hold_to_end)
            outcomes.append(b-r)

        prob = np.mean(np.array(outcomes) > 0)
        st.metric("Probability buying wins", f"{prob:.2%}")

        fig3 = go.Figure()
        fig3.add_histogram(x=outcomes)
        st.plotly_chart(fig3, use_container_width=True)

# =====================================================
# STUDENT GUIDE
# =====================================================
with tab2:
    st.header("How to interpret")

    st.markdown("""
If NPV(Buy) > NPV(Rent) → Buy  
If NPV(Rent) > NPV(Buy) → Rent  

Short stay → rent  
Long stay → buy  
""")
