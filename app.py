import streamlit as st

from config.settings import get_settings

st.set_page_config(
    page_title="Flight Hunter AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

settings = get_settings()
st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 2rem;}
    div[data-testid="stForm"] {direction: rtl;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("✈️ Flight Hunter AI")
st.subheader("اعثر على أفضل أسعار تذاكر الطيران")
st.write("ابحث وقارن عروض الرحلات المتاحة، ثم انتقل إلى موقع مزود الحجز لإتمام الحجز.")

with st.form("flight_search"):
    left, right = st.columns(2)
    with left:
        origin = st.text_input("مطار المغادرة (رمز IATA)", value="CAI", max_chars=3)
        departure = st.date_input("تاريخ المغادرة")
        adults = st.number_input("عدد البالغين", min_value=1, max_value=9, value=1)
    with right:
        destination = st.text_input("مطار الوصول (رمز IATA)", value="JED", max_chars=3)
        trip_type = st.radio("نوع الرحلة", ["ذهاب فقط", "ذهاب وعودة"], horizontal=True)
        return_date = st.date_input("تاريخ العودة") if trip_type == "ذهاب وعودة" else None
    submitted = st.form_submit_button("ابحث عن الرحلات", type="primary", use_container_width=True)

if submitted:
    st.info(
        "تم تجهيز نموذج البحث. سيتم تفعيل جلب الأسعار الحقيقية بعد ربط مزود بيانات الطيران "
        "في المرحلة الثالثة. لن نعرض أسعارًا تجريبية على أنها عروض فعلية."
    )
    st.caption(f"المسار: {origin.upper()} ← {destination.upper()} | العملة الافتراضية: {settings.app_currency}")

st.divider()
st.caption("Flight Hunter AI · مقارنة شفافة · الحجز يتم لدى مزود الخدمة الخارجي")
