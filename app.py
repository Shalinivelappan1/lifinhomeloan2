import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏠 Buy vs Rent — NPV Simulator")
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

    exit_year = st.sidebar.number_input(
        "Sell after years",
        min_value=1,
        value=10
    )

    hold_to_end = st.sidebar.checkbox("Hold till loan end (no resale)")

    st.sidebar.header("Costs")
    buy_commission = st.sidebar.number_input("Buy commission %", value=1.0)
    sell_commission = st.sidebar.number_input("Sell commission %", value=1.0)
    monthly_costs = st.sidebar.number_input("Maintenance+tax+repairs (monthly)", value=450.0)

    # ---------- EMI ----------
    downpayment = price * down_pct/100
    loan_amt = price - downpayment

    r = loan_rate/100/12
    n = tenure*12

    emi = loan_amt*r*(1+r)**n/((1+r)**n-1)
    st.metric("Monthly EMI", f"{emi:,.2f}")

    # =====================================================
    # NPV FUNCTION
    # =====================================================
    def compute_npv(hg, rg, hold_mode=False):

        if hold_mode:
            months = int(tenure*12)
        else:
            months = int(exit_year*12)

        monthly_disc = disc/100/12

        # ---------- BUY ----------
        cf_buy = []

        initial = downpayment + price*buy_commission/100 + 0.03*price + 8000
        cf_buy.append(-initial)

        balance = loan_amt

        for m in range(1, months+1):
            interest = balance*r
            principal = emi - interest
            balance -= principal
            cf_buy.append(-(emi + monthly_costs))

        # resale only if selling
        if not hold_mode:
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

        return npv(monthly_disc, cf_buy), npv(monthly_disc, cf_rent)

    # =====================================================
    # COMPARISON TABLE
    # =====================================================
    st.subheader("Comparison: Sell vs Hold")

    buy_sell, rent_sell = compute_npv(house_growth, rent_growth, hold_mode=False)
    buy_hold, rent_hold = compute_npv(house_growth, rent_growth, hold_mode=True)

    comp_df = pd.DataFrame({
        "Scenario": ["Sell after chosen years", "Hold till loan end"],
        "NPV Buy": [buy_sell, buy_hold],
        "NPV Rent": [rent_sell, rent_hold],
        "Buy − Rent": [buy_sell - rent_sell, buy_hold - rent_hold]
    })

    st.dataframe(comp_df)

    # =====================================================
    # SCENARIO TABLE
    # =====================================================
    st.subheader("Scenario comparison (sell case)")

    scenarios = {
        "Base": (house_growth, rent_growth),
        "Boom": (house_growth+1, rent_growth),
        "Crash": (house_growth-1, rent_growth)
    }

    rows=[]
    for name,(hg,rg) in scenarios.items():
        b,rn = compute_npv(hg,rg,hold_mode=False)
        rows.append([name,b,rn,b-rn])

    df = pd.DataFrame(rows, columns=["Scenario","NPV Buy","NPV Rent","Buy-Rent"])
    st.dataframe(df)

    # =====================================================
    # SENSITIVITY
    # =====================================================
    st.subheader("Growth sensitivity")

    g = st.slider("House growth", -5.0, 5.0, float(house_growth))
    b,rn = compute_npv(g, rent_growth, hold_mode=hold_to_end)

    col1,col2 = st.columns(2)
    col1.metric("NPV Buy", f"{b:,.0f}")
    col2.metric("NPV Rent", f"{rn:,.0f}")

    # =====================================================
    # MONTE CARLO
    # =====================================================
    st.subheader("Monte Carlo")

    if st.button("Run Monte Carlo"):
        sims=500
        results=[]

        for _ in range(sims):
            hg=np.random.normal(house_growth,1)
            rg=np.random.normal(rent_growth,1)
            b,rn = compute_npv(hg,rg,hold_mode=hold_to_end)
            results.append(b-rn)

        prob = np.mean(np.array(results)>0)
        st.metric("Probability buy wins", f"{prob:.2%}")

        fig=go.Figure()
        fig.add_histogram(x=results)
        st.plotly_chart(fig,use_container_width=True)

# =====================================================
# STUDENT GUIDE
# =====================================================
with tab2:

    st.header("How to interpret")

    st.markdown("""
**Decision rule**

If NPV(Buy) > NPV(Rent) → Buy  
If NPV(Rent) > NPV(Buy) → Rent  

**When renting is better**
- Short holding period  
- Low price growth  
- High interest rates  

**When buying is better**
- Long stay  
- Strong price growth  
- Rising rent  

Comparing “sell vs hold” shows:
Short stay → renting often wins  
Lifetime stay → buying often wins  
""")
