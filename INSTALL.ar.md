**العربية** | [English](INSTALL.md)

# تثبيت ماكرو COLOR_SWAP — على أي طابعة Klipper

الإصدار 6.5 — 2026-11-21 — كُتب على طابعة FLSUN V400 (Klipper v0.13، Mainsail v2.19، KlipperScreen، OrcaSlicer 2.4.2).
طابعات الدلتا والكارتيزي و CoreXY والسرير المتحرك تستعمل نفس الملف `color_swap.cfg`.

> **حالة الإصدار 6.5:** مثبّت على FLSUN V400 يوم 2026-11-21 (Klipper جاهز بلا تحذيرات)، وشُغّل في محاكي (402 فحصًا على دلتا وكارتيزي و CoreXY). لوحة Telegram 1.8: ‏114 فحصًا. طُبعت تبديلات ألوان حقيقية بالإصدار 6.4.
> **الجديد في 6.5 لم يُشاهَد بعد في طباعة حقيقية:** التبديل الذي يغيّر نوع الخامة ينتظرك حتى في AWAY، واللوحة تنبّه قبل كل تبديل بـ 10 دقائق. راقب أول طباعة فيها تغيير خامة.
> ملفات هذه الحزمة مطابقة حرفيًا لما على الطابعة.

## المحتويات

| الملف | ماذا تفعل به |
|---|---|
| `color_swap.cfg` | **الماكرو نفسه** — يُرفع لكل طابعة |
| `FLSUN_V400/macros.cfg` و`FLSUN_V400/KlipperScreen.conf` | ملفات جاهزة لطابعة FLSUN V400 فقط |
| 🆕 `KlipperScreen_color_swap.conf` | أزرار KlipperScreen الأربعة، تُلصق في `KlipperScreen.conf` عندك (للطابعات الأخرى) |
| `orca_change_filament_gcode.txt` | سطر OrcaSlicer لتبديل اللون |
| `orca_before_layer_change_gcode.txt` | سطر OrcaSlicer لنقاط الحفظ (اختياري) |
| `moonraker_notifier.txt` | رسائل الهاتف (Telegram)، يُلصق في آخر `moonraker.conf` |
| 🆕 `telegram_bot.txt` | التحكم عن بعد من Telegram: خطوات التثبيت و`telegram.conf` وقائمة الأوامر |
| `README.ar.md` / `README.md` | طريقة الاستعمال خطوة بخطوة (عربي / إنجليزي) |
| `INSTALL.ar.md` / `INSTALL.md` | هذا الملف (عربي / إنجليزي) |
| `test/` | نموذج تجربة: لوح + حرف T |
| `telegram_panel/` | لوحة التحكم في Telegram (ملف Python واحد + `install.sh`)، انظر الجزء 6 في README |
| `klipperscreen_popup_fix.sh` | إصلاح اختياري في KlipperScreen: الرسائل المنبثقة لا تحجز اللمس |
| `sim/` | اختبارات: `python sim/run_tests.py` (يحتاج `pip install jinja2`) |
| `screenshots/` | صور النوافذ |
| `ROLLBACK_v6.4/` | 🆕 ملفات الإصدار 6.4 / اللوحة 1.5 (للرجوع) |
| `SHA256SUMS.txt` | بصمة كل ملف |

---

## الحالة 1 — طابعة FLSUN V400 (10 دقائق)

1. افتح **Mainsail** ← **Machine** (ملفات الإعدادات).
2. خذ نسخة احتياطية: نزّل `color_swap.cfg` و`macros.cfg` و`KlipperScreen.conf` و`printer.cfg` إلى جهازك.
3. ارفع `color_swap.cfg` مكان الموجود.
4. ارفع `FLSUN_V400/macros.cfg` مكان `macros.cfg` الموجود.
   > الملفان يجب أن يتغيّرا **معًا**: الإصدار 6 يتوقع أن `RESUME` يدفع 1 مم (الإصدار 5 كان يتخطاه).
   > إن كان `macros.cfg` عندك معدّلًا بيدك، انظر «التحديث من الإصدار 5» في الأسفل.
5. يجب أن يكون في `printer.cfg` السطر `[include color_swap.cfg]` **تحت** `[include macros.cfg]` مباشرة (موجود إن كان الإصدار 5 مثبتًا).
6. ارفع `FLSUN_V400/KlipperScreen.conf` مكان الموجود (يضيف زر **Color swap settings**)، ثم أعد تشغيل KlipperScreen.
7. رسائل الهاتف: `moonraker_notifier.txt` كما هو (لا تغيير إن كانت الرسائل تصل في الإصدار 5.1).
8. تأكد أن الطابعة **لا تطبع**، ثم اضغط **Save & Restart**.
9. **التجربة** — اكتب في الـ Console:
   ```
   COLOR_SWAP_CHECK
   ```
   يعرض حدود الطابعة، ونقطة الصخ، والحساس والمحركات التي وجدها، وأي شيء ناقص. لا يتحرك شيء.
   ثم `COLOR_SWAP` يجب أن يرد: `COLOR_SWAP only works during a print.`

### التحديث من الإصدار 5 وعندك macros.cfg خاص بك

تغيّر مكانان فقط في `macros.cfg`:

- **`RESUME`**: احذف هذه الأسطر الثلاثة (التبديل الآن يسحب 1 مم زيادة بدلها، فيجب أن يبقى الدفع):
  ```
  {% if swap %}
  {% set e = 0 %}
  {% endif %}
  ```
- **`M600`** (اختياري، لنافذة نفاد الخيط): انظر `M600` في `FLSUN_V400/macros.cfg` — الجزء الذي يبدأ بـ `COLOR_SWAP RUNOUT=1`.

---

## الحالة 2 — طابعة Klipper أخرى (15 دقيقة)

### 1. أقسام في `printer.cfg`

```
[pause_resume]
[respond]
[virtual_sdcard]      (موجود في كل تثبيت Mainsail / Fluidd)
[save_variables]
filename: ~/printer_data/config/variables.cfg
[exclude_object]      (لخط التنظيف في الطبقة الأولى)
[gcode_arcs]          (للدلتا فقط، لخط التنظيف في الطبقة الأولى)
```

أضف ما ليس عندك.

### 2. الرفع والتضمين

ارفع `color_swap.cfg` وأضف `[include color_swap.cfg]` إلى `printer.cfg`، **بعد** تضمين ملف ماكروهاتك (أو `mainsail.cfg`).

### 3. لا شيء تعدّله في الملف

الإصدار 6 يتعرّف على الطابعة وحده:

| ماذا | كيف |
|---|---|
| نقطة الصخ | منتصف السرير في X (الدلتا: 0)، و`park_edge` (12 مم) داخل حد Y الأمامي |
| خط تنظيف الطبقة الأولى | الدلتا: قوس داخل الحد الأمامي الأيمن. غيرها: خط مستقيم بمحاذاة الحد الأمامي |
| حساس الخيط | أول `[filament_switch_sensor]` أو `[filament_motion_sensor]` موجود |
| قفل الرأس | كل `stepper_*` له `hold_current` في قسم TMC |
| التحميل الطويل (bowden) | يُقسَّم إلى قطع أقصر من `max_extrude_only_distance` |

كل ما عدا ذلك يُغيَّر من الشاشة: **Color swap settings** (الخطوة 6)، أو الماكرو `COLOR_SWAP_SETTINGS` في Mainsail.
لطابعة bowden: اضبط **Printer setup ← Filament path ← Length pulled out / Length pushed in** على طول الأنبوب.

### 4. قيمة واحدة تتحقق منها: ماذا يدفع RESUME عندك

الماكرو يستدعي `PAUSE` و`RESUME` **الموجودين عندك**. في Mainsail و Fluidd: سحب 1 مم عند التوقف ودفع 1 مم عند الإكمال.
الإعداد **Printer setup ← This printer ← What RESUME pushes by itself** (`pause_retract_mm`، الافتراضي 1) يجب أن يساوي هذا الرقم. اجعله 0 إن كان `RESUME` عندك لا يدفع شيئًا.

### 5. أسطر الربط (مستحسنة، غير إلزامية)

بدونها يعمل الماكرو: يلاحظ الإلغاء خلال 10 ثوانٍ، وبداية طباعة جديدة أو نهايتها خلال دقيقة.
معها يصير أشد أمانًا (ضغط `RESUME` بلا خيط محمَّل يُرفض):

| الماكرو | أضف | أين |
|---|---|---|
| `RESUME` | `_COLOR_SWAP_ON_RESUME` | أول سطر في `gcode:` |
| `CANCEL_PRINT` | `_COLOR_SWAP_RESET` | قبل `CANCEL_PRINT_BASE` |
| `START_PRINT` / `PRINT_START` | `_CS_CLEAR_CHECKPOINT` | أول سطر |
| `END_PRINT` / `PRINT_END` | `_CS_CLEAR_CHECKPOINT DONE=1` | آخر سطر |
| حساس الخيط | `runout_gcode: COLOR_SWAP_RUNOUT` | في قسم الحساس (نفاد الخيط يفتح نافذة التبديل) |

> إن كان `RESUME` و`CANCEL_PRINT` من `mainsail.cfg` أو `fluidd.cfg` (لا يُعدَّل)، انسخ الماكرو إلى ملفك أولًا.

### 6. أزرار KlipperScreen

افتح `KlipperScreen.conf` عندك، والصق محتوى `KlipperScreen_color_swap.conf` **فوق** السطر
`#~# --- Do not edit below this line...`، ثم أعد تشغيل KlipperScreen.

### 7. Save & Restart ثم التحقق

```
COLOR_SWAP_CHECK
```

اقرأ كل سطر: نقطة الصخ يجب أن تكون فوق حافة السرير وبعيدة عن مكان الطباعة، و«Missing sections» يجب أن تقول none.

### طابعتك ليست دلتا؟ اقرأ هذا عن الاستكمال بعد انقطاع الكهرباء

`RESUME_SAVED_PRINT` يجب أن يعرف مكان الرأس دون أن يلمس القطعة.
الدلتا تعمل Home للأعلى، فيعمل دائمًا. في الطابعات الأخرى Home لمحور Z **ينزل على القطعة**، لذلك:

| الحالة | النتيجة |
|---|---|
| المحركات ما زالت تعمل (إلغاء عند تبديل، بلا إعادة تشغيل) | يعمل: بلا Home أصلًا |
| بعد انقطاع الكهرباء أو إعادة التشغيل | يُرفض — إلا إذا فعّلت **Printer setup ← This printer ← After a power cut trust Z** وكان في `printer.cfg` القسم `[force_move]` وفيه `enable_force_move: True`. عندها Home لـ X و Y فقط، و Z يُعتبر كما كان. استعمله فقط إن كان السرير أو الجسر عندك لا يتحرك فعلًا بلا كهرباء. **غير مجرَّب.** |

---

## إعداد OrcaSlicer (مرة لكل بروفايل طابعة)

1. **Printer settings** ← ابحث عن **Manual filament change** ← ✔.
2. **Printer settings** ← ابحث عن **Change filament G-code** ← الصق محتوى `orca_change_filament_gcode.txt`:
   ```
   {if layer_num >= 0}COLOR_SWAP SLOT={next_extruder + 1} MATERIAL={filament_type[next_extruder]} OLD_MATERIAL={filament_type[previous_extruder]} TEMP={new_filament_temp} OLD_TEMP={old_filament_temp} RETRACT={new_retract_length_toolchange} PURGE={flush_length}{endif}
   ```
3. **Process** ← ابحث عن **Prime tower** ← أطفئ **Enable**.
4. **حرارة السرير**: ابحث عن `bed temperature` واختر **By First filament**.
5. اختياري (الإصدار 6 يحفظ نقطة كل دقيقة وحده): **Printer settings** ← **Machine G-code** ← **Before layer change G-code** ← أضف في آخره:
   ```
   _CS_CHECKPOINT LAYER={layer_num + 1} TOTAL={total_layer_count} SLOT={current_extruder + 1} MATERIAL={filament_type[current_extruder]}
   ```
6. احفظ البروفايلين.

---

## التحكم عن بعد (اختياري)

اتبع `telegram_bot.txt`، ثم فعّل **Color swap settings ← Alerts ← Telegram answer buttons**.

---

## الرجوع للإصدار 6.4 (FLSUN V400)

1. ارفع `ROLLBACK_v6.4/color_swap.cfg` مكان `color_swap.cfg` (و`ROLLBACK_v6.4/FLSUN_V400/macros.cfg` مكان `macros.cfg`؛ هو نفس الملف في 6.5).
2. تأكد أن الطابعة **لا تطبع**، ثم اضغط **Save & Restart**.
3. لوحة Telegram: انسخ `ROLLBACK_v6.4/telegram_panel/cs_panel_bot.py` إلى `~/cs-telegram-panel/` ثم شغّل `systemctl --user restart cs-telegram-panel`.
4. Orca لا يحتاج تغييرًا. الإصدار 6.5 لم يضف أي إعداد، فالإعدادات المحفوظة (`cs_set` في `variables.cfg`) تبقى كما هي.

---

## إزالة الماكرو

1. احذف السطر `[include color_swap.cfg]` من `printer.cfg`.
2. احذف أسطر الربط (`_COLOR_SWAP_ON_RESUME`، `_COLOR_SWAP_RESET`، `_CS_CLEAR_CHECKPOINT`، `COLOR_SWAP_RUNOUT`)، وجزء `COLOR_SWAP RUNOUT=1` من `M600`، وأسطر Orca.
3. **Save & Restart**.
