# تثبيت ماكرو COLOR_SWAP — على أي طابعة Klipper

الإصدار 5 — 2026-11-06 — لطابعة FLSUN V400 (Klipper v0.13، Mainsail v2.19، KlipperScreen، OrcaSlicer 2.4.2)

## محتويات الملف المضغوط

| الملف | ماذا تفعل به |
|---|---|
| `color_swap.cfg` | **الماكرو نفسه** — يُرفع لكل طابعة |
| `FLSUN_V400/macros.cfg` و`FLSUN_V400/KlipperScreen.conf` | ملفات جاهزة لطابعة FLSUN V400 فقط (فيها أسطر الربط وزرّا Color swap وResume saved) |
| `orca_change_filament_gcode.txt` | سطر OrcaSlicer لتبديل اللون |
| `moonraker_notifier.txt` | 🆕 قسم رسائل الهاتف (Telegram) يُلصق في آخر `moonraker.conf` |
| `orca_before_layer_change_gcode.txt` | 🆕 سطر OrcaSlicer لنقاط الحفظ (استكمال بعد انقطاع الكهرباء) |
| `README.md` | طريقة الاستعمال خطوة بخطوة |
| `test/` | نموذج تجربة: لوح + حرف T |
| `ROLLBACK_v4/` | 🆕 ملفات الطابعة قبل الإصدار 5 (للرجوع) |
| `SHA256SUMS.txt` | بصمة كل ملف — للتأكد أن الملف سليم بعد الرفع |

ملفات `ROLLBACK_v4/` منسوخة من الطابعة نفسها (الإصدار 4 العامل). ملفات الإصدار 5 مطابقة لما رُفع إلى الطابعة يوم 2026-11-06.

---

## الحالة 1 — طابعة FLSUN V400 (10 دقائق)

1. افتح **Mainsail** ← **Machine** (ملفات الإعدادات).
2. خذ نسخة احتياطية: نزّل `macros.cfg` و`printer.cfg` إلى جهازك.
3. ارفع `color_swap.cfg`.
4. ارفع `FLSUN_V400/macros.cfg` مكان `macros.cfg` الموجود.
   > إن كان `macros.cfg` في طابعتك مختلفًا (عدّلته بنفسك)، لا ترفعه — اتبع الخطوتين 3 و4 من الحالة 2 بدلًا من ذلك.
5. افتح `printer.cfg` وأضف هذا السطر **تحت** `[include macros.cfg]` مباشرة:
   ```
   [include color_swap.cfg]
   ```
6. ارفع `KlipperScreen.conf` مكان الموجود (يضيف زر **Color swap** في قائمة الطباعة)، ثم أعد تشغيل KlipperScreen.
7. 🆕 افتح `moonraker.conf` والصق محتوى `moonraker_notifier.txt` في **آخره** (لا تستبدل الملف كاملًا).
   ثم بدّل `BOT_TOKEN` و`CHAT_ID` (الخطوات في `README.md`، الجزء 4).
8. تأكد أن الطابعة **لا تطبع**، ثم اضغط **Save & Restart**.
9. **التجربة:** اكتب في الـ Console:
   ```
   COLOR_SWAP
   ```
   الرد الصحيح: `COLOR_SWAP only works during a print.` ← التثبيت ناجح، ولم يتحرك شيء.

---

## الحالة 2 — طابعة Klipper أخرى (20 دقيقة)

### قبل البدء: تأكد أن `printer.cfg` فيه هذه الأقسام

```
[pause_resume]
[respond]
[exclude_object]
[gcode_arcs]
```

أي قسم غير موجود ← أضفه كما هو (سطر واحد لكل قسم).

### الخطوات

1. ارفع `color_swap.cfg` وأضف `[include color_swap.cfg]` إلى `printer.cfg`.
2. **ماكرو `RESUME`:** أضف هذا السطر **أول سطر** داخل `gcode:`:
   ```
   _COLOR_SWAP_ON_RESUME
   ```
3. **ماكرو `CANCEL_PRINT`:** أضف هذا السطر **قبل** `CANCEL_PRINT_BASE`:
   ```
   _COLOR_SWAP_RESET
   ```
   **ماكرو البداية (`START_PRINT` أو `PRINT_START`):** أضف في أوله:
   ```
   _CS_CLEAR_CHECKPOINT
   ```
   **ماكرو النهاية (`END_PRINT` أو `PRINT_END`):** أضف في آخره (يوقف الحفظ التلقائي بعد انتهاء الطباعة):
   ```
   _CS_CLEAR_CHECKPOINT DONE=1
   ```
   > إن كان ماكرو البداية عندك ينتهي بسحب خيط (`G1 E-…`) بعد خط التنظيف: احذفه.
   > Orca يسحب ويرجع ما سحبه هو فقط، فيبدأ الـ skirt ناقصًا ومتقطعًا.
   > الاستكمال بعد التوقف (`RESUME_SAVED_PRINT`) يحتاج `[save_variables]` في `printer.cfg`،
   > ويعمل على طابعات **الدلتا فقط** (الـ Home فيها يصعد للأعلى). في الطابعات الأخرى الـ Home ينزل على القطعة، فالماكرو يرفض.
   مثال:
   ```
   [gcode_macro RESUME]
   rename_existing: RESUME_BASE
   gcode:
     _COLOR_SWAP_ON_RESUME
     ...باقي الماكرو كما هو...
   ```
   > مُستحسن: إن كان `RESUME` عندك يدفع الخيط (`G1 E…`) قبل `RESUME_BASE`، تخطَّ هذا الدفع بعد التبديل
   > وأضف `VELOCITY=250` إلى `RESUME_BASE` — انظر `RESUME` في `FLSUN_V400/macros.cfg` كمثال.
   > إن كان `RESUME` و`CANCEL_PRINT` من ملف `mainsail.cfg` أو `fluidd.cfg` (لا يُعدَّل)،
   > انسخ الماكرو إلى ملف ماكروهاتك أولًا، ثم أضف السطر.
4. افتح `color_swap.cfg` وعدّل قسم `[gcode_macro _COLOR_SWAP_CFG]`:

   | المتغير | ماذا تضع |
   |---|---|
   | `park_x / park_y` | نقطة الصخ: فوق حافة السرير، بعيدًا عن القطعة |
   | `sensor` | اسم حساس الخيط في `printer.cfg` (إن لم يوجد حساس فلا مشكلة) |

   **مثال سرير مربع 235×235 مم** (إحداثيات من 0 إلى 235):
   ```
   variable_park_x: 117.5
   variable_park_y: 10
   ```
5. **Save & Restart**، ثم التجربة كما في الخطوة 9 من الحالة 1.

> الماكرو يستدعي `PAUSE` الموجود في طابعتك لرفع الرأس وإبعاده.
> تأكد أن `PAUSE` عندك يرفع الرأس فعلًا قبل أول طبعة.

---

## إعداد OrcaSlicer (مرة لكل بروفايل طابعة)

1. **Printer settings** ← ابحث عن **Manual filament change** ← ✔.
2. **Printer settings** ← ابحث عن **Change filament G-code** ← الصق محتوى `orca_change_filament_gcode.txt`:
   ```
   {if layer_num >= 0}COLOR_SWAP SLOT={next_extruder + 1} MATERIAL={filament_type[next_extruder]} OLD_MATERIAL={filament_type[previous_extruder]} TEMP={new_filament_temp} OLD_TEMP={old_filament_temp} RETRACT={new_retract_length_toolchange} PURGE={flush_length}{endif}
   ```
3. **Process** ← ابحث عن **Prime tower** ← أطفئ **Enable**.
4. **حرارة السرير**: ابحث عن `bed temperature` واختر **By First filament**.
5. 🆕 **Printer settings** ← **Machine G-code** ← **Before layer change G-code** ← أضف في آخره (اترك الموجود):
   ```
   _CS_CHECKPOINT LAYER={layer_num + 1} TOTAL={total_layer_count} SLOT={current_extruder + 1} MATERIAL={filament_type[current_extruder]}
   ```
   > خطأ عند التقطيع؟ احذف `SLOT=…` و`MATERIAL=…` واترك الباقي.
6. احفظ البروفايلين.

---

## الرجوع للإصدار 4 (FLSUN V400)

1. ارفع الملفين من `ROLLBACK_v4/` مكان الموجودين: `color_swap.cfg` و`macros.cfg`.
2. تأكد أن الطابعة **لا تطبع**، ثم اضغط **Save & Restart**.
3. Orca لا يحتاج تغييرًا.

---

## إزالة الماكرو (الرجوع للوضع السابق)

1. احذف السطر `[include color_swap.cfg]` من `printer.cfg`.
2. احذف الأسطر `_COLOR_SWAP_ON_RESUME` و`_COLOR_SWAP_RESET` و`_CS_CLEAR_CHECKPOINT`، وسطر `_CS_CHECKPOINT` من Orca.
3. **Save & Restart**.
