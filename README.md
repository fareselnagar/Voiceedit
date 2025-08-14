
# auto-audio-engineer-advanced

مشروع متقدم لهندسة صوتية تلقائية جاهز للنشر على GitHub.

## مميزات
- فصل مصادر (Vocal / Music) باستخدام Spleeter أو Demucs (اختياري).
- إزالة ضوضاء متقدمة باستخدام `noisereduce` + Demucs denoiser fallback.
- معيار LUFS ثابت باستخدام `pyloudnorm`.
- EQ تلقائي متعدد النطاقات، Compressor متقدم، Limiter نهائي.
- واجهة رفع ملف، معاينة قبل/بعد، وتحميل النتيجة.
- Dockerfile للحاوية.

## تشغيل محلي
1. ثبت ffmpeg في النظام.
2. أنشئ بيئة:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
> ملاحظة: بعض الحزم (torch, demucs, spleeter) كبيرة وتتطلب اتصال إنترنت سريع ومساحة تخزين.

3. شغّل:
```bash
python app.py
```
ثم افتح `http://localhost:5000`

## ملاحظات
- الحزمة تشتمل على مكونات اختيارية (Demucs) — إذا واجهت صعوبات في التثبيت، يمكنك تعطيلها في `audio_processor.py`.
- هذا المشروع مُعدّ للنشر على GitHub — قم بإضافة ملف `.gitignore` مع `venv/` و`uploads/` و`outputs/`.
