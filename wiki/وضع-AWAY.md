**العربية** | [English](Away-Mode)

<div dir="rtl">

## الإكمال التلقائي باللون الحالي

**AWAY هو الوضع الافتراضي** (منذ 6.3) مع 5 دقائق: أيًّا كان من بدأ الطباعة، التبديل الذي يغيّر اللون فقط يكمل وحده. أما التبديل الذي يغيّر نوع الخامة فينتظر شخصًا دائمًا (6.5). **Color swap settings ← I am AWAY** — ضغطة واحدة تحوّله إلى **HOME** حين تريد أن ينتظرك كل تبديل. مدة الانتظار هي الزر الذي تحته (5 دقائق).

| ماذا يحدث عند التبديل | |
|---|---|
| الرأس يذهب لنقطة الصخ. الخيط القديم **يبقى في الفوهة** (قد تكمل به الطباعة) | النافذة: **Unload** / **Keep current color** |
| ضغطت أي زر | الإكمال التلقائي يتوقف لهذا التبديل، والطابعة تنتظرك |
| لا أحد يضغط شيئًا 5 دقائق | الطباعة تكمل **باللون الحالي**، وتصل رسالة للهاتف |
| 6.5: خامة السلايسر (MATERIAL) تختلف عن القديمة (PETG ← PLA) | **لا عدّ تنازلي**: التبديل ينتظرك مثل HOME، والفوهة تبرد إلى حرارة الانتظار. زر **Keep** ما زال يكمل بالخيط القديم إن اخترته |

**نفس الخامة، يتغيّر اللون فقط** — النافذة تعدّ تنازليًا:

<table><tr>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/klipperscreen_01_swap_away_color.png" width="460" alt="KlipperScreen"><br><sub>KlipperScreen</sub></td>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/mainsail_01_swap_away_color.png" width="300" alt="Mainsail"><br><sub>Mainsail</sub></td>
</tr></table>

**6.5: الخامة تتغيّر (PETG ← PLA)** — لا عدّ تنازلي، التبديل ينتظرك:

<table><tr>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/klipperscreen_02_swap_away_material.png" width="460" alt="KlipperScreen"><br><sub>KlipperScreen</sub></td>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/mainsail_02_swap_away_material.png" width="300" alt="Mainsail"><br><sub>Mainsail</sub></td>
</tr></table>

**Keep current color** عند تغيّر الخامة يحذّر من الخامة التي سيُطبع بها ذلك الجزء:

<table><tr>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/klipperscreen_03_keep_warning.png" width="460" alt="KlipperScreen"><br><sub>KlipperScreen</sub></td>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/mainsail_03_keep_warning.png" width="300" alt="Mainsail"><br><sub>Mainsail</sub></td>
</tr></table>

- باقي الملف يُطبع باللون «الخطأ» حتى التبديل التالي. لا يضيع شيء آخر.
- التبديل بين خيطين من نفس نوع الخامة فقط هو الذي يكمل وحده؛ الماكرو يقارن `MATERIAL` و`OLD_MATERIAL` من سطر السلايسر. بدون `OLD_MATERIAL` (سطر سلايسر قديم) لا يستطيع المقارنة فيكمل كما كان.
- اضغط **I am AWAY** للتحويل إلى HOME: كل تبديل ينتظرك ويُسحب الخيط القديم فورًا. واضغط **I am HOME** للرجوع إلى AWAY.
- عند التشغيل ينتظر AWAY دائمًا مدة الغياب التي تعرضها النافذة.

## ماذا يفعل الانتظار الطويل (لا شيء هنا يُضيّع الطباعة)

| بعد | ماذا يحدث | للإكمال |
|---|---|---|
| 5 دقائق بلا ضغطة (`standby_min`) | الفوهة تبرد إلى 170° | أي زر يعيد التسخين. **Continue...** يصخ 10 مم أولًا ثم يطلب قطع الخيط |
| 60 دقيقة (`nozzle_off_min`) | سخان الفوهة ينطفئ. **السرير والمحركات تبقى** | نفس الشيء |
| 8 ساعات (`wait_max_min`) | Klipper يطفئ كل شيء | `RESUME_SAVED_PRINT` ([الجزء 3](%D8%A7%D8%B3%D8%AA%D9%83%D9%85%D8%A7%D9%84-%D8%B7%D8%A8%D8%A7%D8%B9%D8%A9-%D9%85%D8%AA%D9%88%D9%82%D9%81%D8%A9)) |
| كل 10 دقائق (`remind_min`) | رسالة للهاتف | — |

## الأوامر عن بعد

أوامر بسيطة لا تحتاج نافذة. أرسلها من أي شيء يصل للطابعة: Mainsail عبر VPN، أو Mobileraker، أو OctoApp، أو Telegram.

| الأمر | ماذا يفعل |
|---|---|
| `CS_STATUS` | أين وصل التبديل، وحرارة الفوهة، والأوامر المناسبة الآن. الرد يصل للهاتف أيضًا |
| `CS_WAIT` | «أنا قادم»: يوقف الإكمال التلقائي لهذا التبديل |
| `CS_KEEP` | بلا تبديل: أكمل الآن باللون الذي في الفوهة |
| `CS_UNLOAD` / `CS_LOAD` | اسحب الخيط القديم / حمّل الخيط الذي أدخله أحدهم وصخّه |
| `CS_PURGE` | صخ 30 مم زيادة (`CS_PURGE MM=60`) |
| `CS_CONTINUE` | انتهى التبديل: أكمل الطباعة. لا أحد يقطع الخيط — انظر للكاميرا أولًا |
| `CS_CANCEL` | إلغاء الطباعة |

</div>
