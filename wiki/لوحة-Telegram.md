**العربية** | [English](Telegram-Panel)

<div dir="rtl">

`telegram_panel/` بوت صغير يعمل على الطابعة ويحوّل المحادثة إلى لوحة تحكم. لا تكتب شيئًا: كل شيء أزرار. نصوص اللوحة بالإنجليزية.

**هي للتحكم بالطابعة عن بعد.** كل ما يحتاج شخصًا واقفًا أمام الطابعة — Unload، Load + purge، Purge، Re-home، أزرار المواد، Printer setup — **غير موجود** في المحادثة عمدًا.

<table><tr>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_6_keyboard.png" width="620" alt="Telegram"><br><sub>شريط المفاتيح (دائمًا في الأسفل)</sub></td>
</tr></table>

<table><tr>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_2_panel_next_swap.png" width="360" alt="Telegram"><br><sub>لوحة التحكم أثناء الطباعة مع التبديل القادم (1.8)</sub></td>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_1_print_start.png" width="360" alt="Telegram"><br><sub>رسالة بداية الطباعة (1.7) والتنبيه قبل التبديل بـ 10 دقائق (1.8)</sub></td>
</tr></table>

| في المحادثة | ما هو |
|---|---|
| **شريط المفاتيح** (دائمًا في الأسفل، مكان لوحة مفاتيح الهاتف) | **Status**، **Pause**، **Resume**، **Home / Away**، **Photo**، **Settings**، **Cancel print**، **STOP**. يبقى مكانه مهما كثرت الرسائل، فلا تحتاج للتمرير للوصول للتحكم. المفتاح يعمل فقط حين يكون له معنى (Pause لا يفعل شيئًا والطابعة متوقفة)، و Cancel print و STOP يسألان فقط، وجواب Yes / No على اللوحة |
| لوحة التحكم | رسالة **واحدة** مثبّتة في أعلى المحادثة وتحدّث نفسها (كل دقيقة أثناء الطباعة). أي مفتاح ينزلها إلى الأسفل فوق المفاتيح مباشرة، ويحذف النسخة القديمة وضغطة المفتاح، فتبقى المحادثة نظيفة. الحالة، الملف، نسبة الإنجاز، الطبقة، الوقت الباقي، الحرارة، التبديل المنتظر، HOME / AWAY. الأزرار: **Refresh**، **Photo** و **Video** (مع كاميرا)، **Pause / Resume**، **Cancel print**، **Heaters off** (والطابعة متوقفة وسخان يعمل)، **I am HOME / AWAY**، **Settings**، **Timelapse ON / OFF** و **Last timelapse** (مع moonraker-timelapse)، **Emergency stop** |
| رسالة بداية الطباعة | فقط لطباعة فيها تبديل ألوان (Moonraker يعدّها من الملف). تعرض الخيوط المستعملة (بالغرام)، وتنبّه إذا تغيّر نوع الخامة (تلك التبديلات تنتظرك حتى في AWAY)، وتذكر الوضع وفيها **I am HOME - tap when leaving** / **I am AWAY** و **Settings** — وقت الاختيار قبل أول تبديل. أزرارها تختفي عند بداية التبديل |
| بطاقة تبديل اللون | تُرسل وحدها عند بداية التبديل (يرنّ الهاتف) وتتحدّث في مكانها. تقول ما الذي ينتظر، وتعرض فقط ما ينفع عن بعد |
| التبديل القادم (1.8) | أثناء الطباعة تعرض اللوحة **🔜 Next swap: Filament 2 PLA at layer 42 · about 16 min**، وقبل كل تبديل بـ `warn_min` (10) دقائق تصل رسالة واحدة **🔔 Color swap in about 10 min** تقول ما سيحدث هناك |
| الكاميرا (1.9) | مع كاميرا على الطابعة، **📷 Photo** (المفتاح واللوحة وبطاقة التبديل) يرسل صورة للطابعة. وتصل صورة وحدها تحت بطاقة التبديل مباشرة عند بداية التبديل، وعند جاهزية التنظيف (**is the color right?** — افحص اللون عن بعد)، وعند نفاد الخيط، وعند نهاية الطباعة (اكتملت، خطأ، أُلغيت). الكاميرا تُكتشف وحدها (أول كاميرا في Moonraker)؛ و`camera:` في `cs_telegram.conf` يقبل رابط صورة، أو `off`. بلا كاميرا أو مفصولة: لا يظهر زر Photo ولا يتغيّر شيء آخر. الصور التلقائية تتبع **Alerts ← Phone messages** |
| الفيديو والتايم لابس (1.9) | **🎥 Video** يسجّل 10 ثوانٍ من الكاميرا الحية على الطابعة (ffmpeg، نواة واحدة، أدنى أولوية: عرض 640، نحو 1.5 MB) ويرسلها لتشاهدها في المحادثة. البث الحي المستمر غير ممكن في بوت Telegram. ومع moonraker-timelapse تعرض اللوحة **🎬 Timelapse: ON / OFF** (ضغطة واحدة تبدّله)، وفيديو الطباعة **المكتملة** يصل للمحادثة وحده بعد أن يصنعه Moonraker (`timelapse_video: off` في `cs_telegram.conf` يوقف ذلك)، و **🎞 Last timelapse** يرسل أحدث فيديو مرة أخرى. Telegram يقبل من البوت 50 MB كحد أقصى: الفيديو الأكبر يبقى في Mainsail ← Timelapse |
| Settings | نافذة إعدادات [الجزء 5](%D9%86%D8%A7%D9%81%D8%B0%D8%A9-%D8%A7%D9%84%D8%A5%D8%B9%D8%AF%D8%A7%D8%AF%D8%A7%D8%AA) بنفس الأزرار، تتحدّث في مكانها (بلا Printer setup و Check install) |

**ماذا تعرض بطاقة تبديل اللون**

| الحالة | الأزرار |
|---|---|
| الخيط القديم ما زال في الفوهة (وضع AWAY، أو السحب التلقائي مطفأ) | **Keep the current color and continue**، **Wait for me - do not continue** (ما دام العدّ التنازلي يعمل؛ ولا يظهر عند تغيّر الخامة لأنه ينتظر أصلًا)، **Cancel print** |
| الخيط القديم خرج (أو يُسحب الآن في HOME)، أو الجديد محمَّل وينتظر فحص اللون | **Cancel print** فقط — والبطاقة تقول إن أحدًا يجب أن يكون عند الطابعة، وإن AWAY يُضبط قبل التبديل |
| نفاد الخيط | **Cancel print** فقط |

<table><tr>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_3_swap_card_away.png" width="300" alt="Telegram"><br><sub>AWAY، يتغيّر اللون فقط: عدّ تنازلي</sub></td>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_4_swap_card_material.png" width="300" alt="Telegram"><br><sub>AWAY، تتغيّر الخامة: ينتظرك</sub></td>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_5_keep_warning.png" width="300" alt="Telegram"><br><sub>Keep يسأل أولًا ويحذّر</sub></td>
</tr></table>

<table><tr>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_7_purge_photo.png" width="300" alt="Telegram"><br><sub>التنظيف جاهز: البطاقة ثم صورة لفحص اللون</sub></td>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_8_video.png" width="300" alt="Telegram"><br><sub>🎥 Video: عشر ثوانٍ من الكاميرا الحية</sub></td>
</tr></table>

- Keep و Cancel print و Emergency stop تسأل مرة ثانية.
- عند انتهاء التبديل تُغلق البطاقة وحدها وتقول كيف انتهى: أكملت بأي خيط، أو أُلغيت.
- النوافذ التي تُفتح **على** الطابعة (نافذة التبديل، الإعدادات، الاستكمال) لا تُرسل للمحادثة.
- محادثتك وحدها تستعمله، وأي محادثة أخرى تُتجاهل. لا توجد طريقة لإرسال G-code.
- 1.4: الزر يظهر فقط ما دام ينفع. أثناء تبديل يحتاج يدًا لا يوجد زر HOME / AWAY في اللوحة (ومفتاح Home / Away لا يفعل شيئًا). وعند توقف Klipper (بعد إيقاف طارئ) تعرض اللوحة فقط **Restart Klipper** (يسأل أولًا).
- 1.4: Klipper لا ينفّذ أي أمر أثناء التسخين. الضغطة حينها لا تضيع: اللوحة تقول **switching to AWAY - waiting for the printer**، وتُنفَّذ فور انتهاء التسخين قبل أي تبديل.
- إصلاح 1.4: في 1.3 كانت رسالة Telegram «pinned a message» تُقرأ كضغطة مفتاح، فتُرسل لوحة جديدة وتُثبَّت كل ثانيتين حتى حظر Telegram البوت لساعات. هذه الرسائل تُتجاهل الآن، ورد «too many requests» يُنتظر.
- يستعمل البوت الموجود عندك للتنبيهات (سطر `tgram://` في `moonraker.conf`) — بلا رمز جديد.
- مكتبة Python القياسية فقط، ملف واحد، خدمة واحدة للمستخدم العادي (`cs-telegram-panel`). بلا sudo وبلا كلمة مرور.
- ما يفعله يُكتب في `cs_telegram_panel.log` (Mainsail ← Machine ← logs).

**التثبيت** (مرة واحدة عبر SSH والطابعة متوقفة): انسخ مجلد `telegram_panel` إلى الطابعة ونفّذ `bash install.sh`. للإزالة: `bash install.sh remove`. لإعادة تشغيله: `systemctl --user restart cs-telegram-panel`.

اترك **Alerts ← Telegram answer buttons** على OFF مع هذه اللوحة: ذلك الزر للبوت الآخر (`telegram_bot.txt`، moonraker-telegram-bot)، وهو بديل وليس إضافة.

> الإصدار 1.9 (الكاميرا) مثبّت على FLSUN V400 (2026-11-23): الخدمة تعمل، وشريط المفاتيح الجديد أُرسل، وعلى الطابعة نفسها وجدت اللوحة كاميرا USB عبر Moonraker، والتقطت صورة حقيقية، وأظهرت زر Photo. وعلى الطابعة صُنع فيديو حقيقي مدته 10 ثوانٍ (640x360، 1.4 MB، في 10.7 ثانية) وأظهرت اللوحة Photo و Video و Timelapse: ON. جُرّب مع خادم Telegram وهمي والطابعة المحاكاة (163 فحصًا). الصور التلقائية وفيديو التايم لابس لم تُشاهَد بعد في طباعة حقيقية.
>
> الإصدار 1.8 مثبّت على FLSUN V400 (2026-11-21): الخدمة تعمل واللوحة المثبّتة حُدّثت. الأجزاء الجديدة جُرّبت مع خادم Telegram وهمي والطابعة المحاكاة (114 فحصًا: `python telegram_panel/test_panel_bot.py`)، وقراءة الملف جُرّبت على ملف طباعة حقيقي 5 MB على الطابعة نفسها (1.5 ثانية). التنبيه المسبق لم يُشاهَد بعد في طباعة حقيقية.

</div>
