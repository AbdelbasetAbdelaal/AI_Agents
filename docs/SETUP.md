# إعداد وتشغيل Flight Hunter AI

## المتطلبات
- Python 3.11 أو أحدث.

## التثبيت على Windows
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

افتح العنوان المحلي الذي يطبعه Streamlit في الطرفية.

## الاختبارات
```powershell
pytest -q
```

## هل أحتاج مفاتيح أو حسابات؟
لا. لا يحتاج التطبيق إلى حسابات مطورين أو مفاتيح API أو ملف أسرار. ملف `.env.example` اختياري ويحتوي فقط على إعدادات عامة.

## حدود البحث
تعرض النسخة الحالية روابط بحث خارجية للمواقع المصرية والسعودية ومواقع المقارنة. لا تسحب أسعاراً حية من المواقع التي لا تسمح بالوصول العام المصرح به، ولا تنفذ الحجز أو الدفع. السعر النهائي والتوافر يتم التحقق منهما على الموقع الأصلي.


## تشغيل متصفح سطح المكتب الاختياري

يتطلب هذا الوضع تثبيت PySide6 وQt WebEngine بالإضافة إلى متطلبات المشروع:

```powershell
pip install -r requirements-desktop.txt
python run_desktop.py
```

يمكن الاستمرار في استخدام Streamlit دون تثبيت Qt:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

المتصفح يتيح التصفح اليدوي داخل نافذة مستقلة، ولا ينفذ scraping أو جمع أسعار آلياً. إذا رفض موقعٌ ما العمل داخل Qt WebEngine، افتحه يدوياً في Chrome أو Edge.
