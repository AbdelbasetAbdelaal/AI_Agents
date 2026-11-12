from datetime import date, timedelta

import streamlit as st
from pydantic import ValidationError

from config.settings import get_settings
from flight_hunter.airports import AIRPORTS, AIRPORT_LABELS
from flight_hunter.models import FlightSearchRequest

st.set_page_config(
    page_title="Flight Hunter AI | البحث عن الرحلات",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

settings = get_settings()
today = date.today()

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: 'Cairo', sans-serif;
    }
    .block-container {max-width: 1240px; padding-top: 1.5rem; padding-bottom: 3rem;}
    [data-testid="stAppViewContainer"] {direction: rtl;}
    [data-testid="stHeader"] {background: transparent;}
    [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {text-align: right;}
    div[data-testid="stForm"] {direction: rtl; border: 1px solid rgba(128,128,128,.22);
        border-radius: 18px; padding: 1.3rem 1.4rem; background: rgba(128,128,128,.035);}
    div[data-testid="stFormSubmitButton"] button {height: 3rem; font-weight: 700; border-radius: 10px;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 18px;
        background: linear-gradient(115deg, #102b46, #176b83); color: white; margin-bottom: 1.2rem;}
    .hero h1 {font-size: 2rem; margin: 0 0 .35rem 0; color: white;}
    .hero p {margin: 0; opacity: .9; font-size: 1rem;}
    .eyebrow {font-size: .78rem; letter-spacing: .08em; opacity: .8; font-weight: 700;}
    .section-title {font-size: 1.1rem; font-weight: 800; margin: .4rem 0 .8rem;}
    .empty-state {border: 1px dashed rgba(128,128,128,.45); border-radius: 16px;
        padding: 1.6rem; text-align: center; background: rgba(128,128,128,.035);}
    .empty-state .plane {font-size: 2rem;}
    .muted {color: #8492a0; font-size: .9rem;}
    .trust {padding: .9rem 1rem; border-radius: 12px; background: rgba(30,130,100,.08);
        border: 1px solid rgba(30,130,100,.2); font-size: .9rem;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">FLIGHT HUNTER AI · مصر</div>
      <h1>رحلتك القادمة تبدأ من هنا ✈️</h1>
      <p>قارن خيارات السفر بوضوح، واعثر على الرحلة الأنسب من حيث السعر والمدة والتوقفات.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-title">ابحث عن رحلة</div>', unsafe_allow_html=True)

with st.form("flight_search", border=True):
    trip_type = st.radio(
        "نوع الرحلة",
        ["ذهاب وعودة", "ذهاب فقط"],
        horizontal=True,
        index=0,
    )
    origin_col, destination_col = st.columns(2)
    with origin_col:
        origin_label = st.selectbox(
            "من (مطار المغادرة)",
            AIRPORT_LABELS,
            index=AIRPORT_LABELS.index("القاهرة — CAI"),
        )
    with destination_col:
        destination_options = [
            "جدة — JED", "المدينة المنورة — MED", "الرياض — RUH",
            "دبي — DXB", "أبوظبي — AUH", "الدوحة — DOH",
            "إسطنبول — IST", "لندن — LHR", "باريس — CDG",
            "القاهرة — CAI", "الإسكندرية — HBE",
        ]
        destination_label = st.selectbox("إلى (مطار الوصول)", destination_options, index=0)

    date_col, return_col = st.columns(2)
    with date_col:
        departure_date = st.date_input(
            "تاريخ المغادرة",
            value=today + timedelta(days=14),
            min_value=today,
            format="DD/MM/YYYY",
        )
    with return_col:
        if trip_type == "ذهاب وعودة":
            return_date = st.date_input(
                "تاريخ العودة",
                value=max(today + timedelta(days=21), departure_date + timedelta(days=7)),
                min_value=departure_date,
                format="DD/MM/YYYY",
            )
        else:
            return_date = None

    st.markdown("**المسافرون ودرجة السفر**")
    adult_col, child_col, cabin_col = st.columns(3)
    with adult_col:
        adults = st.number_input("البالغون", min_value=1, max_value=9, value=1, step=1)
    with child_col:
        children = st.number_input("الأطفال (2–11 سنة)", min_value=0, max_value=8, value=0, step=1)
    with cabin_col:
        cabin_label = st.selectbox("درجة السفر", ["اقتصادية", "اقتصادية ممتازة", "رجال الأعمال", "الأولى"])
    submitted = st.form_submit_button("ابحث عن أفضل الرحلات", type="primary", use_container_width=True)

if submitted:
    origin = origin_label.rsplit("—", 1)[-1].strip()
    destination = destination_label.rsplit("—", 1)[-1].strip()
    cabin_map = {
        "اقتصادية": "ECONOMY",
        "اقتصادية ممتازة": "PREMIUM_ECONOMY",
        "رجال الأعمال": "BUSINESS",
        "الأولى": "FIRST",
    }
    try:
        request = FlightSearchRequest(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=int(adults),
            children=int(children),
            cabin_class=cabin_map[cabin_label],
            currency=settings.app_currency,
        )
        st.session_state["flight_search_request"] = request.model_dump(mode="json")
        st.session_state["search_submitted"] = True
    except ValidationError as exc:
        st.session_state["search_submitted"] = False
        st.error("يرجى مراجعة بيانات الرحلة: " + "؛ ".join(error["msg"] for error in exc.errors()))

if st.session_state.get("search_submitted"):
    request = st.session_state["flight_search_request"]
    st.markdown('<div class="section-title">نتائج البحث</div>', unsafe_allow_html=True)
    st.caption(
        f'{request["origin"]} ← {request["destination"]}  ·  '
        f'{request["departure_date"]}  ·  '
        f'{"عودة " + request["return_date"] if request["return_date"] else "ذهاب فقط"}  ·  '
        f'{request["adults"]} بالغ / {request["children"]} طفل'
    )
    st.markdown(
        """
        <div class="empty-state">
          <div class="plane">🛫</div>
          <h3>واجهة البحث جاهزة — ربط الأسعار في المرحلة التالية</h3>
          <p>لم يتم جلب عروض مباشرة بعد. سنعرض هنا الرحلات المتاحة وأسعارها الحقيقية
          فور ربط مزودي بيانات الطيران في المرحلة الثالثة.</p>
          <p class="muted">لن نستخدم أسعارًا تجريبية أو نعرض بيانات غير مؤكدة على أنها أسعار فعلية.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class="empty-state">
          <div class="plane">🌍</div>
          <h3>إلى أين تريد السفر؟</h3>
          <p>أدخل تفاصيل رحلتك أعلاه، ثم اضغط على «ابحث عن أفضل الرحلات».</p>
          <p class="muted">ستظهر نتائج المقارنة هنا بعد تفعيل مصادر الأسعار المباشرة.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander("كيف نختار أفضل رحلة؟", expanded=False):
    st.write(
        "ستتم مقارنة الأسعار النهائية ومدد الرحلات وعدد التوقفات وشركات الطيران. "
        "يمكنك لاحقًا تصفية النتائج حسب السعر ومدة الرحلة والتوقفات وشركة الطيران. "
        "إتمام الحجز والدفع سيكون على موقع شركة الطيران أو مزود الحجز."
    )

st.markdown(
    '<div class="trust">🔒 شفافية الأسعار: لا توجد حاليًا نتائج مباشرة متصلة. '
    'لن يظهر سعر إلا بعد استلامه من مزود بيانات موثوق.</div>',
    unsafe_allow_html=True,
)
st.divider()
st.caption("Flight Hunter AI · الإصدار التأسيسي · العملة: EGP")
