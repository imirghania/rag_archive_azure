"""Content of the typed test pack. Fictional organisations and people only.
Block kinds: P(text), H(text), T(header, rows, foot=n bold last rows)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class P:
    text: str


@dataclass
class H:
    text: str


@dataclass
class T:
    header: list[str]
    rows: list[list[str]]
    foot: int = 0  # last n rows are bold (totals)
    rtl: bool | None = None  # None: right-to-left when the header starts with Arabic


@dataclass
class Doc:
    ref: str            # one token: the segmenter reads `Ref: <token>`
    title: str          # CAPITAL LETTERS, two words or more
    dept: str           # FIN or HR
    lang: str           # en, ar, mixed
    what: str           # one line for the README
    blocks: list = field(default_factory=list)


# ---------------------------------------------------------------- FINANCE, English
SUPPLY = Doc("SA-2026-0415", "SUPPLY AGREEMENT EXTRACT", "FIN", "en",
    "Supplier contract extract: prices, 45-day payment, 2% early discount, 1.5% late interest, AED 750,000 liability cap", [
    P('Supply Agreement between Harbor Pine Supplies Ltd ("Supplier") and Marwa Logistics LLC ("Buyer").'),
    P("Effective date: 1 March 2026. Term: 24 months, ending 28 February 2028."),
    H("1. Prices (AED, excluding VAT)"),
    T(["Item code", "Description", "Unit price", "Minimum order"], [
        ["PK-200", "Pallet wrap roll", "38.50", "500"],
        ["PK-310", "Corrugated box, large", "4.75", "2,000"],
        ["PK-450", "Strapping band reel", "112.00", "100"]]),
    H("2. Payment"),
    P("Invoices are payable within 45 days of the invoice date. A discount of 2% of the invoice subtotal applies when "
      "payment is received within 10 days. Late payments carry interest of 1.5% per month."),
    H("3. Liability and termination"),
    P("Supplier liability is capped at AED 750,000 per contract year. Either party may terminate with 90 days written "
      "notice. Prices are fixed for the first 12 months and may rise by up to 3% afterwards."),
    P("Signed for the Supplier: Rania Kassab, Sales Director."),
    P("Signed for the Buyer: Omar Haddad, Finance Director."),
])

INVOICE = Doc("INV-2026-1187", "SALES INVOICE", "FIN", "en",
    "Supplier invoice: three lines, VAT 5%, total AED 50,835.75, due 29 May 2026", [
    P("Seller: Harbor Pine Supplies Ltd. Customer: Marwa Logistics LLC."),
    P("Invoice date: 14 April 2026. Due date: 29 May 2026. Customer order: PO-2026-0388."),
    T(["Item code", "Description", "Qty", "Unit price", "Amount"], [
        ["PK-200", "Pallet wrap roll", "600", "38.50", "23,100.00"],
        ["PK-310", "Corrugated box, large", "2,500", "4.75", "11,875.00"],
        ["PK-450", "Strapping band reel", "120", "112.00", "13,440.00"],
        ["", "Subtotal", "", "", "48,415.00"],
        ["", "VAT 5%", "", "", "2,420.75"],
        ["", "Total due (AED)", "", "", "50,835.75"]], foot=3),
    P("Early payment discount: 2% of the subtotal (AED 968.30) if paid by 24 April 2026."),
    P("Payment terms: 45 days from the invoice date."),
])

BANK = Doc("BS-2026-05-001", "BANK STATEMENT", "FIN", "en",
    "Bank statement page, May 2026: opening 182,400.00, closing 173,839.25, six transactions", [
    P("Account holder: Marwa Logistics LLC. Bank: Gulfstream Commercial Bank. Account ending 4471."),
    P("Statement period: 1 May 2026 to 31 May 2026. Currency: AED."),
    T(["Date", "Description", "Debit", "Credit", "Balance"], [
        ["01 May 2026", "Opening balance", "", "", "182,400.00"],
        ["01 May 2026", "Rent warehouse 14 (LS-2025-0092)", "19,240.00", "", "163,160.00"],
        ["03 May 2026", "Receipt Al Faris Retail", "", "64,200.00", "227,360.00"],
        ["12 May 2026", "Payroll batch April 2026", "41,515.00", "", "185,845.00"],
        ["15 May 2026", "Bank charges", "120.00", "", "185,725.00"],
        ["20 May 2026", "Receipt Desert Rose Hotels", "", "38,950.00", "224,675.00"],
        ["26 May 2026", "Payment INV-2026-1187 Harbor Pine", "50,835.75", "", "173,839.25"],
        ["31 May 2026", "Closing balance", "", "", "173,839.25"]], foot=1),
    P("Total debits: 111,710.75. Total credits: 103,150.00. Closing balance: 173,839.25."),
])

EXPENSE = Doc("POL-FIN-007", "EXPENSE POLICY SUMMARY", "FIN", "en",
    "Plain-text policy: allowances, receipt threshold AED 75, approval limits 5,000 / 25,000", [
    P("Effective 1 January 2026. Applies to all staff of Marwa Logistics LLC."),
    H("1. Allowances"),
    T(["Item", "Limit (AED)"], [
        ["Meal allowance, domestic travel, per day", "120"],
        ["Meal allowance, international travel, per day", "250"],
        ["Hotel, per night", "650"],
        ["Mileage, per km", "0.80"]]),
    H("2. Receipts and claims"),
    P("A receipt is required for any expense above AED 75. Claims must be submitted within 30 days of the expense. "
      "Approved claims are reimbursed within 10 working days."),
    H("3. Approval limits"),
    T(["Claim amount (AED)", "Approver"], [
        ["Up to 5,000", "Line manager"],
        ["Above 5,000 and up to 25,000", "Finance Director"],
        ["Above 25,000", "Chief Financial Officer"]]),
])

# ---------------------------------------------------------------- FINANCE, Arabic
LEASE = Doc("LS-2025-0092", "WAREHOUSE LEASE AGREEMENT", "FIN", "ar",
    "Arabic lease: warehouse 14, 3 years, rent 18,500/month, +4% a year, deposit 37,000, 60-day notice", [
    H("عقد إيجار مستودع"),
    P("تاريخ العقد: 15 ديسمبر 2024"),
    P("الطرف الأول (المؤجر): شركة النخيل للعقارات ذ.م.م، ويمثلها السيد فيصل الزعابي، مدير الأملاك."),
    P("الطرف الثاني (المستأجر): شركة مروة للخدمات اللوجستية ذ.م.م، ويمثلها السيد عمر حداد، المدير المالي."),
    H("البند الأول: العقار"),
    P("أجّر الطرف الأول للطرف الثاني المستودع رقم 14 في المنطقة الصناعية الثالثة، بمساحة 2,400 متر مربع، "
      "لاستخدامه في التخزين والتوزيع فقط."),
    H("البند الثاني: المدة"),
    P("مدة الإيجار ثلاث سنوات، تبدأ في 1 يناير 2025 وتنتهي في 31 ديسمبر 2027، وتُجدَّد بموافقة الطرفين كتابةً "
      "قبل 90 يومًا من انتهائها."),
    H("البند الثالث: الأجرة"),
    P("الأجرة السنوية في السنة الأولى 222,000 درهم، تُدفع شهريًا بواقع 18,500 درهم في اليوم الأول من كل شهر. "
      "تزداد الأجرة بنسبة 4% في بداية كل سنة تالية."),
    T(["السنة", "الفترة", "الأجرة الشهرية (درهم)", "الأجرة السنوية (درهم)"], [
        ["الأولى", "1 يناير 2025 إلى 31 ديسمبر 2025", "18,500.00", "222,000.00"],
        ["الثانية", "1 يناير 2026 إلى 31 ديسمبر 2026", "19,240.00", "230,880.00"],
        ["الثالثة", "1 يناير 2027 إلى 31 ديسمبر 2027", "20,009.60", "240,115.20"]]),
    H("البند الرابع: التأمين والإنهاء"),
    P("يدفع الطرف الثاني مبلغ تأمين قدره 37,000 درهم (أجرة شهرين) يُردّ عند انتهاء العقد. لكل طرف إنهاء العقد "
      "بإشعار كتابي مدته 60 يومًا. غرامة التأخير 2% من الدفعة المتأخرة بعد 7 أيام من تاريخ الاستحقاق."),
])

LETTER = Doc("LT-2026-0231", "PAYMENT REMINDER LETTER", "FIN", "ar",
    "Arabic official letter: June 2026 rent 19,240 unpaid, 2% late fee 384.80, total 19,624.80 by 15 June 2026", [
    H("خطاب تذكير بسداد الأجرة"),
    P("التاريخ: 8 يونيو 2026"),
    P("السادة / شركة مروة للخدمات اللوجستية ذ.م.م المحترمين"),
    P("تحية طيبة وبعد،"),
    P("الموضوع: دفعة إيجار شهر يونيو 2026 للمستودع رقم 14"),
    P("نفيدكم بأنه لم يصلنا حتى تاريخه سداد دفعة الإيجار المستحقة في 1 يونيو 2026 والبالغة 19,240.00 درهم، "
      "وذلك بموجب عقد الإيجار رقم LS-2025-0092."),
    P("وعملًا بأحكام العقد تُضاف غرامة تأخير نسبتها 2% (384.80 درهم) إذا لم يتم السداد قبل 15 يونيو 2026، "
      "ليصبح المبلغ المطلوب 19,624.80 درهم."),
    P("للاستفسار يرجى التواصل مع قسم الحسابات على الرقم الداخلي 305."),
    P("وتفضلوا بقبول فائق الاحترام،"),
    P("فيصل الزعابي، مدير الأملاك، شركة النخيل للعقارات ذ.م.م"),
])

AR_INVOICE = Doc("INV-AR-2026-063", "MAINTENANCE SERVICES INVOICE", "FIN", "ar",
    "Arabic invoice (DOCX): maintenance services, subtotal 8,950, VAT 447.50, total 9,397.50, due 24 June 2026", [
    H("فاتورة خدمات صيانة"),
    P("التاريخ: 25 مايو 2026"),
    P("البائع: مؤسسة الواحة للصيانة. المشتري: شركة مروة للخدمات اللوجستية ذ.م.م."),
    P("موعد السداد: خلال 30 يومًا من تاريخ الفاتورة، أي في موعد أقصاه 24 يونيو 2026."),
    T(["البيان", "الكمية", "سعر الوحدة (درهم)", "الإجمالي (درهم)"], [
        ["صيانة رافعة شوكية", "3", "1,200.00", "3,600.00"],
        ["فحص نظام الإطفاء", "1", "2,750.00", "2,750.00"],
        ["تنظيف المستودع", "4", "650.00", "2,600.00"],
        ["المجموع الفرعي", "", "", "8,950.00"],
        ["ضريبة القيمة المضافة 5%", "", "", "447.50"],
        ["الإجمالي المستحق", "", "", "9,397.50"]], foot=3),
    P("تُسدَّد المبالغ بالتحويل المصرفي إلى حساب المؤسسة المذكور في عقد الصيانة السنوي."),
])

# ---------------------------------------------------------------- FINANCE, mixed
TAX_INV = Doc("TI-2026-2210", "TAX INVOICE", "FIN", "mixed",
    "Bilingual invoice, English and Arabic on the same lines: total 11,445.00 incl. VAT 5%", [
    P("Seller: Zahra Tech Trading LLC (البائع: زهرة تك للتجارة ذ.م.م)"),
    P("Buyer: Marwa Logistics LLC (المشتري: شركة مروة للخدمات اللوجستية ذ.م.م)"),
    P("Date: 2 June 2026 (التاريخ: 2 يونيو 2026)"),
    P("Tax registration no.: 100234567800003 (الرقم الضريبي: 100234567800003)"),
    P("Payment terms: 14 days (شروط الدفع: 14 يومًا)"),
    T(["Code / الرمز", "Description / الوصف", "Qty / الكمية", "Unit price / السعر", "Amount / المبلغ"], [
        ["SC-110", "Barcode scanner / ماسح باركود", "10", "420.00", "4,200.00"],
        ["PR-220", "Label printer / طابعة ملصقات", "4", "1,350.00", "5,400.00"],
        ["LB-330", "Thermal labels roll / رول ملصقات حرارية", "200", "6.50", "1,300.00"],
        ["", "Subtotal / المجموع الفرعي", "", "", "10,900.00"],
        ["", "VAT 5% / الضريبة", "", "", "545.00"],
        ["", "Total / الإجمالي (AED)", "", "", "11,445.00"]], foot=3, rtl=False),
])

SCHEDULE = Doc("PS-2026-014", "PAYMENT SCHEDULE", "FIN", "mixed",
    "English table with Arabic payee names: three instalments, total AED 40,082.50, 2% reserve 801.65", [
    P("Approved by Omar Haddad, Finance Director, on 5 June 2026. Budget code: BC-4410. Currency: AED."),
    T(["No.", "Due date", "Payee", "Reference", "Amount", "Status"], [
        ["1", "15 June 2026", "زهرة تك للتجارة ذ.م.م", "TI-2026-2210", "11,445.00", "Paid"],
        ["2", "24 June 2026", "مؤسسة الواحة للصيانة", "INV-AR-2026-063", "9,397.50", "Pending"],
        ["3", "1 July 2026", "شركة النخيل للعقارات ذ.م.م", "LS-2025-0092", "19,240.00", "Scheduled"],
        ["", "Total", "", "", "40,082.50", ""]], foot=1, rtl=False),
    P("Contingency reserve: 2% of the total, AED 801.65, held under budget code BC-4410-R."),
    P("No single instalment exceeds AED 25,000."),
])

PO = Doc("PO-2026-0507", "PURCHASE ORDER", "FIN", "mixed",
    "Arabic order (DOCX) with English product codes and Western digits: total 5,770.00, 3% discount 173.10", [
    H("أمر شراء رقم PO-2026-0507"),
    P("التاريخ: 7 يونيو 2026"),
    P("إلى: زهرة تك للتجارة ذ.م.م. من: شركة مروة للخدمات اللوجستية ذ.م.م."),
    P("يرجى توريد الأصناف التالية وفق عرض السعر QT-2026-118، على أن يتم التسليم في المستودع رقم 14 قبل 25 يونيو 2026."),
    T(["الرمز", "الوصف", "الكمية", "سعر الوحدة (AED)", "الإجمالي (AED)"], [
        ["SC-110", "ماسح باركود", "6", "420.00", "2,520.00"],
        ["LB-330", "رول ملصقات حرارية", "500", "6.50", "3,250.00"],
        ["المجموع", "", "", "", "5,770.00"]], foot=1),
    P("شروط الدفع: 30 يومًا من تاريخ استلام البضاعة، مع خصم 3% (173.10 AED) عند السداد خلال 10 أيام."),
    P("المسؤولة عن الطلب: سلمى رحمن، مشرفة المشتريات."),
])

BUDGET = Doc("BM-2026-Q3", "BUDGET MEMO", "FIN", "mixed",
    "Plain-text Arabic memo with Arabic-Indic digits: Q3 2026 budget 450,000 split 30/40/25/5%", [
    H("مذكرة ميزانية الربع الثالث ٢٠٢٦"),
    P("التاريخ: ٢٨ يونيو ٢٠٢٦"),
    P("الميزانية المعتمدة للربع الثالث من عام ٢٠٢٦ هي ٤٥٠٬٠٠٠٫٠٠ درهم، وتُوزَّع على البنود التالية:"),
    T(["البند", "النسبة", "المبلغ (درهم)"], [
        ["الصيانة", "٣٠٪", "١٣٥٬٠٠٠٫٠٠"],
        ["تقنية المعلومات", "٤٠٪", "١٨٠٬٠٠٠٫٠٠"],
        ["اللوجستيات", "٢٥٪", "١١٢٬٥٠٠٫٠٠"],
        ["احتياطي", "٥٪", "٢٢٬٥٠٠٫٠٠"],
        ["الإجمالي", "١٠٠٪", "٤٥٠٬٠٠٠٫٠٠"]], foot=1),
    P("وافق على الميزانية عمر حداد، المدير المالي، بتاريخ ٣٠ يونيو ٢٠٢٦. تبدأ الميزانية في ١ يوليو ٢٠٢٦."),
])

# ---------------------------------------------------------------- HR, English
PAYROLL = Doc("PAY-2026-04", "PAYROLL SUMMARY - APRIL 2026", "HR", "en",
    "Payroll summary: 27 daily-paid staff, gross 43,700.00, deductions 5%, net 41,515.00, paid 12 May 2026", [
    P("Daily-paid workforce of Marwa Logistics LLC. Pay period: 1 to 30 April 2026. Amounts in AED."),
    T(["Department", "Headcount", "Gross pay", "Deductions", "Net pay"], [
        ["Operations drivers", "14", "24,500.00", "1,225.00", "23,275.00"],
        ["Dispatch", "5", "9,000.00", "450.00", "8,550.00"],
        ["Warehouse", "8", "10,200.00", "510.00", "9,690.00"],
        ["Total", "27", "43,700.00", "2,185.00", "41,515.00"]], foot=1),
    P("Deductions are 5% of gross pay (pension and insurance contribution) for every department."),
    P("Payment was made by bank transfer on 12 May 2026."),
    P("Prepared by Mona Tarek, HR Payroll Officer."),
])

LEAVE = Doc("HR-POL-012", "ANNUAL LEAVE POLICY", "HR", "en",
    "Leave policy: 30 calendar days, carry-over 10 days, 14 days notice, sick leave pay bands, overtime 1.25x / 1.5x", [
    P("Effective 1 January 2026. Applies to all employees after the 6-month probation period."),
    H("1. Annual leave"),
    P("Each employee has 30 calendar days of paid annual leave per year. Up to 10 unused days may be carried over to "
      "the next year. Leave requests must be made at least 14 days before the first day of leave."),
    H("2. Sick leave"),
    T(["Sick days in a year", "Pay"], [
        ["Days 1 to 15", "Full pay"],
        ["Days 16 to 45", "Half pay"],
        ["Days 46 to 90", "Unpaid"]]),
    H("3. Overtime"),
    P("Overtime is paid at 1.25 times the normal hourly rate on weekdays and 1.5 times on rest days. "
      "Overtime needs written approval from the line manager."),
])

OFFER = Doc("OFR-2026-031", "EMPLOYMENT OFFER LETTER", "HR", "en",
    "Offer letter (DOCX): Khalid Mansour, Warehouse Supervisor, total AED 8,400/month, starts 1 July 2026", [
    P("Date: 3 June 2026"),
    P("To: Mr Khalid Mansour"),
    P("Dear Mr Mansour, we are pleased to offer you the position of Warehouse Supervisor at Marwa Logistics LLC, "
      "starting on 1 July 2026."),
    T(["Monthly pay", "Amount (AED)"], [
        ["Basic salary", "6,200.00"],
        ["Housing allowance", "1,800.00"],
        ["Transport allowance", "400.00"],
        ["Total monthly pay", "8,400.00"]], foot=1),
    P("The probation period is 6 months. After probation, the notice period is 30 days. Annual leave is 30 calendar days."),
    P("Please confirm your acceptance by 12 June 2026."),
    P("Tariq Younis, HR Manager."),
])

# ---------------------------------------------------------------- HR, Arabic
CIRCULAR = Doc("HRC-2026-018", "HR CIRCULAR", "HR", "ar",
    "Arabic circular: summer hours 15 June to 15 September 2026, midday outdoor ban 12:30 to 15:00, overtime 125%", [
    H("تعميم رقم 18 لسنة 2026 بشأن ساعات الدوام الصيفي"),
    P("التاريخ: 1 يونيو 2026"),
    P("إلى: جميع موظفي شركة مروة للخدمات اللوجستية"),
    P("تعلن إدارة الموارد البشرية أنه اعتبارًا من 15 يونيو 2026 وحتى 15 سبتمبر 2026 يُعمل بساعات الدوام "
      "الصيفي الموضحة في الجدول التالي:"),
    T(["الفئة", "أيام الدوام", "ساعات الدوام", "عدد الساعات"], [
        ["المكاتب", "الاثنين إلى الخميس", "7:30 صباحًا إلى 3:30 مساءً", "8"],
        ["المكاتب", "الجمعة", "7:30 صباحًا إلى 12:00 ظهرًا", "4.5"],
        ["العاملون في الموقع", "الاثنين إلى السبت", "6:00 صباحًا إلى 12:00 ظهرًا", "6"]]),
    P("يُمنع العمل في الأماكن المكشوفة بين الساعة 12:30 ظهرًا والساعة 3:00 عصرًا."),
    P("لا يُعدّ ما يزيد على هذه الساعات عملًا إضافيًا إلا بموافقة كتابية من المدير المباشر، ويُدفع بنسبة 125% "
      "من الأجر الاعتيادي."),
    P("للاستفسار يرجى الاتصال بإدارة الموارد البشرية على الرقم الداخلي 214."),
])

CERT = Doc("EC-2026-077", "EMPLOYMENT CERTIFICATE", "HR", "ar",
    "Arabic employment certificate: Yasser Al Haddad, transport supervisor since 3 March 2019, salary 9,750", [
    H("شهادة عمل"),
    P("التاريخ: 20 مايو 2026"),
    P("إلى من يهمه الأمر،"),
    P("تشهد شركة مروة للخدمات اللوجستية ذ.م.م بأن السيد ياسر الحداد يعمل لديها منذ 3 مارس 2019 بوظيفة مشرف نقل، "
      "وهو على رأس عمله حتى تاريخ إصدار هذه الشهادة."),
    P("ويبلغ راتبه الشهري الإجمالي 9,750 درهم، موزعًا كما يلي:"),
    T(["البند", "المبلغ (درهم)"], [
        ["الراتب الأساسي", "6,500.00"],
        ["بدل السكن", "2,200.00"],
        ["بدل المواصلات", "1,050.00"],
        ["الإجمالي", "9,750.00"]], foot=1),
    P("أُعطيت هذه الشهادة بناءً على طلبه دون أدنى مسؤولية على الشركة تجاه الغير."),
    P("مدير الموارد البشرية: طارق يونس"),
])

LEAVE_NOTICE = Doc("LV-2026-142", "LEAVE APPROVAL NOTICE", "HR", "ar",
    "Arabic leave approval (DOCX): annual leave 6 to 24 July 2026, 19 days, balance 24 before and 5 after", [
    H("إشعار الموافقة على إجازة"),
    P("التاريخ: 28 يونيو 2026"),
    P("وافقت إدارة الموارد البشرية على طلب الإجازة المبيّن بياناته في الجدول التالي:"),
    T(["البند", "التفاصيل"], [
        ["الموظف", "ياسر الحداد"],
        ["نوع الإجازة", "إجازة سنوية"],
        ["تاريخ البداية", "6 يوليو 2026"],
        ["تاريخ النهاية", "24 يوليو 2026"],
        ["عدد الأيام", "19 يومًا تقويميًا"],
        ["الرصيد قبل الإجازة", "24 يومًا"],
        ["الرصيد بعد الإجازة", "5 أيام"],
        ["تاريخ العودة إلى العمل", "27 يوليو 2026"]]),
    P("اعتمد الطلب: طارق يونس، مدير الموارد البشرية."),
])

TRAINING = Doc("TR-2026-009", "TRAINING NOTICE", "HR", "ar",
    "Plain-text Arabic notice: safety course 21 June 2026, 25 seats, register by 14 June, pass mark 70%", [
    H("إعلان دورة تدريبية: السلامة المهنية في المستودعات"),
    P("تعلن إدارة الموارد البشرية عن دورة السلامة المهنية في المستودعات، وتفاصيلها كما يلي:"),
    T(["البند", "التفاصيل"], [
        ["تاريخ الدورة", "21 يونيو 2026"],
        ["الوقت", "من 9:00 صباحًا إلى 1:00 ظهرًا"],
        ["المكان", "القاعة 2"],
        ["عدد المقاعد", "25"],
        ["آخر موعد للتسجيل", "14 يونيو 2026"],
        ["درجة النجاح", "70%"],
        ["المدربة", "الدكتورة هالة سمير"]]),
    P("الحضور إلزامي لمشرفي المستودعات والسائقين."),
])

# ---------------------------------------------------------------- HR, mixed
CONTRACT = Doc("EMP-2026-044", "EMPLOYMENT CONTRACT EXTRACT", "HR", "mixed",
    "Bilingual contract extract: Nadia Farouk, Accountant, AED 12,500/month, starts 15 August 2026, probation 6 months", [
    P("Employer: Marwa Logistics LLC (صاحب العمل: شركة مروة للخدمات اللوجستية ذ.م.م)"),
    P("Employee: Nadia Farouk (الموظفة: نادية فاروق)"),
    T(["Term / البند", "Details / التفاصيل"], [
        ["Job title / المسمى الوظيفي", "Accountant / محاسبة"],
        ["Start date / تاريخ المباشرة", "15 August 2026 / 15 أغسطس 2026"],
        ["Monthly salary / الراتب الشهري", "AED 12,500 / 12,500 درهم"],
        ["Probation / فترة التجربة", "6 months / 6 أشهر"],
        ["Notice period / مدة الإشعار", "30 days / 30 يومًا"],
        ["Annual leave / الإجازة السنوية", "30 calendar days / 30 يومًا تقويميًا"],
        ["Working hours / ساعات العمل", "8 hours per day / 8 ساعات يوميًا"]], rtl=False),
    P("1. Confidentiality: the employee shall not disclose company information."),
    P("البند 1، السرية: يلتزم الموظف بعدم إفشاء معلومات الشركة."),
    P("2. Termination: either party may end this contract with the notice period above."),
    P("البند 2، الإنهاء: يجوز لأي من الطرفين إنهاء العقد بمراعاة مدة الإشعار المذكورة أعلاه."),
    P("Signed: Tariq Younis, HR Manager (وقّع: طارق يونس، مدير الموارد البشرية)"),
])

ATTEND = Doc("AS-2026-05", "ATTENDANCE SUMMARY", "HR", "mixed",
    "Arabic report with Arabic-Indic digits: May 2026, 21 working days, overall attendance 95.2%, 31 late, 7 absences", [
    H("ملخص الحضور والانصراف لشهر مايو ٢٠٢٦"),
    P("عدد أيام العمل في الشهر: ٢١ يومًا. حد التنبيه لنسبة الحضور: ٩٣٪."),
    T(["القسم", "عدد الموظفين", "نسبة الحضور", "حالات التأخر", "أيام الغياب"], [
        ["العمليات", "١٤", "٩٦٫٢٪", "١٢", "٣"],
        ["الإرسال", "٥", "٩٨٫١٪", "٢", "١"],
        ["المستودع", "٨", "٩١٫٥٪", "١٧", "٣"],
        ["الإجمالي", "٢٧", "٩٥٫٢٪", "٣١", "٧"]], foot=1),
    P("أعلى نسبة حضور في قسم الإرسال، وأدنى نسبة في قسم المستودع، وهو دون حد التنبيه."),
])

ROSTER = Doc("TA-2026-021", "TRAINING ATTENDANCE", "HR", "mixed",
    "English table with Arabic names (DOCX): safety course 21 June 2026, session 1, pass mark 70, average 78.5", [
    P("Course: Warehouse Safety, session 1 of 4. Date: 21 June 2026. Pass mark: 70%."),
    T(["No.", "Name", "Department", "Attendance", "Score (%)"], [
        ["1", "ياسر الحداد", "Operations", "Present", "82"],
        ["2", "منى طارق", "Dispatch", "Present", "91"],
        ["3", "هند الشامسي", "Warehouse", "Present", "64"],
        ["4", "كريم البنا", "Warehouse", "Present", "76"],
        ["5", "فاطمة النقبي", "Dispatch", "Present", "88"],
        ["6", "بلال سعيد", "Operations", "Present", "70"]], rtl=False),
    P("Result: 5 of 6 passed. Average score: 78.5%. Resit for the one failed attendee: 5 July 2026."),
])

# (dossier id, department, language group, [(doc, format)]); scans of one dossier go in one file, in order.
DOSSIERS = [
    ("FIN-C90-S1-F0001", "FIN", "en", "pdf", [(SUPPLY, "scan"), (INVOICE, "scan"), (BANK, "docx"), (EXPENSE, "txt")]),
    ("FIN-C90-S1-F0002", "FIN", "ar", "pdf", [(LEASE, "scan"), (LETTER, "scan"), (AR_INVOICE, "docx")]),
    ("FIN-C91-S1-F0003", "FIN", "mixed", "tif", [(TAX_INV, "scan"), (SCHEDULE, "scan"), (PO, "docx"), (BUDGET, "txt")]),
    ("HR-C90-S1-F0001", "HR", "en", "pdf", [(PAYROLL, "scan"), (LEAVE, "scan"), (OFFER, "docx")]),
    ("HR-C90-S1-F0002", "HR", "ar", "pdf", [(CIRCULAR, "scan"), (CERT, "scan"), (LEAVE_NOTICE, "docx"), (TRAINING, "txt")]),
    ("HR-C91-S1-F0003", "HR", "mixed", "tif", [(CONTRACT, "scan"), (ATTEND, "scan"), (ROSTER, "docx")]),
]
