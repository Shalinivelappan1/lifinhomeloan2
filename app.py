import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏠 Buy vs Rent — India Classroom Simulator (₹)")
st.caption("Developer: Dr. Shalini Velappan")

tab1, tab2 = st.tabs(["Simulator", "Student Guide"])

# =====================================================
# SIMULATOR
# =====================================================
with tab1:

    # ---------- PROPERTY ----------
    st.sidebar.header("Property (₹)")

    price = st.sidebar.number_input("House price (₹)", value=8000000.0)
    down_pct = st.sidebar.number_input("Down payment %", value=20.0)
    loan_rate = st.sidebar.number_input("Loan interest %", value=8.5)
    tenure = st.sidebar.number_input("Loan tenure (years)", value=25)

    # ---------- RENT ----------
    st.sidebar.header("Rent")

    rent0 = st.sidebar.number_input("Monthly rent (₹)", value=25000.0)
    rent_growth = st.sidebar.number_input("Rent growth %", value=5.0)

    # ---------- MARKET ----------
    st.sidebar.header("Market")

    house_growth = st.sidebar.number_input("House price growth %", value=5.0)
    disc = st.sidebar.number_input("Investment return %", value=8.0)

    inflation_toggle = st.sidebar.checkbox("Use real (inflation-adjusted) analysis")
    inflation = st.sidebar.number_input("Inflation %", value=5.0)

    # ---------- HOLDING ----------
    st.sidebar.header("Holding period")

    lifetime = st.sidebar.checkbox("Hold till lifetime (no sale)")
    if lifetime:
        exit_year = 60
    else:
        exit_year = st.sidebar.number_input(
            "Sell after years", min_value=1, value=10
        )

    # ---------- COSTS ----------
    st.sidebar.header("Costs")

    buy_cost_pct = st.sidebar.number_input(
        "Stamp + registration %", value=7.0
    )
    sell_commission = st.sidebar.number_input("Sell cost %", value=2.0)
    monthly_costs = st.sidebar.number_input(
        "Maintenance/month (₹)", value=4000.0
    )

    # ---------- TAX ----------
    st.sidebar.header("Tax benefits (India)")

    tax_rate = st.sidebar.number_input("Income tax rate %", value=30.0)

    use_tax = st.sidebar.checkbox("Apply tax deductions")

    # ---------- EMI ----------
    downpayment = price * down_pct/100
    loan_amt = price - downpayment

    r = loan_rate/100/12
    n = tenure*12

    emi = loan_amt*r*(1+r)**n/((1+r)**n-1)
    st.metric("Monthly EMI", f"₹ {emi:,.0f}")

    # ---------- DISCOUNT RATE ----------
    if inflation_toggle:
        real_disc = (1+disc/100)/(1+inflation/100)-1
        monthly_disc = real_disc/12
    else:
        monthly_disc = disc/100/12

    # =====================================================
    # NPV FUNCTION
    # =====================================================
    def compute_npv(hg, rg):

        months = int(exit_year*12)

        # ---------- BUY ----------
        cf_buy = []

        initial = downpayment + price*buy_cost_pct/100
        cf_buy.append(-initial)

        balance = loan_amt

        for m in range(1, months+1):

            interest = balance*r
            principal = emi - interest
            balance -= principal

            tax_save = 0

            if use_tax:
                annual_interest = interest*12
                interest_ded = min(annual_interest, 200000)
                tax_save += interest_ded * tax_rate/100/12

                principal_ded = min(principal*12, 150000)
                tax_save += principal_ded * tax_rate/100/12

            cf_buy.append(-(emi + monthly_costs - tax_save))

        # resale
        if not lifetime:
            sale_price = price*(1+hg/100)**exit_year
            sale_net = sale_price*(1-sell_commission/100) - balance
            cf_buy[-1] += sale_net

        # ---------- RENT ----------
        cf_rent = []

        invest0 = downpayment + price*buy_cost_pct/100
        cf_rent.append(-invest0)

        rent = rent0
        invest_balance = invest0

        for m in range(1, months+1):

            invest_balance *= (1 + monthly_disc)
            rent = rent*(1 + rg/100/12)

            cf_rent.append(-rent)

        cf_rent[-1] += invest_balance

        def npv(rate, cfs):
            return sum(cf/((1+rate)**i) for i, cf in enumerate(cfs))

        return npv(monthly_disc, cf_buy), npv(monthly_disc, cf_rent)

    # =====================================================
    # SCENARIOS
    # =====================================================
    st.subheader("Scenario comparison")

    scenarios = {
        "Base": (house_growth, rent_growth),
        "Boom": (house_growth+2, rent_growth),
        "Slow": (house_growth-2, rent_growth)
    }

    rows=[]
    for name,(hg,rg) in scenarios.items():
        b,rn = compute_npv(hg,rg)
        rows.append([name,b,rn,b-rn])

    df = pd.DataFrame(rows,
        columns=["Scenario","NPV Buy","NPV Rent","Buy-Rent"]
    )
    st.dataframe(df, use_container_width=True)

    # =====================================================
    # BREAK-EVEN TENURE
    # =====================================================
    st.subheader("Break-even holding period")

    tenures = range(1,31)
    diffs=[]

    for t in tenures:
        exit_year_backup = exit_year
        globals()['exit_year'] = t
        b,rn = compute_npv(house_growth, rent_growth)
        diffs.append(b-rn)
        globals()['exit_year'] = exit_year_backup

    fig = go.Figure()
    fig.add_scatter(x=list(tenures), y=diffs)
    fig.add_hline(y=0)

    fig.update_layout(
        xaxis_title="Years stayed in house",
        yaxis_title="NPV(Buy − Rent)"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "The break-even tenure is where the line crosses zero. "
        "Short stays favour renting because transaction costs dominate. "
        "Long stays favour buying because equity builds over time."
    )

# =====================================================
# STUDENT GUIDE
# =====================================================
with tab2:

    st.header("How to interpret")

    st.markdown("""
### Decision rule
If NPV(Buy) > NPV(Rent) → Buying creates more wealth  
If NPV(Rent) > NPV(Buy) → Renting is financially better  

### Why tenure matters
Buying has high upfront costs (stamp duty, taxes).
So short stays make buying unattractive.

### Why leverage matters
Home buying is leveraged.
If prices rise → wealth increases fast.
If prices stagnate → returns collapse.

### Why tax benefits matter
Section 80C and Section 24 reduce effective EMI.
But they rarely flip the decision alone.

### Key classroom insight
Most households underestimate:
- opportunity cost of down payment
- effect of inflation
- impact of tenure
""")
