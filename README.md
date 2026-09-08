# Production Edge Engine v6

هذا المستودع يحتوي على محرك تداول متعدد الطبقات مكتوب بـ **Pine Script v6 فقط**.

## الملفات

- `pine/production_edge_engine_v6.pine` — الكود الكامل. هو Strategy/Overlay Indicator لكي يعرض Dashboard ويصل إلى Strategy Tester statistics.
- `docs/PRODUCTION_EDGE_ENGINE_AR.md` — التقرير العربي: البحث، التصميم، شروط الدخول والخروج، anti-repainting، منهجية walk-forward، القيود، وعدم اختلاق النتائج.

## ملاحظات مهمة

- جميع بيانات HTF مؤكدة باستخدام `[1]` مع `barmerge.lookahead_on`.
- الإشارات لا تظهر إلا على bar مؤكدة، ولا تُرسم تاريخيًا على pivot bar.
- لا توجد نتائج TRAIN/VALIDATION/HOLDOUT في المستودع لعدم وجود OHLCV أو رمز/زمن محدد؛ شغّلها على TradingView ولا تستخدم HOLDOUT للتحسين.
- عدّل commission وslippage من Properties لكل سوق قبل تقييم الأداء.
