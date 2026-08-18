import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Palo Alto Networks | Workforce Attrition Analysis", layout="wide")

# ---------- Load & clean data ----------
@st.cache_data
def load_data():
    df = pd.read_csv("Palo_Alto_Networks.csv")
    df["Department"] = df["Department"].str.strip()
    df["JobRole"] = df["JobRole"].str.strip()
    df["AttritionLabel"] = df["Attrition"].map({0: "Stayed", 1: "Left"})
    bins = [17, 25, 35, 45, 60]
    labels = ["18-25", "26-35", "36-45", "46-60"]
    df["AgeGroup"] = pd.cut(df["Age"], bins=bins, labels=labels)
    tbins = [-1, 2, 5, 10, 40]
    tlabels = ["0-2 yrs", "3-5 yrs", "6-10 yrs", "10+ yrs"]
    df["TenureBucket"] = pd.cut(df["YearsAtCompany"], bins=tbins, labels=tlabels)
    return df

df = load_data()

# ---------- Sidebar filters (User Capabilities) ----------
st.sidebar.title("🔍 Filters")
dept_sel = st.sidebar.multiselect("Department", sorted(df["Department"].unique()),
                                   default=sorted(df["Department"].unique()))
role_sel = st.sidebar.multiselect("Job Role", sorted(df["JobRole"].unique()),
                                   default=sorted(df["JobRole"].unique()))
tenure_range = st.sidebar.slider("Tenure Range (Years at Company)",
                                  int(df["YearsAtCompany"].min()), int(df["YearsAtCompany"].max()),
                                  (int(df["YearsAtCompany"].min()), int(df["YearsAtCompany"].max())))
ot_sel = st.sidebar.multiselect("OverTime", df["OverTime"].unique(), default=list(df["OverTime"].unique()))
travel_sel = st.sidebar.multiselect("Business Travel", df["BusinessTravel"].unique(),
                                     default=list(df["BusinessTravel"].unique()))

fdf = df[
    (df["Department"].isin(dept_sel)) &
    (df["JobRole"].isin(role_sel)) &
    (df["YearsAtCompany"].between(*tenure_range)) &
    (df["OverTime"].isin(ot_sel)) &
    (df["BusinessTravel"].isin(travel_sel))
]

st.title("🛡️ Workforce Attrition Patterns and Risk Hotspot Analysis")
st.caption("Palo Alto Networks — HR Analytics Dashboard")

if fdf.empty:
    st.warning("No employees match the selected filters. Adjust filters in the sidebar.")
    st.stop()

# ---------- KPI row ----------
overall_rate = fdf["Attrition"].mean() * 100
left_count = int(fdf["Attrition"].sum())
stayed_count = len(fdf) - left_count
avg_tenure_left = fdf.loc[fdf["Attrition"] == 1, "YearsAtCompany"].mean()
ot_rate = fdf.loc[fdf["OverTime"] == "Yes", "Attrition"].mean() * 100 if (fdf["OverTime"] == "Yes").any() else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Employees", f"{len(fdf):,}")
c2.metric("Attrition Rate", f"{overall_rate:.1f}%")
c3.metric("Employees Left", f"{left_count:,}")
c4.metric("Avg Tenure of Leavers", f"{avg_tenure_left:.1f} yrs" if left_count else "N/A")
c5.metric("Attrition Rate (OverTime staff)", f"{ot_rate:.1f}%")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Attrition Overview", "🏢 Department & Role Heatmaps",
    "👥 Demographic Explorer", "⏳ Tenure & Workload Analysis"
])

# ---------- Tab 1: Overview ----------
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        pie = px.pie(fdf, names="AttritionLabel", title="Retained vs Exited Employees",
                      color="AttritionLabel", color_discrete_map={"Stayed": "#2E86AB", "Left": "#E63946"})
        st.plotly_chart(pie, use_container_width=True)
    with col2:
        dept_rate = fdf.groupby("Department")["Attrition"].mean().reset_index()
        dept_rate["Attrition"] *= 100
        bar = px.bar(dept_rate.sort_values("Attrition", ascending=False), x="Department", y="Attrition",
                      title="Attrition Rate by Department (%)", text_auto=".1f", color="Attrition",
                      color_continuous_scale="Reds")
        st.plotly_chart(bar, use_container_width=True)

    role_rate = fdf.groupby("JobRole")["Attrition"].agg(["mean", "count"]).reset_index()
    role_rate["mean"] *= 100
    role_rate = role_rate.sort_values("mean", ascending=False)
    bar2 = px.bar(role_rate, x="mean", y="JobRole", orientation="h", text_auto=".1f",
                   title="Attrition Rate by Job Role (%)", labels={"mean": "Attrition Rate (%)"},
                   color="mean", color_continuous_scale="Oranges")
    bar2.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(bar2, use_container_width=True)

# ---------- Tab 2: Heatmaps ----------
with tab2:
    pivot = fdf.pivot_table(values="Attrition", index="Department", columns="JobLevel", aggfunc="mean") * 100
    heat = px.imshow(pivot, text_auto=".1f", color_continuous_scale="Reds", aspect="auto",
                      title="Attrition Intensity: Department x Job Level (%)",
                      labels=dict(color="Attrition %"))
    st.plotly_chart(heat, use_container_width=True)

    pivot2 = fdf.pivot_table(values="Attrition", index="JobRole", columns="Department", aggfunc="mean") * 100
    heat2 = px.imshow(pivot2, text_auto=".1f", color_continuous_scale="Reds", aspect="auto",
                       title="Attrition Intensity: Job Role x Department (%)",
                       labels=dict(color="Attrition %"))
    st.plotly_chart(heat2, use_container_width=True)

    st.subheader("🚨 High-Risk Segments (Attrition ≥ 25%, n ≥ 20)")
    risk = fdf.groupby(["Department", "JobRole"])["Attrition"].agg(["mean", "count"]).reset_index()
    risk["mean"] *= 100
    risk = risk[(risk["mean"] >= 25) & (risk["count"] >= 20)].sort_values("mean", ascending=False)
    risk.columns = ["Department", "Job Role", "Attrition Rate (%)", "Employee Count"]
    st.dataframe(risk.style.format({"Attrition Rate (%)": "{:.1f}"}), use_container_width=True)

# ---------- Tab 3: Demographics ----------
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        age_rate = fdf.groupby("AgeGroup", observed=True)["Attrition"].mean().reset_index()
        age_rate["Attrition"] *= 100
        st.plotly_chart(px.bar(age_rate, x="AgeGroup", y="Attrition", text_auto=".1f",
                                title="Attrition by Age Group (%)", color="Attrition",
                                color_continuous_scale="Teal"), use_container_width=True)
    with col2:
        gen_rate = fdf.groupby("Gender")["Attrition"].mean().reset_index()
        gen_rate["Attrition"] *= 100
        st.plotly_chart(px.bar(gen_rate, x="Gender", y="Attrition", text_auto=".1f",
                                title="Attrition by Gender (%)", color="Gender"), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        mar_rate = fdf.groupby("MaritalStatus")["Attrition"].mean().reset_index()
        mar_rate["Attrition"] *= 100
        st.plotly_chart(px.bar(mar_rate, x="MaritalStatus", y="Attrition", text_auto=".1f",
                                title="Attrition by Marital Status (%)", color="MaritalStatus"),
                         use_container_width=True)
    with col4:
        edu_rate = fdf.groupby("EducationField")["Attrition"].mean().reset_index()
        edu_rate["Attrition"] *= 100
        edu_rate = edu_rate.sort_values("Attrition", ascending=False)
        st.plotly_chart(px.bar(edu_rate, x="EducationField", y="Attrition", text_auto=".1f",
                                title="Attrition by Education Field (%)", color="Attrition",
                                color_continuous_scale="Purples"), use_container_width=True)

# ---------- Tab 4: Tenure & Workload ----------
with tab4:
    col1, col2 = st.columns(2)
    with col1:
        ten_rate = fdf.groupby("TenureBucket", observed=True)["Attrition"].mean().reset_index()
        ten_rate["Attrition"] *= 100
        st.plotly_chart(px.bar(ten_rate, x="TenureBucket", y="Attrition", text_auto=".1f",
                                title="Attrition by Tenure Bucket (%)", color="Attrition",
                                color_continuous_scale="YlOrBr"), use_container_width=True)
    with col2:
        promo = fdf.groupby("YearsSinceLastPromotion")["Attrition"].mean().reset_index()
        promo["Attrition"] *= 100
        st.plotly_chart(px.line(promo, x="YearsSinceLastPromotion", y="Attrition", markers=True,
                                 title="Attrition vs Years Since Last Promotion (%)"),
                         use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        ot_rate2 = fdf.groupby("OverTime")["Attrition"].mean().reset_index()
        ot_rate2["Attrition"] *= 100
        st.plotly_chart(px.bar(ot_rate2, x="OverTime", y="Attrition", text_auto=".1f",
                                title="Attrition: OverTime vs No OverTime (%)",
                                color="OverTime", color_discrete_map={"Yes": "#E63946", "No": "#2E86AB"}),
                         use_container_width=True)
    with col4:
        bt_rate = fdf.groupby("BusinessTravel")["Attrition"].mean().reset_index()
        bt_rate["Attrition"] *= 100
        order = ["Non-Travel", "Travel_Rarely", "Travel_Frequently"]
        bt_rate["BusinessTravel"] = pd.Categorical(bt_rate["BusinessTravel"], categories=order, ordered=True)
        bt_rate = bt_rate.sort_values("BusinessTravel")
        st.plotly_chart(px.bar(bt_rate, x="BusinessTravel", y="Attrition", text_auto=".1f",
                                title="Attrition by Business Travel Frequency (%)", color="Attrition",
                                color_continuous_scale="Blues"), use_container_width=True)

    dist_bins = [0, 5, 10, 20, 30]
    dist_labels = ["0-5 km", "6-10 km", "11-20 km", "21-30 km"]
    fdf2 = fdf.copy()
    fdf2["DistBucket"] = pd.cut(fdf2["DistanceFromHome"], bins=dist_bins, labels=dist_labels, include_lowest=True)
    dist_rate = fdf2.groupby("DistBucket", observed=True)["Attrition"].mean().reset_index()
    dist_rate["Attrition"] *= 100
    st.plotly_chart(px.bar(dist_rate, x="DistBucket", y="Attrition", text_auto=".1f",
                            title="Attrition by Distance From Home (%)", color="Attrition",
                            color_continuous_scale="Greens"), use_container_width=True)

st.divider()
st.caption("Workforce Attrition Patterns and Risk Hotspot Analysis at Palo Alto Networks — "
           "Business Analytics Capstone Project | Built with Streamlit")
