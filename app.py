import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏠 Buy vs Rent — Classroom NPV Simulator")
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
    rent_growth = st.sidebar.number_input("Rent growth %", value=2.0)

    st.sidebar.header("Market")
    house_growth = st.sidebar.number_input("House price growth %", value=3.0)
    disc = st.sidebar.number_input("Discount / investment return %", value=5.0)

    st.sidebar.header("Holding period")

    lifetime = st.sidebar.checkbox("Hold till lifetime (no sale)")
    if lifetime:
        exit_year = 60
    else:
        exit_year = st.sidebar.number_input(
            "Sell after years", min_value=1, value=10
        )

    st.sidebar.header("Costs")
    buy_commission = st.sidebar.number_input("Buy commission %", value=1.0)
    sell_commission = st.sidebar.number_input("Sell commission %", value=1.0)
    monthly_costs = st.sidebar.number_input(
        "Maintenance + tax + repairs (monthly)", value=450.0
    )

    # ---------- EMI ----------
    downpayment = price * down_pct/100
    loan_amt = price - downpayment

    r = loan_rate/100/12
    n = tenure*12

    emi = loan_amt*r*(1+r)**n/((1+r)**n-1)
    st.metric("Monthly EMI", f"{emi:,.2f}")

    # ---------- TEACHING: YEAR 1 BREAKDOWN ----------
    year1_interest = 0
    year1_principal = 0
    bal = loan_amt

    for m in range(12):
        i = bal*r
        p = emi - i
        bal -= p
        year1_interest += i
        year1_principal += p

    st.info(
        f"Year-1 interest: {year1_interest:,.0f} | "
        f"principal repaid: {year1_principal:,.0f}"
    )

    # =====================================================
    # NPV FUNCTION
    # =====================================================
    def compute_npv(hg, rg):

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

        # resale only if not lifetime hold
        if not lifetime:
            sale_price = price*(1+hg/100)**exit_year
            sale_net = sale_price*(1-sell_commission/100) - balance
            cf_buy[-1] += sale_net

        # ---------- RENT WITH INVESTMENT ----------
        cf_rent = []

        invest0 = downpayment + price*buy_commission/100 + 0.03*price + 8000
        cf_rent.append(-invest0)

        rent = rent0
        invest_balance = invest0

        for m in range(1, months+1):

            invest_balance *= (1 + monthly_disc)
            rent = rent*(1 + rg/100/12)

            cf_rent.append(-rent)

        cf_rent[-1] += invest_balance

        # ---------- NPV ----------
        def npv(rate, cfs):
            return sum(cf/((1+rate)**i) for i, cf in enumerate(cfs))

        return npv(monthly_disc, cf_buy), npv(monthly_disc, cf_rent)

    # =====================================================
    # SCENARIOS
    # =====================================================
    st.subheader("Scenario comparison")

    scenarios = {
        "Base": (house_growth, rent_growth),
        "Boom": (house_growth+1, rent_growth),
        "Crash": (house_growth-1, rent_growth)
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
    # SENSITIVITY
    # =====================================================
    st.subheader("Growth sensitivity")

    g = st.slider("House price growth %", -5.0, 8.0, float(house_growth))
    b,rn = compute_npv(g, rent_growth)

    col1,col2,col3 = st.columns(3)
    col1.metric("NPV Buy", f"{b:,.0f}")
    col2.metric("NPV Rent", f"{rn:,.0f}")
    col3.metric("Buy advantage (₹)", f"{b-rn:,.0f}")

    # =====================================================
    # BREAK-EVEN CHART
    # =====================================================
    st.subheader("Break-even house price growth")

growths = np.linspace(-5,8,40)
diffs=[]

for gr in growths:
    b,rn = compute_npv(gr, rent_growth)
    diffs.append(b-rn)

fig = go.Figure()

# main line
fig.add_scatter(
    x=growths,
    y=diffs,
    mode="lines",
    line=dict(width=5),
    name="Buy advantage"
)

# zero line
fig.add_hline(
    y=0,
    line_width=4,
    line_dash="solid",
)

# layout for classroom projection
fig.update_layout(
    height=520,
    template="simple_white",
    title_font=dict(size=26),
    font=dict(size=18),
    xaxis=dict(
        title="Annual house price growth (%)",
        title_font=dict(size=22),
        tickfont=dict(size=18)
    ),
    yaxis=dict(
        title="NPV difference (₹ Buy − Rent)",
        title_font=dict(size=22),
        tickfont=dict(size=18)
    ),
    margin=dict(l=40,r=40,t=40,b=40)
)

st.plotly_chart(fig, use_container_width=True)
st.info(
"Where the line crosses zero is the break-even growth rate. "
"To the right → buying creates more wealth. "
"To the left → renting is financially better. "
"This shows that buying is essentially a leveraged bet on house price growth."
)

    # =====================================================
    # MONTE CARLO
    # =====================================================
    st.subheader("Monte Carlo simulation")

    if st.button("Run Monte Carlo"):

        sims = 500
        results=[]

        cov = [[1,0.4],[0.4,1]]
        means = [house_growth, rent_growth]

        for _ in range(sims):
            hg,rg = np.random.multivariate_normal(means,cov)
            b,rn = compute_npv(hg,rg)
            results.append(b-rn)

        prob = np.mean(np.array(results)>0)
        st.metric("Probability buying wins", f"{prob:.2%}")

        fig = go.Figure()
        fig.add_histogram(x=results)
        st.plotly_chart(fig, use_container_width=True)

# =====================================================
# STUDENT GUIDE
# =====================================================
with tab2:

    st.header("How to interpret")

    st.markdown("""
### Decision rule
If **NPV(Buy) > NPV(Rent)** → Buying creates more wealth  
If **NPV(Rent) > NPV(Buy)** → Renting is financially better  

### Key intuition
Buying a house is a **leveraged bet on house prices**.

### Renting wins when:
- Short stay  
- High interest rates  
- Low price growth  

### Buying wins when:
- Long stay  
- High rent growth  
- Strong price appreciation  

Small changes in assumptions can flip decisions.
This is why households often misjudge buy vs rent.
""")
