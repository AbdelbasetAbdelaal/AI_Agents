from datetime import date, timedelta
import os

import streamlit as st
from pydantic import ValidationError

from flight_hunter.airports import AIRPORTS, AIRPORT_LABELS
from flight_hunter.models import FlightSearchRequest
from flight_hunter.fare_results import fare_age_label, filter_fares, parse_fare_csv
from flight_hunter.sources import SOURCES, build_google_flights_url, sources_by_category
from flight_hunter.serpapi_flights import FlightSearchError, search_google_flights

st.set_page_config(
    page_title="Flight Hunter AI | البحث عن الرحلات",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

today = date.today()
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {font-family:'Cairo',sans-serif;}
    .block-container {max-width:1240px;padding-top:1.5rem;padding-bottom:3rem;}
    [data-testid="stAppViewContainer"] {direction:rtl;}
    [data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"] {text-align:right;}
    div[data-testid="stForm"] {direction:rtl;border:1px solid rgba(128,128,128,.22);border-radius:18px;padding:1.3rem 1.4rem;background:rgba(128,128,128,.035);}
    div[data-testid="stFormSubmitButton"] button {height:3rem;font-weight:700;border-radius:10px;}
    .hero {padding:1.4rem 1.6rem;border-radius:18px;background:linear-gradient(115deg,#102b46,#176b83);color:white;margin-bottom:1.2rem;}
    .hero h1 {font-size:2rem;margin:0 0 .35rem;color:white;}
    .hero p {margin:0;opacity:.9;font-size:1rem;}
    .section-title {font-size:1.1rem;font-weight:800;margin:.4rem 0 .8rem;}
    .trust {padding:.9rem 1rem;border-radius:12px;background:rgba(30,130,100,.08);border:1px solid rgba(30,130,100,.2);font-size:.9rem;}
    footer {visibility:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div style="font-size:.78rem;letter-spacing:.08em;opacity:.8;font-weight:700;">FLIGHT HUNTER AI · مصر والسعودية</div>
      <h1>رحلتك القادمة تبدأ من هنا ✈️</h1>
      <p>ابحث عن رحلتك، ثم قارن بنفسك بين شركات الطيران ومواقع السفر من مصادرها الأصلية.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-title">ابحث عن رحلة</div>', unsafe_allow_html=True)
with st.form("flight_search", border=True):
    trip_type = st.radio("نوع الرحلة", ["ذهاب وعودة", "ذهاب فقط"], horizontal=True)
    col_from, col_to = st.columns(2)
    with col_from:
        origin_label = st.selectbox(
            "من (مطار المغادرة)", AIRPORT_LABELS,
            index=AIRPORT_LABELS.index("القاهرة — CAI"),
        )
    with col_to:
        destination_label = st.selectbox(
            "إلى (مطار الوصول)", AIRPORT_LABELS,
            index=AIRPORT_LABELS.index("جدة — JED"),
        )

    col_depart, col_return = st.columns(2)
    with col_depart:
        departure_date = st.date_input(
            "تاريخ المغادرة", value=today + timedelta(days=14),
            min_value=today, format="DD/MM/YYYY",
        )
    with col_return:
        return_date = None
        if trip_type == "ذهاب وعودة":
            return_date = st.date_input(
                "تاريخ العودة",
                value=max(today + timedelta(days=21), departure_date + timedelta(days=7)),
                min_value=departure_date, format="DD/MM/YYYY",
            )

    col_adults, col_children, col_currency = st.columns(3)
    with col_adults:
        adults = st.number_input("البالغون", min_value=1, max_value=9, value=1, step=1)
    with col_children:
        children = st.number_input("الأطفال (2–11 سنة)", min_value=0, max_value=8, value=0, step=1)
    with col_currency:
        currency = st.selectbox("العملة المفضلة عند المقارنة", ["EGP", "SAR", "USD"])

    submitted = st.form_submit_button("ابحث عن الرحلات وقارن الأسعار", type="primary", use_container_width=True)

if submitted:
    try:
        request = FlightSearchRequest(
            origin=AIRPORTS[origin_label],
            destination=AIRPORTS[destination_label],
            departure_date=departure_date,
            return_date=return_date,
            adults=int(adults),
            children=int(children),
            currency=currency,
        )
        st.session_state["flight_search_request"] = request.model_dump(mode="json")
        st.session_state["search_submitted"] = True
    except ValidationError as exc:
        st.session_state["search_submitted"] = False
        st.error("يرجى مراجعة بيانات الرحلة: " + "؛ ".join(item["msg"] for item in exc.errors()))

if st.session_state.get("search_submitted"):
    request = FlightSearchRequest.model_validate(st.session_state["flight_search_request"])
    st.markdown('<div class="section-title">مصادر البحث المناسبة لرحلتك</div>', unsafe_allow_html=True)
    route = f"{request.origin} → {request.destination}"
    date_text = request.departure_date.strftime("%d/%m/%Y")
    if request.return_date:
        date_text += " · عودة " + request.return_date.strftime("%d/%m/%Y")
    st.caption(f"{route} · {date_text} · {request.adults} بالغ · {request.children} طفل · العملة المفضلة: {request.currency}")

    st.success("تم تجهيز البحث. جدول المقارنة يعرض فقط عروض الأسعار الفعلية التي تم تحميلها والتحقق من بياناتها.")
    st.markdown('<div class="section-title">الوكيل الذكي للبحث عن الرحلات</div>', unsafe_allow_html=True)
    st.write("يبحث الوكيل دون استبعاد أي شركة طيران يعرضها Google Flights. في الذهاب والعودة يسترجع خيارات العودة المرتبطة برحلات الذهاب ثم يرتب الرحلات الكاملة حسب السعر.")
    api_key = st.text_input(
        "مفتاح SerpApi المجاني",
        value=os.getenv("SERPAPI_API_KEY", ""),
        type="password",
        help="أنشئ حسابًا مجانيًا في SerpApi وانسخ المفتاح من لوحة التحكم. لا تضع المفتاح في GitHub.",
        key="serpapi_key_input",
    )
    if st.button("ابدأ البحث الفعلي الآن", type="primary", use_container_width=True):
        try:
            with st.spinner("الوكيل يبحث عن الرحلات ويحلل النتائج..."):
                live_result = search_google_flights(
                    api_key=api_key,
                    origin=request.origin,
                    destination=request.destination,
                    departure_date=request.departure_date.isoformat(),
                    return_date=request.return_date.isoformat() if request.return_date else None,
                    adults=request.adults,
                    children=request.children,
                    currency=request.currency,
                )
            st.session_state["live_flight_result"] = live_result
            st.session_state["live_flight_query"] = request.model_dump(mode="json")
        except FlightSearchError as exc:
            st.error(str(exc))
        except Exception:
            st.error("حدث خطأ غير متوقع أثناء البحث. لم يتم عرض نتائج غير مؤكدة.")
    live_result = st.session_state.get("live_flight_result")
    if live_result and st.session_state.get("live_flight_query") == request.model_dump(mode="json"):
        offers = live_result.get("offers", [])
        st.caption(f"المصدر: {live_result['source']} · وقت التحقق: {live_result['checked_at']} · نوع الرحلة: {live_result['trip_type']}")
        if offers:
            st.metric("عدد العروض المسترجعة", len(offers))
            st.metric("أقل سعر ظهر في النتائج", f"{offers[0]['price']:,.0f} {offers[0]['currency']}")
            rows = [{
                "شركة الطيران": x["airline"],
                "تاريخ ووقت الذهاب": x["departure_at"],
                "تاريخ ووقت العودة": x.get("return_departure_at") or "—",
                "وصول الذهاب": x["arrival_at"],
                "وصول العودة": x.get("return_arrival_at") or "—",
                "السعر الإجمالي المعروض": x["price"],
                "العملة": x["currency"],
                "توقفات الذهاب": x["stops"],
                "توقفات العودة": x.get("return_stops") if x.get("return_stops") is not None else "—",
                "مدة الذهاب (دقيقة)": x["duration_minutes"],
                "مدة العودة (دقيقة)": x.get("return_duration_minutes") or "—",
                "الأمتعة / الملاحظات": x["baggage_summary"],
                "رقم الرحلة": x["flight_numbers"],
            } for x in offers]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.info("هذه عروض أعادها Google Flights عبر SerpApi وقت البحث. في الذهاب والعودة يعرض الجدول رحلتي الذهاب والعودة المرتبطتين والسعر كما أعاده المصدر. لم يتم استبعاد أي شركة طيران يعرضها المصدر، لكن هذا لا يضمن تغطية كل شركات السوق. تحقق من السعر النهائي والأمتعة لدى مقدم الحجز.")
            st.link_button("فتح Google Flights للتحقق والحجز", build_google_flights_url(request), use_container_width=True)
        else:
            st.warning("لم يُرجع المصدر عروضًا مطابقة. جرّب تاريخًا آخر أو تحقق من رموز المطارات.")
    st.caption("الحصة المجانية المعلنة من SerpApi هي 250 عملية بحث شهريًا. بحث الذهاب والعودة يستهلك عدة عمليات لاسترجاع خيارات العودة. راجع لوحة حسابك لمعرفة الحصة الفعلية.")
    st.link_button("ابحث عن هذه الرحلة في Google Flights", build_google_flights_url(request), type="primary", use_container_width=True)

    st.markdown('<div class="section-title">مقارنة الأسعار الفعلية</div>', unsafe_allow_html=True)
    st.write("ارفع ملف CSV لعروض أسعار حصلت عليها من مصدر يسمح صراحةً بإعادة استخدامها. لا يجمع التطبيق أسعار Wego أو Wingie آلياً؛ شروطهما تمنع الاستعلامات أو جمع الأسعار آلياً.")
    with st.expander("صيغة ملف الأسعار المطلوبة", expanded=False):
        st.code("provider,airline,origin,destination,departure_at,arrival_at,cabin_class,price,currency,stops,duration_minutes,checked_at,passengers,return_departure_at,baggage_summary,booking_url", language="text")
        st.caption("الدرجات المقبولة: economy / premium economy / business / first أو المقابل العربي. يجب أن يطابق الملف تاريخ الرحلة وعدد المسافرين؛ وللذهاب والعودة أضف return_departure_at. رابط العرض HTTPS.")
    uploaded_fares = st.file_uploader("ارفع ملف أسعار CSV", type=["csv"], key="fare_csv")
    if uploaded_fares is not None:
        fare_records, fare_errors = parse_fare_csv(uploaded_fares.getvalue())
        matching = [item for item in fare_records if item.origin == request.origin and item.destination == request.destination and item.departure_at[:10] == request.departure_date.isoformat() and item.passengers == request.adults + request.children and (request.return_date is None or item.return_departure_at[:10] == request.return_date.isoformat())]
        if fare_errors:
            with st.expander(f"ملاحظات التحقق ({len(fare_errors)})", expanded=False):
                for message in fare_errors:
                    st.warning(message)
        if not matching:
            st.info("لا توجد عروض صالحة لهذا المسار في الملف. لم تتم إضافة أسعار تقديرية.")
        else:
            cabin = st.selectbox("درجة السفر", ["الكل", "اقتصادي", "اقتصادي ممتاز", "أعمال", "أولى"], key="fare_cabin")
            currency_filter = st.selectbox("عملة السعر", sorted({item.currency for item in matching}), key="fare_currency")
            direct_only = st.checkbox("الرحلات المباشرة فقط", value=False, key="fare_direct")
            filtered = filter_fares(matching, origin=request.origin, destination=request.destination, cabin_class=None if cabin == "الكل" else cabin, currency=currency_filter, direct_only=direct_only)
            if not filtered:
                st.warning("لا توجد عروض تطابق الفلاتر الحالية.")
            else:
                st.metric("أقل سعر مطابق", f"{filtered[0].price:,.2f} {filtered[0].currency}")
                rows = [{"شركة الطيران": x.airline, "المصدر": x.provider, "الدرجة": x.cabin_class, "السعر": x.price, "العملة": x.currency, "التوقفات": x.stops, "المدة (دقيقة)": x.duration_minutes, "الأمتعة": x.baggage_summary or "غير محدد", "آخر تحقق": x.checked_at, "حالة السعر": fare_age_label(x.checked_at), "رابط العرض": x.booking_url} for x in filtered]
                st.dataframe(rows, use_container_width=True, hide_index=True)
                st.caption("الترتيب من الأرخص إلى الأغلى. تحقق من السعر النهائي وشروط التذكرة لدى المصدر.")
    else:
        st.info("لا توجد أسعار فعلية محمّلة بعد. ارفع ملف CSV من مصدر مصرح به لبدء المقارنة.")

    for category, sources in sources_by_category().items():
        st.markdown(f"**{category}**")
        cols = st.columns(2)
        for index, source in enumerate(sources):
            with cols[index % 2]:
                st.link_button(f"{source.name} ↗", source.url, use_container_width=True)
                st.caption(source.note)

    st.info(
        "هذه الروابط للبحث اليدوي. لا يجمع التطبيق أسعار Wego أو Wingie آلياً لأن شروطهما تمنع ذلك، "
        "ولا يعرض أسعاراً غير متحقق منها. قد تحتاج إلى إدخال تفاصيل الرحلة مرة أخرى في بعض المواقع."
    )
else:
    st.markdown(
        """
        <div style="border:1px dashed rgba(128,128,128,.45);border-radius:16px;padding:1.6rem;text-align:center;background:rgba(128,128,128,.035);">
          <div style="font-size:2rem;">🌍</div>
          <h3>إلى أين تريد السفر؟</h3>
          <p>أدخل تفاصيل رحلتك، ثم ارفع عروض أسعار موثقة لمقارنتها وفرزها حسب الدرجة والسعر.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander("المصادر التي يغطيها التطبيق", expanded=False):
    st.write("شركات مصرية: مصر للطيران، إير كايرو، النيل للطيران، فلاي إيجيبت.")
    st.write("شركات سعودية: الخطوط السعودية، طيران ناس، طيران أديل، طيران الرياض.")
    st.write("مواقع مقارنة: Wego مصر، المسافر، Google Flights.")
    st.write("المطارات: مطارات مصر والسعودية، إضافة إلى وجهات دولية شائعة.")

st.markdown(
    '<div class="trust">🔎 الشفافية أولاً: لا نطلب حسابات أو مفاتيح API، ولا ننفذ حجزاً أو دفعاً. تحقق من السعر النهائي وشروط الأمتعة على الموقع الأصلي قبل اتخاذ قرارك.</div>',
    unsafe_allow_html=True,
)
st.divider()
st.caption("Flight Hunter AI · بحث ومقارنة خارجية · لا حجز ولا دفع داخل التطبيق")
