"""All invented facts for the handwritten test pack: texts, dossier groups and test questions. One source of truth."""
# Fields per design (only for sheets that print boxes): memo TO/FROM/DATE/SUBJECT; gov OUT_NO/DATE;
# voucher DATE/PAID_TO/AMOUNT/WORDS; minutes DATE/TIME/VENUE/ATTENDEES.
# {{wrong|right}} marks the one deliberate crossed-out correction; margin_note is written in the right margin.

TEXTS = [
 dict(n=1, id="HW01", dept="HR", design="letterhead_en", lang="en", title="RESIGNATION LETTER", kind="English formal letter: resignation",
  body="""15 November 2026

Dear Ms Mansour,

I am writing to resign from my position as Senior Accounts Clerk in the Finance Department of Harbourline Trading Co. Ltd. My employee number is E-20418 and I joined the company on 4 September 2019.

In line with my contract, I will work a notice period of 60 days. My last working day will therefore be 14 January 2027. I will hand over my open files, including the supplier reconciliations for October and November, to Ms Lina Qasem before that date.

Please confirm my unused annual leave, which I calculate as 11 days, and the date of my final salary payment.

Yours sincerely,
Khaled Nasser"""),
 dict(n=2, id="HW02", dept="FIN", design="letterhead_en", lang="en", title="COMPLAINT TO SUPPLIER", kind="English formal letter: supplier complaint",
  body="""20 October 2026

Bluewave Marine Supplies Ltd.
Attention: Sales Manager

Subject: Order PO-7731 and invoice INV-5520

Dear Sir or Madam,

We received order PO-7731 on 12 October 2026. Of the 40 life jackets ordered (item LJ-210), only 34 arrived, and 6 of those were damaged. Invoice INV-5520 nevertheless charges us for all 40 units at 18.50 each, a total of 740.00 USD.

Please send the 12 missing and damaged units within 10 days, or issue a credit note for 222.00 USD. We will hold that part of the payment until then.

Yours faithfully,
Omar Haddad
Finance Manager"""),
 dict(n=3, id="HW03", dept="FIN", design="letterhead_bi", lang="en", title="PAYMENT REQUEST", title_ar="طلب سداد", kind="English formal letter: payment request",
  body="""15 November 2026

Delta Office Systems, Accounts Department
Subject: Overdue invoice INV-6104

Dear Sir or Madam,

Our records show that invoice INV-6104, for 12,750.00 USD, fell due on 30 September 2026 and is now 46 days overdue. In line with clause 7.2 of contract SC-2026-014, a late charge of 1.5% (191.25 USD) has been added. The total now payable is 12,941.25 USD.

Please transfer this amount by 25 November 2026 and send us the transfer receipt. If you have already paid, kindly send the payment date and reference so that we can correct our records.

Yours faithfully,
Lina Qasem
Accounts Receivable, Finance Department"""),
 dict(n=4, id="HW04", dept="FIN", design="letterhead_ar", lang="ar", title="OFFICIAL LETTER", title_ar="خطاب رسمي", kind="Arabic official letter (Western and Arabic-Indic digits)",
  body="""إلى: مدير مديرية الإيرادات والرسوم، وزارة الخدمات البلدية
الموضوع: سداد رسوم تجديد الترخيص WL-5521

تحية طيبة وبعد،

بالإشارة إلى كتابكم رقم M/4817/2026 بتاريخ 22/11/2026، نفيدكم بأننا أصدرنا أمرا إلى مصرفنا بتحويل مبلغ 3,450.00 دولار أمريكي، وهو قيمة رسوم التجديد السنوية، إلى حسابكم بتاريخ ١٠ ديسمبر ٢٠٢٦، أي قبل الموعد النهائي بخمسة أيام.

وسنرسل لكم نسخة من إشعار التحويل فور وصوله إلينا. نرجو التكرم بتأكيد استلام المبلغ وإصدار الإيصال الرسمي.

وتفضلوا بقبول فائق الاحترام والتقدير،

عمر حداد
مدير الشؤون المالية"""),
 dict(n=5, id="HW05", dept="HR", design="letterhead_ar", lang="ar", title="LEAVE REQUEST", title_ar="طلب إجازة", kind="Arabic employment / leave request",
  body="""إلى: السيدة رانيا منصور، مديرة إدارة الموارد البشرية
الموضوع: طلب إجازة سنوية

تحية طيبة وبعد،

أتقدم إليكم بطلب إجازة سنوية لمدة ١٠ أيام عمل، تبدأ يوم الأحد 6 ديسمبر 2026 وتنتهي يوم الخميس 17 ديسمبر 2026، على أن أعود إلى العمل يوم الأحد 20 ديسمبر 2026.

رصيد إجازاتي السنوية حتى اليوم هو ٢٢ يوما، ورقمي الوظيفي E-31877. سأسلم أعمالي الجارية إلى الزميلة لينا قاسم قبل بدء الإجازة، ويمكن الاتصال بي عند الضرورة على الرقم 555-0177.

شاكرة لكم حسن تعاونكم،

ليلى الخطيب
محاسبة، إدارة الشؤون المالية"""),
 dict(n=6, id="HW06", dept="FIN", design="memo_ar", lang="mixed", title="INTERNAL MEMORANDUM", title_ar="مذكرة داخلية", kind="Mixed Arabic + English note (product codes and amounts)",
  fields=dict(TO="عمر حداد، مدير الشؤون المالية", FROM="لينا قاسم", DATE="19/10/2026", SUBJECT="طلب الشراء PO-7731 والفاتورة INV-5520"),
  body="""تبين عند استلام الشحنة من شركة Bluewave Marine Supplies أن الكمية المستلمة من الصنف LJ-210 (سترات نجاة) هي 34 قطعة فقط من أصل 40، وأن 6 قطع منها تالفة.

سعر القطعة 18.50 USD، والمبلغ الإجمالي في الفاتورة INV-5520 هو 740.00 USD. أوصي بتعليق دفع مبلغ 222.00 USD (12 قطعة) إلى حين استلام إشعار دائن (credit note) من المورد.

أرجو الموافقة على سداد الباقي، وقدره 518.00 USD، قبل ٣٠ نوفمبر 2026.

مع الشكر،
لينا قاسم"""),
 dict(n=7, id="HW07", dept="HR", design="letterhead_bi", lang="mixed", title="ONBOARDING NOTE", title_ar="مذكرة تهيئة موظف جديد", kind="Mixed Arabic + English note (codes, amounts, dates)",
  body="""ملاحظة تهيئة الموظف الجديد يوسف العلي (E-40235)، المسمى الوظيفي: Warehouse Coordinator، تاريخ المباشرة: الأحد 3 يناير 2027.

التجهيزات المطلوبة:
- حاسوب محمول طراز LT-5520 بسعر 1,150 USD
- شاشة MN-27 وبطاقة دخول رقم B-77204
- حساب بريد إلكتروني ورقم داخلي (extension 215)

الراتب الأساسي 2,800 USD شهريا مضافا إليه بدل سكن 600 USD، وفترة التجربة ٩٠ يوما. يرجى تجهيز العقد EC-2027-009 وإبلاغ قسم IT قبل 28 ديسمبر 2026."""),
 dict(n=8, id="HW08", dept="FIN", design="voucher", lang="en", title="PAYMENT VOUCHER", title_ar="سند صرف", kind="Handwritten receipt / payment voucher with amounts and dates",
  fields=dict(DATE="02/11/2026", PAID_TO="Marwan Salem Transport", AMOUNT="1,275.50", WORDS="One thousand two hundred seventy-five and 50/100 USD"),
  body="""Freight services, invoice FT-0388 dated 28 October 2026.
3 container trips at 350.00 each = 1,050.00
Fuel surcharge = 125.50
Port handling = 100.00
Total paid in cash on 2 November 2026: 1,275.50 USD.
Balance due after this payment: 0.00
Received with thanks from Harbourline Trading Co. Ltd. The next invoice, FT-0391, is expected on 30 November 2026. Voucher approved by Omar Haddad, Finance Manager.""",
  extra="Sign the three lines at the bottom with an invented signature (a squiggle is fine). Do not write a real name there."),
 dict(n=9, id="HW09", dept="FIN", design="minutes", lang="en", title="MINUTES OF MEETING", title_ar="محضر اجتماع", kind="Minutes of a meeting with action items",
  fields=dict(DATE="9 November 2026", TIME="10:30", VENUE="Meeting Room B2", ATTENDEES="O. Haddad (chair), L. Qasem, T. Aziz, M. Reda"),
  body="""1. Q4 budget: approved at 214,000 USD, which is 6,000 USD more than Q3 (208,000 USD).
2. Supplier payments: the Bluewave credit note of 222.00 USD is still missing, so payment of invoice INV-5520 stays on hold.
3. Stock: the count of item LJ-210 must be repeated.

Action items
A1. Lina Qasem - send the reminder for invoice INV-6104 by 16 November 2026.
A2. Tariq Aziz - obtain the Bluewave credit note by 20 November 2026.
A3. Mona Reda - recount item LJ-210 by 25 November 2026.

Next meeting: 7 December 2026 at 10:30. Meeting closed at 11:45."""),
 dict(n=10, id="HW10", dept="FIN", design="formal_ruled", lang="en", title="CONTRACT CLAUSE", kind="Short contract clause",
  body="""Clause 7 - Payment and late payment
Contract No. SC-2026-014, effective 1 July 2026, between Harbourline Trading Co. Ltd. (the Seller) and Delta Office Systems (the Buyer).

7.1 The Buyer shall pay each invoice within 30 days of the invoice date.
7.2 If an invoice is not paid by its due date, the Seller may add a one-time late charge of 1.5% of the overdue amount.
7.3 The Buyer must notify the Seller in writing of any dispute within 10 days of receiving the invoice. The undisputed part must still be paid on time.
7.4 The total liability of the Seller shall not exceed 50,000 USD."""),
 dict(n=11, id="HW11", dept="HR", design="hr_employment", lang="en", title="EMPLOYMENT LETTER", kind="English employment letter (offer)",
  body="""19 November 2026

Dear Mr Al-Ali,

We are pleased to offer you the position of Warehouse Coordinator at Harbourline Trading Co. Ltd., starting on Sunday 3 January 2027. Your contract number is EC-2027-009.

Your basic salary will be 2,800 USD per month, with a housing allowance of 600 USD, a total of 3,400 USD per month, paid on the 25th of each month. You are entitled to 24 days of annual leave per year. The probation period is 90 days and ends on 3 April 2027.

Please sign and return a copy of this letter by 20 December 2026.

Yours sincerely,
Rania Mansour
Human Resources Manager"""),
 dict(n=12, id="HW12", dept="FIN", design="letterhead_en", lang="en", title="BANK TRANSFER INSTRUCTION", kind="Bank transfer instruction with account numbers and amounts",
  body="""10 December 2026

To: The Manager, First Coastal Bank, Port District Branch

Please debit our current account no. 1100-2345-6789 (Harbourline Trading Co. Ltd.) and make the following transfers today, value date 10 December 2026:

1. Municipal Services Ministry, fee account 0045-7781-2209, USD 3,450.00, reference WL-5521 licence renewal.
2. Bluewave Marine Supplies Ltd., account 7730-1195-4402, USD 8,600.00, reference INV-5601.

Total debit: USD 12,050.00. Please send the confirmation to accounts@harbourline.example.

Authorised signatories: Omar Haddad and Lina Qasem."""),
 dict(n=13, id="HW13", dept="FIN", design="certificate", lang="en", title="STATEMENT OF FIGURES", kind="List of numbers and dates (digit stress test)",
  body="""Statement of unpaid customer invoices, 05/11/2026

INV-6104   12,750.00   due 30/09/2026
INV-6122   4,380.75   due 15/10/2026
INV-6139   9,015.40   due 31/10/2026
INV-6150   1,206.05   due 20/11/2026
Total outstanding: 27,352.20 USD

Other figures to check:
Purchase orders: 7731, 7748, 7790
Weights: 0.5 kg, 17.25 kg, 108 kg
Rates: 1.5%, 12%, 100%
Account: 1100-2345-6789
Telephone: +00 21 555 0142
Arabic-Indic digits: ٢٠٢٦/١١/٠٥ and ١٢٬٧٥٠٫٠٠
Prepared by Lina Qasem, checked by Omar Haddad."""),
 dict(n=14, id="HW14", dept="FIN", design="memo_en", lang="en", title="INTERNAL MEMORANDUM", kind="Letter with one deliberate crossed-out correction",
  fields=dict(TO="All warehouse and finance staff", FROM="Omar Haddad, Finance Manager", DATE="23 November 2026", SUBJECT="Year-end stock count"),
  body="""The annual stock count will take place on {{28 December|29 December}} 2026. The warehouse will be closed to deliveries and dispatches from 08:00 to 18:00 on that day.

Four teams of three people each will count the stock. Every team must record the item code, the quantity counted and the shelf number. Differences of more than 2% must be reported to Mona Reda the same day.

Please confirm your attendance with Lina Qasem by 10 December 2026."""),
 dict(n=15, id="HW15", dept="HR", design="formal_ruled", lang="en", title="OVERTIME APPROVAL", kind="Letter with a margin note",
  body="""To: Rania Mansour, Human Resources Manager
Subject: Overtime of the warehouse team, November 2026

Dear Ms Mansour,

Six employees of the warehouse team worked overtime on three weekends in November 2026, 8 hours each weekend: 144 hours in total.

The overtime rate is 18.00 USD per hour (1.5 times the normal rate of 12.00 USD). The total amount is therefore 2,592.00 USD.

Please approve this amount so that it can be paid with the November payroll on 25 November 2026.

Regards,
Mona Reda, Warehouse Supervisor""",
  margin_note=dict(lines=["Approved.", "Pay with Nov", "payroll. R.M.", "18/11/2026"], at_line=9, where="in the right margin column, beside the second paragraph (about the 9th ruled line)")),
 dict(n=16, id="HW16", dept="FIN", design="gov", lang="ar", title="OFFICIAL CORRESPONDENCE", title_ar="مراسلة رسمية", kind="Arabic government-style letter (Western and Arabic-Indic digits)",
  fields=dict(OUT_NO="M/4817/2026", DATE="22/11/2026"),
  body="""السادة / شركة هاربورلاين للتجارة المحدودة المحترمين
السلام عليكم ورحمة الله وبركاته،

الموضوع: رسوم تجديد ترخيص المستودع رقم WL-5521

نفيدكم بأن ترخيص المستودع الخاص بشركتكم ينتهي بتاريخ ٣١ ديسمبر 2026، وأن رسوم التجديد السنوية هي 3,450 دولار أمريكي. يرجى سدادها في موعد أقصاه ١٥ ديسمبر 2026 وتزويدنا بنسخة من إشعار التحويل.

وفي حال التأخر، ستفرض غرامة قدرها 5% من قيمة الرسوم عن كل أسبوع تأخير.

وتفضلوا بقبول فائق الاحترام،

مدير مديرية الإيرادات والرسوم
المهندس سليم الزعبي"""),
 dict(n=17, id="HW17", dept="HR", design="minutes", lang="mixed", title="MINUTES OF MEETING", title_ar="محضر اجتماع", kind="Arabic minutes with English terms and action items",
  fields=dict(DATE="12/11/2026", TIME="9:00", VENUE="قاعة الاجتماعات 2", ATTENDEES="رانيا منصور، ليلى الخطيب، سلمى العمر"),
  body="""افتتحت السيدة رانيا منصور الاجتماع الساعة 9:00، وتمت مناقشة البنود التالية:

1. خطة التوظيف للربع الأول من 2027: الموافقة على تعيين ٣ موظفين جدد.
2. التدريب: دورة السلامة المهنية (Safety Training) يوم ١٧ ديسمبر 2026 لـ 12 متدربا، والتكلفة الإجمالية 1,800 دولار.

بنود العمل:
أ) سلمى العمر: إعداد قائمة المتدربين قبل 25 نوفمبر 2026.
ب) ليلى الخطيب: حجز القاعة قبل 1 ديسمبر 2026.
ج) رانيا منصور: رفع طلب الميزانية إلى الإدارة المالية وتأكيد المدرب.

الاجتماع القادم: 10 ديسمبر 2026."""),
]

# dossier id -> text ids (ids pass keys.DOSSIER_ID_RE; checked in make_texts)
GROUPS = {
 "FIN-C95-S1-F0001": ["HW02", "HW03", "HW04", "HW16"],
 "FIN-C95-S1-F0002": ["HW06", "HW08", "HW12", "HW13"],
 "FIN-C96-S1-F0001": ["HW09", "HW10", "HW14"],
 "HR-C95-S1-F0001": ["HW01", "HW05", "HW11"],
 "HR-C96-S1-F0001": ["HW07", "HW15", "HW17"],
}

# (group, question language, question, expected answer, kind, source text ids); kind: text | numeric | none | correction
QUESTIONS = [
 ("FIN-C95-S1-F0001", "en", "How many life jackets were damaged in order PO-7731?", "6 (of the 34 that arrived).", "numeric", "HW02"),
 ("FIN-C95-S1-F0001", "en", "What is the annual renewal fee for warehouse licence WL-5521 and by what date must it be paid?", "3,450 USD, by 15 December 2026.", "numeric", "HW16"),
 ("FIN-C95-S1-F0001", "ar", "ما المبلغ الإجمالي المستحق على Delta Office Systems بعد إضافة غرامة التأخير؟", "12,941.25 USD (12,750.00 plus the 191.25 late charge).", "numeric", "HW03"),
 ("FIN-C95-S1-F0001", "ar", "متى أمرت الشركة المصرف بتحويل رسوم تجديد الترخيص؟", "On 10 December 2026 (١٠ ديسمبر ٢٠٢٦).", "text", "HW04"),
 ("FIN-C95-S1-F0001", "en", "What discount did Bluewave Marine Supplies offer on the next order?", "NOT ANSWERABLE: the documents mention no discount. The system should say it cannot find it.", "none", "-"),
 ("FIN-C95-S1-F0002", "ar", "كم المبلغ الذي أوصت لينا قاسم بتعليق دفعه بخصوص الفاتورة INV-5520؟", "222.00 USD (12 pieces).", "numeric", "HW06"),
 ("FIN-C95-S1-F0002", "en", "How much was paid to Marwan Salem Transport and on what date?", "1,275.50 USD, on 2 November 2026 (02/11/2026).", "numeric", "HW08"),
 ("FIN-C95-S1-F0002", "ar", "ما رقم حساب Bluewave Marine Supplies في تعليمات التحويل المصرفي؟", "7730-1195-4402.", "text", "HW12"),
 ("FIN-C95-S1-F0002", "en", "What is the total outstanding amount in the statement of unpaid invoices?", "27,352.20 USD.", "numeric", "HW13"),
 ("FIN-C95-S1-F0002", "en", "What is the SWIFT code of First Coastal Bank?", "NOT ANSWERABLE: no SWIFT code appears in the documents.", "none", "-"),
 ("FIN-C96-S1-F0001", "en", "On what date will the annual stock count take place?", "29 December 2026. The first value, 28 December, is crossed out and corrected by hand: the corrected value is the answer.", "correction", "HW14"),
 ("FIN-C96-S1-F0001", "en", "What late charge does the contract clause allow if an invoice is not paid on time?", "A one-time late charge of 1.5% of the overdue amount (clause 7.2).", "numeric", "HW10"),
 ("FIN-C96-S1-F0001", "ar", "من يجب أن يحصل على إشعار الدائن من Bluewave ومتى؟", "Tariq Aziz, by 20 November 2026.", "text", "HW09"),
 ("FIN-C96-S1-F0001", "ar", "كم بلغت ميزانية الربع الرابع التي تمت الموافقة عليها؟", "214,000 USD.", "numeric", "HW09"),
 ("FIN-C96-S1-F0001", "en", "Who will lead each stock-count team in the warehouse?", "NOT ANSWERABLE: the memo gives team sizes but no team leaders.", "none", "-"),
 ("HR-C95-S1-F0001", "en", "What is Khaled Nasser's last working day?", "14 January 2027.", "text", "HW01"),
 ("HR-C95-S1-F0001", "ar", "كم يوما طلبت ليلى الخطيب كإجازة سنوية ومتى تعود إلى العمل؟", "10 working days; she returns on Sunday 20 December 2026.", "numeric", "HW05"),
 ("HR-C95-S1-F0001", "ar", "ما إجمالي الراتب الشهري المعروض على السيد العلي؟", "3,400 USD (2,800 basic plus 600 housing).", "numeric", "HW11"),
 ("HR-C95-S1-F0001", "en", "When does Mr Al-Ali's probation period end?", "3 April 2027.", "text", "HW11"),
 ("HR-C95-S1-F0001", "en", "Why is Khaled Nasser resigning?", "NOT ANSWERABLE: the letter gives no reason.", "none", "-"),
 ("HR-C96-S1-F0001", "en", "Which laptop model will the new employee receive and what does it cost?", "Model LT-5520, 1,150 USD.", "numeric", "HW07"),
 ("HR-C96-S1-F0001", "en", "What is the total overtime amount for the warehouse team in November 2026?", "2,592.00 USD (144 hours at 18.00).", "numeric", "HW15"),
 ("HR-C96-S1-F0001", "en", "Was the overtime approved, by whom and when? (answer is in the margin note)", "Yes: approved by R.M. on 18/11/2026, to be paid with the November payroll.", "text", "HW15"),
 ("HR-C96-S1-F0001", "ar", "كم بلغت التكلفة الإجمالية لدورة السلامة المهنية؟", "1,800 USD for 12 trainees.", "numeric", "HW17"),
 ("HR-C96-S1-F0001", "ar", "من هو المدرب الذي سيقدم دورة السلامة المهنية؟", "NOT ANSWERABLE: the minutes only say the trainer must still be confirmed.", "none", "HW17"),
]
