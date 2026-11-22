**العربية** | [English](OrcaSlicer-Setup)

<div dir="rtl">

> اكتب اسم كل إعداد في **مربع البحث** داخل الإعدادات. إن لم يظهر، فعّل **Advanced**.

1. **Printer settings** ← **Change filament G-code** ← امسح ما فيه والصق هذا السطر كما هو (سطر واحد):
   ```
   {if layer_num >= 0}COLOR_SWAP SLOT={next_extruder + 1} MATERIAL={filament_type[next_extruder]} OLD_MATERIAL={filament_type[previous_extruder]} TEMP={new_filament_temp} OLD_TEMP={old_filament_temp} RETRACT={new_retract_length_toolchange} PURGE={flush_length}{endif}
   ```
2. **حرارة السرير** ← ابحث عن `bed temperature` ← اختر الخيار **By First filament** (بدل **By Highest Temp**).
   بهذا يبقى السرير على حرارة الخيط المطبوع أولًا طوال الطباعة. الماكرو نفسه لا يغيّر حرارة السرير أبدًا.
3. **نقاط الحفظ (للكهرباء)** ← **Printer settings** ← **Machine G-code** ← **Before layer change G-code** ←
   أضف هذا السطر **في آخره** (اترك الأسطر الموجودة كما هي):
   ```
   _CS_CHECKPOINT LAYER={layer_num + 1} TOTAL={total_layer_count} SLOT={current_extruder + 1} MATERIAL={filament_type[current_extruder]}
   ```
   المحتوى الكامل في `orca_before_layer_change_gcode.txt`. يمكن إضافته لأي بروفايل طابعة، حتى للطباعة بلون واحد.
   > إن أظهر Orca خطأ عند التقطيع بسبب هذا السطر: احذف الجزأين `SLOT=…` و`MATERIAL=…` واترك الباقي.
4. احفظ إعداد الطابعة وإعداد الطباعة.

باقي الإعدادات كما هي من الإصدار 2: **Manual filament change** ✔، **Prime tower** مطفأ،
**Exclude objects** ✔ و**Label objects** ✔.

## كمية الصخ

زر **Flushing volumes** في لوحة Filament (فوق الخيوط) يعرض الجدول. Orca يحسب الكمية من فرق اللونين.
الماكرو يأخذها، ويطبّق عليها:

| القاعدة | القيمة |
|---|---|
| أقل كمية | 25 مم (≈ 60 مم³) |
| أكثر كمية | 250 مم |
| إضافة عند تغيير **النوع** (PLA ↔ PETG) | +15 مم |
| إضافة عند **الرجوع للفيلمنت الأساسي** (مثلًا PLA دعامات ← PETG) | +20 مم (60 قبل 6.6) |
| بدون رقم من Orca | 50 مم (القيمة القياسية في Marlin، ≈ 120 مم³ مثل Prusa) |

مثال: PLA ← PETG (رجوع للأساسي) = 25 + 15 + 20 = **60 مم**، على 3 دفعات كل منها 20 مم.

**لتعديل الكميات:** **Color swap settings ← Purge amount** (LOW / NORMAL / HIGH)، أو رقمًا رقمًا من **Advanced ← Purge details** ([الجزء 5](%D9%86%D8%A7%D9%81%D8%B0%D8%A9-%D8%A7%D9%84%D8%A5%D8%B9%D8%AF%D8%A7%D8%AF%D8%A7%D8%AA)). لا حاجة لإعادة التشغيل.

> مرجع للمقارنة: مستخدمو Bambu يذكرون حوالي 800 مم³ (≈ 330 مم) لتغيير PLA ← PETG. إن بقيت الطبقة هشّة بعد التغيير، ارفع الرقم إلى 120–200.

</div>
