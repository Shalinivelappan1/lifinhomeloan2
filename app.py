import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏠 Buy vs Rent — NPV Teaching Simulator")
st.caption("Developer: Dr. Shalini Velappan")

tab1, tab2 = st.tabs(["Simulator", "Student Guide"])

with tab1:

    # ---------------- MODE ----------------
    mode = st.sidebar.radio(
        "Model type",
        ["Simple (teaching model)", "India real-world model"]
    )

    # ---------------- INPUTS ----------------
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
    hold_to_end = st.sidebar.checkbox("Hold till loan end")

    st.sidebar.header("Costs")
    monthly_costs = st.sidebar.number_input("Maintenance monthly", value=450.0)
    buy_commission = st.sidebar.number_input("Buy commission %", value=1.0)
    sell_commission = st.sidebar.number_input("Sell commission %", value=1.0)

    # India mode inputs
    if mode == "India real-world model":
        tax_rate = st.sidebar.selectbox("Tax bracket", [0.1,0.2,0.3])
        invest_return = st.sidebar.number_input("Investment return %", value=10.0)
        cap_gain_tax = st.sidebar.number_input("Capital gains tax %", value=20.0)

    # ---------------- EMI ----------------
    downpayment = price * down_pct/100
    loan_amt = price - downpayment
    r = loan_rate/100/12
    n = tenure*12
    emi = loan_amt*r*(1+r)**n/((1+r)**n-1)

    st.metric("Monthly EMI", f"{emi:,.2f}")

    # =====================================================
    # NPV FUNCTION
    # =====================================================
    def compute_npv(horizon_years, include_sale, hg, rg):

        months = int(horizon_years * 12)
        monthly_disc = disc/100/12

        # ---------- BUY ----------
        balance = loan_amt
        cf_buy = []

        initial = downpayment + price*buy_commission/100
        cf_buy.append(-initial)

        for m in range(1, months+1):

            interest = balance*r
            principal = emi - interest
            balance -= principal

            tax_benefit = 0
            if mode == "India real-world model":
                interest_tax = min(interest*12,200000)*tax_rate/12
                principal_tax = min(principal*12,150000)*tax_rate/12
                tax_benefit = interest_tax + principal_tax

            cf_buy.append(-(emi + monthly_costs) + tax_benefit)

        if include_sale:
            sale_price = price*(1+hg/100)**horizon_years
            sale_net = sale_price*(1-sell_commission/100) - balance

            if mode == "India real-world model":
                gain = sale_price - price
                cap_tax = max(gain,0)*cap_gain_tax/100
                sale_net -= cap_tax

            cf_buy[-1] += sale_net

        # ---------- RENT ----------
        cf_rent=[0]
        rent=rent0
        invest = downpayment

        for m in range(1, months+1):
            rent = rent*(1+rg/100/12)

            if mode == "India real-world model":
                sip = max(emi - rent, 0)
                invest = invest*(1+invest_return/100/12) + sip

            cf_rent.append(-rent)

        if mode == "India real-world model":
            cf_rent[-1] += invest

        def npv(rate, cfs):
            return sum(cf/((1+rate)**i) for i,cf in enumerate(cfs))

        return npv(monthly_disc, cf_buy), npv(monthly_disc, cf_rent)

    # ---------------- LIVE ----------------
    if hold_to_end:
        horizon = tenure
        include_sale=False
    else:
        horizon = exit_year
        include_sale=True

    buy_now, rent_now = compute_npv(horizon, include_sale, house_growth, rent_growth)

    st.subheader("Live decision")

    if buy_now > rent_now:
        st.success("Buying financially better")
    else:
        st.warning("Renting financially better")

    c1,c2 = st.columns(2)
    c1.metric("NPV Buy", f"{buy_now:,.0f}")
    c2.metric("NPV Rent", f"{rent_now:,.0f}")

    # ---------------- COMPARISON ----------------
    st.subheader("Sell vs Hold comparison")

    b1,r1 = compute_npv(exit_year, True, house_growth, rent_growth)
    b2,r2 = compute_npv(tenure, False, house_growth, rent_growth)

    df = pd.DataFrame({
        "Scenario":["Sell after chosen years","Hold till loan end"],
        "NPV Buy":[b1,b2],
        "NPV Rent":[r1,r2],
        "Buy − Rent":[b1-r1,b2-r2]
    })
    st.dataframe(df)

    # ---------------- BREAK EVEN ----------------
    st.subheader("Break-even holding period")

    be=None
    for y in range(1, tenure+1):
        b,r = compute_npv(y, True, house_growth, rent_growth)
        if b>r:
            be=y
            break

    if be:
        st.info(f"Buying becomes better after ~ {be} years")
    else:
        st.info("Renting better across horizon")

    # ---------------- NPV vs YEARS ----------------
    st.subheader("NPV vs years")

    years=list(range(1, tenure+1))
    buy_vals=[]
    rent_vals=[]

    for y in years:
        b,r = compute_npv(y, True, house_growth, rent_growth)
        buy_vals.append(b)
        rent_vals.append(r)

    fig=go.Figure()
    fig.add_trace(go.Scatter(x=years,y=buy_vals,name="Buy"))
    fig.add_trace(go.Scatter(x=years,y=rent_vals,name="Rent"))
    st.plotly_chart(fig,use_container_width=True)

    # ---------------- MONTE CARLO ----------------
    st.subheader("Monte Carlo simulation")

    sims = st.slider("Simulations",100,2000,500)

    if st.button("Run Monte Carlo"):

        outcomes=[]

        for _ in range(sims):
            hg = np.random.normal(house_growth,1.5)
            rg = np.random.normal(rent_growth,1.0)
            b,r = compute_npv(horizon, include_sale, hg, rg)
            outcomes.append(b-r)

        prob = np.mean(np.array(outcomes)>0)
        st.metric("Probability buying wins", f"{prob:.2%}")

        fig2 = go.Figure()
        fig2.add_histogram(x=outcomes)
        st.plotly_chart(fig2,use_container_width=True)

with tab2:
    st.markdown("""
Simple mode → matches teaching case exactly  
India mode → adds tax + investing realism  
""")
