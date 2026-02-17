import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏠 Buy vs Rent — NPV Teaching Simulator")
st.caption("Developer: Dr. Shalini Velappan")

tab1, tab2 = st.tabs(["Simulator", "Student Guide"])

with tab1:

    # ================= MODEL TYPE =================
    mode = st.sidebar.radio(
        "Model type",
        ["Simple (teaching model)", "India real-world model"]
    )

    # ================= INPUTS =================
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

    # ================= INDIA MODE INPUTS =================
    if mode == "India real-world model":

        st.sidebar.header("Tax")
        tax_rate = st.sidebar.selectbox("Tax bracket", [0.1,0.2,0.3])
        invest_return = st.sidebar.number_input("Investment return %", value=10.0)
        cap_gain_tax = st.sidebar.number_input("Capital gains tax %", value=20.0)

        st.sidebar.header("HRA")
        salary = st.sidebar.number_input("Annual salary", value=1200000.0)
        hra_received = st.sidebar.number_input("HRA received", value=300000.0)
        metro = st.sidebar.checkbox("Metro city", True)

    # ================= EMI =================
    downpayment = price * down_pct/100
    loan_amt = price - downpayment
    r = loan_rate/100/12
    n = tenure*12
    emi = loan_amt*r*(1+r)**n/((1+r)**n-1)

    st.metric("Monthly EMI", f"{emi:,.2f}")

    # ================= HRA =================
    hra_tax_save_month = 0
    if mode == "India real-world model":
        rent_annual = rent0*12
        hra_exempt = min(
            hra_received,
            max(rent_annual - 0.1*salary,0),
            0.5*salary if metro else 0.4*salary
        )
        hra_tax_save_month = hra_exempt * tax_rate / 12

    # =====================================================
    # CORE FUNCTION
    # =====================================================
    def compute_npv(hg, rg, hold=False, years_override=None):

        if years_override is not None:
            months = int(years_override*12)
        elif hold:
            months = int(tenure*12)
        else:
            months = int(exit_year*12)

        monthly_disc = disc/100/12

        # ---------- BUY ----------
        balance = loan_amt
        cf_buy=[-downpayment]
        equity_track=[]

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
            equity_track.append(price - balance)

        # resale
        if not hold and years_override is None:
            sale_price = price*(1+hg/100)**exit_year
            sale_net = sale_price - balance

            if mode == "India real-world model":
                gain = sale_price - price
                cap_tax = max(gain,0)*cap_gain_tax/100
                sale_net -= cap_tax

            cf_buy[-1] += sale_net

        # ---------- RENT ----------
        cf_rent=[0]
        rent=rent0
        invest = downpayment  # reset each run

        for m in range(1, months+1):
            rent = rent*(1+rg/100/12)

            if mode == "India real-world model":
                sip = max(emi - rent, 0)
                invest = invest*(1+invest_return/100/12) + sip
                cf_rent.append(-rent + hra_tax_save_month)
            else:
                cf_rent.append(-rent)

        if mode == "India real-world model":
            cf_rent[-1] += invest

        def npv(rate,cfs):
            return sum(cf/((1+rate)**i) for i,cf in enumerate(cfs))

        return npv(monthly_disc,cf_buy), npv(monthly_disc,cf_rent), equity_track

    # =====================================================
    # LIVE DECISION
    # =====================================================
    buy_now, rent_now, equity_track = compute_npv(house_growth,rent_growth,hold_to_end)

    st.subheader("Live decision")

    if buy_now>rent_now:
        st.success("Buying financially better")
    else:
        st.warning("Renting financially better")

    c1,c2=st.columns(2)
    c1.metric("NPV Buy",f"{buy_now:,.0f}")
    c2.metric("NPV Rent",f"{rent_now:,.0f}")

    # =====================================================
    # COMPARISON TABLE
    # =====================================================
    st.subheader("Sell vs Hold comparison")

    b1,r1,_=compute_npv(house_growth,rent_growth,hold=False)
    b2,r2,_=compute_npv(house_growth,rent_growth,hold=True)

    df=pd.DataFrame({
        "Scenario":["Sell after chosen years","Hold till loan end"],
        "NPV Buy":[b1,b2],
        "NPV Rent":[r1,r2],
        "Buy − Rent":[b1-r1,b2-r2]
    })
    st.dataframe(df)

    # =====================================================
    # BREAK EVEN
    # =====================================================
    st.subheader("Break-even holding period")

    be=None
    for y in range(1,tenure+1):
        b,r,_=compute_npv(house_growth,rent_growth,hold=False,years_override=y)
        if b>r:
            be=y
            break

    if be:
        st.info(f"Buying becomes better after ~ {be} years")
    else:
        st.info("Renting better across horizon")

    # =====================================================
    # NPV VS YEARS
    # =====================================================
    st.subheader("NPV vs years")

    years=list(range(1,tenure+1))
    buy_vals=[]
    rent_vals=[]

    for y in years:
        b,r,_=compute_npv(house_growth,rent_growth,hold=False,years_override=y)
        buy_vals.append(b)
        rent_vals.append(r)

    fig=go.Figure()
    fig.add_trace(go.Scatter(x=years,y=buy_vals,name="Buy"))
    fig.add_trace(go.Scatter(x=years,y=rent_vals,name="Rent"))
    st.plotly_chart(fig,use_container_width=True)

    # =====================================================
    # EQUITY
    # =====================================================
    st.subheader("Equity build")

    eq_years=list(range(1,len(equity_track)//12+1))
    eq_vals=[equity_track[i*12-1] for i in eq_years]

    fig2=go.Figure()
    fig2.add_trace(go.Scatter(x=eq_years,y=eq_vals,name="Equity"))
    st.plotly_chart(fig2,use_container_width=True)

    # =====================================================
    # MONTE CARLO
    # =====================================================
    st.subheader("Monte Carlo")

    sims=st.slider("Simulations",100,1500,500)

    if st.button("Run Monte Carlo"):

        res=[]
        for _ in range(sims):
            hg=np.random.normal(house_growth,2)
            rg=np.random.normal(rent_growth,1.5)
            b,r,_=compute_npv(hg,rg,hold_to_end)
            res.append(b-r)

        prob=np.mean(np.array(res)>0)
        st.metric("Probability buying wins",f"{prob:.2%}")

        fig3=go.Figure()
        fig3.add_histogram(x=res)
        st.plotly_chart(fig3,use_container_width=True)

with tab2:
    st.markdown("""
**Simple model:**  
Matches classroom case numbers exactly.

**India model:**  
Includes tax benefits, HRA, SIP investing, capital gains.
""")
