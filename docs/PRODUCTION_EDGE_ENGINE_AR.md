# تقرير Production Edge Engine v6

## حالة التسليم

تم تنفيذ النظام في:

- `pine/production_edge_engine_v6.pine`

الملف مكتوب بـ **Pine Script v6 فقط** ويبدأ بـ `//@version=6`.

> **ملاحظة تصميمية مهمة:** الملف معلن كـ `strategy()` وليس `indicator()` بالمعنى الضيق. السبب أن Pine لا يتيح لمؤشر `indicator()` الوصول إلى fills و`strategy.closedtrades` و`strategy.netprofit` و`strategy.max_drawdown`. لذلك صُمّم كـ **Strategy/Overlay Indicator**: يرسم المؤشر والإشارات والـ Dashboard، ويضيف في الوقت نفسه محرك اختبار حقيقي عبر TradingView Strategy Tester. هذا هو الشكل الصحيح عندما تكون إحصائيات الصفقات جزءًا من المطلوب.

## 1. الخلاصة التنفيذية

النظام ليس تنبؤًا بالسعر ولا يدّعي أن Signal Score هو احتمال نجاح. الفكرة القابلة للاختبار هي:

1. لا يتم التداول ضد اتجاه أعلى مؤكد.
2. لا يتم الدخول لمجرد عبور متوسط أو قراءة RSI.
3. يجب أن يتوافق الاتجاه، وبنية السوق، والزخم، وجودة الحركة، وحجم التداول عند توفره، والـ volatility، والمساحة إلى مستوى الإبطال/السيولة.
4. يتم رفض الصفقة إذا كان الـ stop واسعًا جدًا أو كانت المساحة إلى المقاومة/الدعم المقابل لا تعطي `minimumRoomRR`.
5. الخروج يتم من خلال ثلاث جولات ربح، ووقف هيكلي/ATR، ونقل إلى Break Even، وATR trailing، أو إشارة انعكاس مؤكدة.

هذه **فرضية Edge قابلة للاختبار** وليست إثباتًا إحصائيًا. لا توجد في المستودع بيانات OHLCV أو نتائج TradingView من رمز وزمن محدد، ولذلك لم يتم اختلاق Train/Validation/Holdout results.

## 2. ما الذي تم بحثه ولماذا تم اختياره

### Trend Following وTime-Series Momentum

تشير بيانات Moskowitz/Ooi/Pedersen المنشورة عبر AQR إلى أن time-series momentum دُرس عبر 58 أداة futures متنوعة، باستخدام عوائد سابقة لكل أصل بدل ترتيب الأصول فقط [3](https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data). كما أن الأدبيات تحذّر من فصل أثر momentum عن volatility scaling؛ دراسة Kim/Tse/Wald تذكر أن جزءًا كبيرًا من النتائج قد يرتبط بالـ scaling نفسه [4](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2786955).

التطبيق هنا ليس نسخًا لنتائج تلك الأوراق إلى العملات المشفرة. تم استخدام:

- اتجاه EMA سريع/بطيء على الإطار الحالي.
- ميل EMA.
- اتجاه أعلى زمني مؤكد.
- ADX لتصنيف قوة الاتجاه، وليس كمشغل دخول منفرد.

### Momentum

اُستخدم ROC مع حالة RSI وميل ROC. هذا يقلل تكرار MACD؛ فـ MACD المبني على المتوسطات سيعيد جزءًا كبيرًا من معلومة trend/ROC. RSI ليس شرطًا وحيدًا ولا يُستخدم للشراء لمجرد أنه أقل من 30 أو للبيع لمجرد أنه أعلى من 70.

### Mean Reversion

لم تُضمّن نسخة mean-reversion في محرك واحد بشكل مصطنع. mean reversion يحتاج نموذجًا منفصلًا للـ sideways regime، وتكاليف، ومدة احتفاظ، وتعريفًا مستقلًا للـ edge. خلطه مع trend-following بلا بيانات يرفع درجات الحرية ويزيد خطر overfitting. النظام الحالي يرفض Sideways افتراضيًا بدل أن يختلق edge.

### Price Action وBreakout/Pullback

تم اختيار شكلين موضوعيين وقابلين للبرمجة:

- كسر أعلى/أدنى قناة سابقة لا تشمل الشمعة الحالية.
- Pullback إلى EMA السريع مع إغلاق عكسي مؤكد وcandle directional ذات body fraction مقبول.
- Failed breakout: اختراق intrabar للمستوى ثم إغلاق عائد عند/داخل القناة؛ يُعاقب في score، ويمنع الدخول في اتجاه الاختراق، وقد يفعّل خروجًا من الصفقة المقابلة.

لم يتم استخدام أسماء مثل “شمعة سحرية” أو نماذج يدوية غير قابلة للتكرار.

### Market Structure وBOS/CHoCH

تُستخدم pivots مؤكدة فقط بعد مرور `pivotRight` شموع. يتم تسجيل HH/HL/LH/LL عند لحظة التأكد، ولا يتم رسم pivot تاريخيًا على الشمعة التي حدث فيها. كسر آخر swing high/low يسجل BOS، وإذا كان اتجاه الهيكل السابق معاكسًا يصنف الحدث CHoCH.

### Support/Resistance وLiquidity

بدل رسم مناطق ذاتية مثل supply/demand أو order block غير موحدة، يستخدم النظام:

- آخر swing high/low المؤكد.
- أعلى/أدنى نطاق سابق.
- المساحة إلى المقاومة/الدعم المقابل كـ `room-to-liquidity`.

لا توجد بيانات order book أو spread حقيقية داخل Pine؛ لذلك لا يدّعي النظام أنه يقيس liquidity الفعلية.

### Order Blocks وFair Value Gaps وFibonacci

تم عدم استخدامها افتراضيًا. ليس لأن كل تعريف لها عديم الفائدة، بل لأن تعريفاتها تختلف بشدة بين المتداولين، وتضيف درجات حرية كثيرة: حجم المنطقة، مدة صلاحيتها، التعامل مع mitigation، ومرجع FVG. لا تدخل في Production Edge Engine إلا بعد اختبار ablation مستقل يثبت أنها تضيف expectancy بعد التكاليف، لا مجرد تحسن بصري.

### Volume وVWAP

يستخدم النظام relative volume مقابل متوسطه، مع اتجاه الشمعة. عند عدم توفر volume يكون عامل الحجم neutral بدرجة 50 ولا يتم اختراع volume. VWAP يستخدم كسياق price-action وليس إشارة مستقلة.

### Volatility وATR

يُقاس ATR الحالي مقابل متوسط ATR:

```text
ATR ratio = ATR الحالي / SMA(ATR, atrBaselineLen)
```

ثم:

- High volatility: يمنع الدخول افتراضيًا.
- Low volatility: يمنع الدخول افتراضيًا.
- Normal volatility: يسمح بالتقييم الطبيعي.

يستخدم ATR أيضًا في stop buffer وtrailing، بينما يُستخدم آخر swing كمرجع إبطال هيكلي.

### Multi-Timeframe

تم اختيار HTF مؤكد فقط. توصي وثائق TradingView باستخدام expression مزاحًا بـ `[1]` مع `barmerge.lookahead_on` للحصول على آخر قيمة HTF مؤكدة دون تسريب [1](https://www.tradingview.com/pine-script-docs/faq/other-data-and-timeframes/). كما تشرح وثائق repainting أن `lookahead_on` من دون offset يسبب future leak تاريخيًا [2](https://www.tradingview.com/pine-script-docs/concepts/repainting/).

لم يستخدم النظام LTF تلقائيًا؛ لأن LTF يعيد قيمة intrabar واحدة فقط في `request.security()` وله قيود تختلف بين التاريخي والـ realtime. استخدام `request.security_lower_tf()` يحتاج تصميمًا آخر وتعريفًا دقيقًا للـ intrabar execution.

## 3. Architecture النهائية

```text
Confirmed HTF Data [1] + lookahead_on
                 │
                 ▼
        Market Regime Engine
                 │
                 ├── Trend Engine: EMA spread + slope + HTF alignment
                 ├── Structure Engine: confirmed pivots + HH/HL/LH/LL + BOS/CHoCH
                 ├── Momentum Engine: ROC + RSI state + ROC slope
                 ├── Volume Engine: relative volume + candle direction
                 ├── Volatility Engine: ATR ratio + ADX regime context
                 ├── Price Action: breakout / pullback / VWAP / candle body
                 └── Risk/Reward Engine: invalidation distance + room to liquidity
                 │
                 ▼
        Directional score 0..100
                 │
                 ▼
       Quality gates + cooldown + sample window
                 │
          ┌──────┴──────┐
          ▼             ▼
        LONG          SHORT
          │             │
          └──────┬──────┘
                 ▼
  Entry + structure/ATR SL + TP1/TP2/TP3 + BE + trailing + exit
                 │
                 ▼
 Dashboard + dynamic alerts + Strategy Tester statistics
```

## 4. Market Regime Engine

يظهر الـ Dashboard صيغة مثل `NORMAL VOLATILITY / STRONG BULL`.

| الحالة | تعريف الاتجاه | سلوك النظام الافتراضي |
|---|---|---|
| Strong Bull | HTF bullish، EMA chart aligned، ADX HTF فوق العتبة، وميل محلي صاعد | يسمح بالـ LONG |
| Weak Bull | HTF bullish وEMA المحلي aligned، لكن القوة أقل | يسمح افتراضيًا إذا كان `allowWeakTrend` مفعّلًا |
| Sideways | لا يوجد توافق Bull أو Bear | لا توجد إشارات؛ لا يوجد mean-reversion غير مُثبت |
| Weak Bear | HTF bearish وEMA المحلي aligned | يسمح بالـ SHORT |
| Strong Bear | HTF bearish، alignment، ADX قوي، وميل محلي هابط | يسمح بالـ SHORT |
| High Volatility | ATR ratio فوق `highVolRatio` | منع افتراضي؛ يمكن تفعيله يدويًا بعد اختبار مستقل |
| Low Volatility | ATR ratio تحت `lowVolRatio` | منع افتراضي؛ يمكن تفعيله بعد قياس أثره |

High/Low volatility يسبق الوصف الاتجاهي في النص، مثل `HIGH VOLATILITY / WEAK BULL`.

## 5. Market Structure Engine

- `ta.pivothigh()` و`ta.pivotlow()` لا يغيّران القرار قبل اكتمال `pivotRight`.
- عند وصول pivot المؤكد:
  - high أعلى من السابق = HH.
  - high أقل من السابق = LH.
  - low أعلى من السابق = HL.
  - low أقل من السابق = LL.
- BOS صاعد = إغلاق حالي فوق آخر swing high المؤكد.
- BOS هابط = إغلاق حالي تحت آخر swing low المؤكد.
- CHoCH = BOS عكس `structureDirection` السابق.
- يتم الاحتفاظ بحالة الهيكل، لكن لا يتم نقل marker إلى الماضي.

## 6. شروط LONG

تظهر LONG فقط إذا تحققت جميع البوابات التالية على bar مؤكدة:

1. البيانات الأساسية جاهزة.
2. bar داخل sample المختار.
3. لا توجد صفقة مفتوحة.
4. انتهى cooldown.
5. HTF/local alignment صاعد، والقوة مقبولة حسب إعداد `allowWeakTrend`.
6. volatility مقبولة حسب إعدادات regime.
7. أحد setup التالي:
   - breakout فوق القناة السابقة، أو
   - pullback مؤكد إلى EMA السريع.
8. `longScore >= minimumScore`.
9. `roomRRLong >= minimumRoomRR`.
10. مسافة الوقف موجبة ولا تتجاوز `maximumStopAtr`.

## 7. شروط SHORT

العكس الاتجاهي لشروط LONG:

1. HTF/local alignment هابط.
2. volatility مسموحة.
3. breakout تحت القناة السابقة أو pullback مؤكد إلى EMA السريع.
4. `shortScore >= minimumScore`.
5. `roomRRShort >= minimumRoomRR`.
6. وقف موجب ولا يتجاوز الحد الأقصى من ATR.

## 8. Signal Scoring

الأوزان الافتراضية، وهي **prior تصميمي وليست نتيجة optimization**:

| العامل | الوزن |
|---|---:|
| Trend | 20 |
| Structure | 20 |
| Momentum | 15 |
| Volume | 10 |
| Volatility | 10 |
| Price Action / Liquidity | 15 |
| Risk/Reward room | 10 |
| **المجموع** | **100** |

كل عامل يُحوّل إلى 0–100، ثم يحسب الكود المتوسط الوزني. مجموع الأوزان يُطبّع تلقائيًا إذا غيّر المستخدم الأوزان.

التصنيف التشغيلي:

- 0–49: NO TRADE.
- 50–64: WEAK.
- 65–74: MODERATE.
- 75–84: STRONG.
- 85–100: HIGH QUALITY.

`minimumScore` الافتراضي 70، وHigh Quality alert الافتراضي 85. هذه الدرجات ليست probability ولا confidence calibrated؛ الـ Dashboard يضع نجمة على `CONFIDENCE*` ويوضح أنه ليس احتمالًا.

### لماذا لا أصف العوامل بأنها مستقلة رياضيًا؟

EMA وROC وRSI وADX ليست مستقلة إحصائيًا؛ معظمها مشتق من السعر. لذلك صُمّم score كـ **ensemble transparency tool** لا كدليل استقلال. في الاختبار يجب عمل ablation:

- كل عامل وحده.
- إزالة عامل واحد كل مرة.
- تغيير الأوزان ضمن نطاق صغير.
- مقارنة expectancy وdrawdown لا win rate فقط.

## 9. Risk Engine

### Entry

الـ signal close هو السعر المرجعي المعروض. `process_orders_on_close=true` يجعل استراتيجية TradingView تحاول تنفيذ الأمر على إغلاق شمعة الإشارة. التنفيذ الحقيقي قد يختلف بسبب latency وslippage.

### Stop Loss

للـ LONG:

```text
base stop      = entry - ATR × stopAtrMultiple
structure stop = last confirmed swing low - ATR × buffer
SL             = الأقل بينهما
```

للـ SHORT يتم استخدام mirror logic فوق swing high.

يتم رفض الصفقة إذا تجاوزت المسافة `maximumStopAtr`.

### Take Profits

```text
TP1 = entry ± risk × tp1R
TP2 = entry ± risk × tp2R
TP3 = entry ± risk × tp3R
```

النسب الافتراضية 33% / 33% / 34%، بحيث لا يكون النظام معتمدًا على صفقة خروج واحدة.

### Break Even وTrailing

بعد لمس TP1:

- ينقل الوقف إلى entry عند تفعيل `moveStopToBreakeven`.
- يحدّث ATR trail عند تفعيل `useAtrTrail`.
- للـ LONG يأخذ الوقف الأكبر، وللـ SHORT الأصغر، فلا يتم توسيع المخاطرة بعد تحريك الوقف.

### Exit Logic

الصفقة تغلق عند واحد من الآتي:

- stop order.
- TP1/TP2/TP3.
- BOS مؤكد عكسي.
- HTF/local reversal.
- opposite score يحقق حد الخروج.
- نهاية sample المختار، حتى لا يختلط train أو validation أو holdout.

## 10. MTF وAnti-Repainting

- جميع قيم HTF في `request.security()` تستخدم `[1]` داخل expression.
- جميع طلبات HTF تستخدم `barmerge.lookahead_on` مع offset، وليس `lookahead_on` عاريًا.
- لا يوجد `request.security()` لـ LTF.
- `calc_on_every_tick=false`.
- الإشارات محكومة بـ `barstate.isconfirmed`.
- لا يوجد `bar_index` offset لرسم الإشارة في الماضي.
- pivots لا تُرسم على pivot bar؛ marker يظهر عند bar التأكيد.
- لا توجد `timenow` أو random أو بيانات مستقبلية.

هذا يمنع future leak، لكنه لا يلغي gap/slippage أو غموض ترتيب أحداث high/low داخل شمعة واحدة.

## 11. Alerts

القناة الفعالة في هذا الملف هي `alert()` الديناميكية، لأن TradingView لا يفعل `alertcondition()` كـ trigger مستقل داخل strategy scripts [7](https://www.tradingview.com/pine-script-docs/faq/alerts/).

تمت إضافة أحداث:

- LONG
- SHORT
- EXIT
- TP1
- TP2
- TP3
- STOP LOSS
- BREAK EVEN
- HIGH QUALITY SIGNAL

الرسالة الديناميكية تحتوي على:

```text
Event | Symbol | TF | Direction | Entry | SL | TP1 | TP2 | TP3 | Score | RR
```

في TradingView أنشئ Alert واختر شرط strategy ثم اختر `Order fills and alert() function calls` أو `alert() function calls only` حسب الاستخدام.

## 12. Backtesting وWalk-Forward

### تقسيم العينات

يحتوي الكود على `sampleMode`:

- `ALL`
- `TRAIN`
- `VALIDATION`
- `HOLDOUT`

وكل واحد له تاريخ مستقل. التقسيم الافتراضي في الملف:

- TRAIN: 2018–2021.
- VALIDATION: 2022–2023.
- HOLDOUT: 2024–2035.

هذه تواريخ افتراضية وليست مناسبة تلقائيًا لكل أصل. يجب تغييرها حسب عمر الرمز وجودة البيانات.

### البروتوكول الصحيح

1. **TRAIN:** اختبر الفرضية وعددًا محدودًا من الإعدادات. لا تحاول تعظيم win rate.
2. **VALIDATION:** ثبّت الفكرة ثم قيّم تغييرًا صغيرًا في البيئة. لا تعيد اختيار كل parameter بناءً على هذه الفترة.
3. **HOLDOUT:** شغّله مرة واحدة بعد تجميد الكود والأوزان. لا تستخدمه للتحسين.
4. **Forward/Paper:** اترك النظام يعمل خارج العينة قبل رأس مال حقيقي.
5. سجّل عدد التجارب التي جُرّبت؛ لأن كثرة التجارب ترفع احتمال اختيار backtest رابح بالصدفة. هذا هو موضوع Probability of Backtest Overfitting [5](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2731886).

### المقاييس المطلوبة

من Strategy Tester أو تصدير الصفقات احسب:

- Win Rate = wins / closed trades.
- Profit Factor = gross profit / absolute gross loss.
- Expectancy = average net P/L per closed trade.
- Net Profit.
- Max Drawdown وMax Drawdown %.
- Sharpe على سلسلة returns بعد التكاليف.
- Sortino باستخدام downside deviation.
- Recovery Factor = Net Profit / absolute Max Drawdown.
- Average Win / Average Loss.
- Consecutive Losses.
- Number of Trades.

الـ Dashboard داخل Pine يعرض Trades، Wins/Losses، Win Rate، Profit Factor، Expectancy، Net P&L، Max Drawdown، Average Trade. أما Sharpe وSortino وRecovery Factor وconsecutive losses فتحتاج تصدير equity/trades أو تقرير Strategy Tester مفصل؛ لم يتم اختلاقها داخل الكود.

### التكاليف

الاستراتيجية تضبط commission افتراضيًا على `0.05%` لكل تنفيذ في declaration. يجب ضبطه لرمزك. Slippage لا يمكن جعله input ديناميكيًا في declaration؛ اضبطه من Properties، واختبر سيناريوهات متعددة. في الأصول غير السائلة، يجب إدخال spread/impact محافظ يدويًا.

## 13. نتائج الاختبارات المتاحة

| المرحلة | النتيجة |
|---|---|
| TRAIN | **غير متاح بعد**: لا توجد OHLCV مرفقة أو رمز/زمن محدد في المستودع |
| VALIDATION | **غير متاح بعد** |
| HOLDOUT | **غير متاح بعد** ولم يُستخدم للتحسين |
| Bull/Bear/Sideways/High Vol/Low Vol | تحتاج تشغيلًا على بيانات الرمز؛ لا توجد بيانات محلية |
| Multi-asset / Multi-timeframe | تحتاج تشغيلًا منفصلًا؛ لا يجوز تعميم نتيجة رمز واحد |
| Pine compile | تمت مراجعة static مرتين؛ يلزم لصق الملف في محرر TradingView للتأكيد النهائي لأن Pine compiler ليس جزءًا من هذا المستودع |

عدم وضع أرقام هنا مقصود. أي رقم Win Rate أو Profit Factor من دون dataset، commission، slippage، timeframe، وsample محدد سيكون مضللًا.

## 14. Robustness وOverfitting analysis

الاختبار المقترح لكل رمز/زمن:

| محور الحساسية | نطاق التجربة |
|---|---|
| EMA fast/slow | ±10% و±20% مع الحفاظ على fast < slow |
| breakoutLen | 15 / 20 / 25 / 30 |
| pivotRight | 2 / 3 / 4 / 5 |
| ATR stop | 1.25 / 1.5 / 1.75 / 2.0 |
| minimumScore | 65 / 70 / 75 / 80 |
| minimumRoomRR | 1.25 / 1.5 / 1.75 / 2.0 |
| costs | baseline، ضعف commission، وslippage محافظ |

لا يعتبر النظام robust إذا:

- يربح فقط بقيمة parameter واحدة.
- ينهار عند زيادة commission أو slippage قليلًا.
- يعتمد على عدد قليل جدًا من trades.
- تتحسن النتيجة في TRAIN فقط وتنهار في VALIDATION/HOLDOUT.
- يملك win rate عاليًا لكن expectancy سلبيًا أو drawdown غير مقبول.

## 15. مراجعة الكود المستقلة

### المراجعة الأولى: Pine correctness

تم فحص:

- وجود `//@version=6` وعدم وجود v4/v5 declaration.
- وجود declaration واحد `strategy()`.
- استخدام `request.security()` مع HTF offset.
- أنواع inputs، tuples، functions، arrays/loops: لا توجد arrays أو loops غير لازمة.
- table dimensions ومراجع الصفوف.
- partial exits عبر `strategy.exit()` بنسب مجموعها 100%.
- guard على القيم `na` في score وATR وvolume.
- عدم وجود TODO أو PLACEHOLDER أو كود ناقص.

التحقق النهائي يجب أن يتم داخل Pine Editor؛ لا يوجد compiler TradingView ضمن المستودع.

### المراجعة الثانية: Trading logic

تم فحص:

- عدم استخدام pivot قبل confirmation.
- عدم رسم signal تاريخيًا بoffset.
- منع التداول في Sideways/High Vol/Low Vol افتراضيًا.
- رفض stop غير الموجب أو الأوسع من maximumStopAtr.
- عدم دخول صفقة ثانية أثناء position.
- تحديث trailing في اتجاه واحد فقط.
- إغلاق position عند نهاية sample.
- عدم تقديم confidence كاحتمال.
- إبقاء TP/SL levels من entry ثابتة ما لم يتغير stop بعد TP1 إلى BE/trailing.

### حالة الشمعة التي تضرب SL وTP معًا

OHLC وحده لا يثبت ترتيب intrabar. TradingView broker emulator يطبّق قواعده، وقد تختلف النتيجة عن tick data. لذلك يجب استخدام Bar Magnifier أو بيانات أدق عند توفرها، ثم اختبار سيناريو محافظ يفترض stop أولًا. هذا قيد في البيانات وليس مشكلة يمكن إخفاؤها بكود indicator.

## 16. القيود والمخاطر

1. score ليس probability ولا يثبت وجود edge.
2. HTF المؤكد يأتي متأخرًا عمدًا؛ عدم repainting له ثمن في latency.
3. volume قد يكون غير موثوق في بعض الرموز أو غير متاح.
4. لا توجد order-book liquidity أو bid/ask spread حقيقية في Pine.
5. process-on-close لا يضمن fill حقيقيًا على نفس السعر.
6. commission الافتراضي يجب تغييره، وslippage يجب ضبطه من Properties.
7. الأصول ذات gaps أو أخبار أو liquidity ضعيفة قد تتجاوز stop.
8. pivots objective لكنها lagging بطبيعتها.
9. trend-following قد يخسر في chop، والنظام يفضّل تفويت الفرص على كثرة إشارات غير جيدة.
10. لا يوجد position sizing مبني على portfolio-level volatility أو correlation؛ `default_qty_value` في هذا الإصدار هو 10% من equity ويجب تغييره بما يناسب حسابك.
11. لا يوجد ML مدّعى داخل Pine. إدخال نموذج ML بلا dataset وwalk-forward وتكاليف سيكون marketing لا research.

## 17. طريقة الاستخدام

1. افتح TradingView واختر رمزًا ذا بيانات volume مناسبة.
2. افتح Pine Editor والصق `pine/production_edge_engine_v6.pine`.
3. Compile ثم أضف إلى chart.
4. استخدم chart timeframe أقل من HTF، مثل 15m مع 4H أو 1H مع 1D.
5. اضبط commission/slippage في Properties.
6. شغّل `TRAIN` أولًا، وسجّل المقاييس.
7. جمّد parameters ثم شغّل `VALIDATION`.
8. بعد تجميد الكود شغّل `HOLDOUT` مرة واحدة.
9. راقب Strategy Tester، لا win rate فقط.
10. أنشئ alert من `alert()` calls، وابدأ Paper Trading قبل التنفيذ الحقيقي.

## 18. إعدادات بداية محافظة

ليست توصية استثمارية، وإنما baseline قابل للاختبار:

- Chart: 15m–1H.
- HTF: 4H–1D.
- `minimumScore = 70`.
- `highQualityScore = 85`.
- `allowHighVolatility = false`.
- `allowLowVolatility = false`.
- `allowWeakTrend = true` في TRAIN فقط، ثم قارن مع Strong-only.
- `stopAtrMultiple = 1.5`.
- `maximumStopAtr = 4.0`.
- `minimumRoomRR = 1.5`.
- `tp1/tp2/tp3 = 1R/2R/3R`.
- commission وslippage حسب السوق، وليس حسب الإعدادات الافتراضية بشكل أعمى.

## 19. الحكم النهائي

تم بناء محرك متعدد الطبقات قابل للفحص، مع HTF non-repainting، structure confirmation، score، risk engine، alerts، وwalk-forward controls. لكن **لم يثبت بعد positive expectancy على holdout** لأن بيانات الاختبار غير موجودة. لذلك التسليم الصادق هو: كود Production-oriented وفكرة Edge قابلة للدحض، وليس وعدًا بأداء أو Win Rate.

أي قرار بترقية النظام إلى live يجب أن يأتي بعد سجل مستقل يثبت:

- expectancy موجب بعد التكاليف.
- PF معقول.
- drawdown مقبول.
- نتائج متماسكة في TRAIN/VALIDATION/HOLDOUT.
- حساسية parameter مستقرة.
- paper forward test.
