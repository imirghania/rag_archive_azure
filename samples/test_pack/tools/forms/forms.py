"""The 15 forms: layout and the exact text to write in every zone.

Fictional facts shared across forms on purpose (so cross-document questions work):
- employee Layla Mansour, EMP-20417, Procurement; supplier Sunrise Office Supplies Ltd; PO-2026-0417 for 1,230.60;
- the toner delivery was short by 2 units, so invoice INV-55120 was approved for 1,102.20 and paid by cheque.
Dates are written in several styles on purpose. All data is made up.
"""
from __future__ import annotations

from lib import L, R, Cross, Form, Sig, Tick


def f01() -> Form:
    f = Form("F01", "leave_request", "LEAVE REQUEST", "HR/LV/2026/0417", "HR", "en",
             "Employee asks for annual leave; the manager decides in the lower box.", "HR-C92-S1-F0001")
    y = f.y0 + 50
    a, b, c = f.cols([5, 3, 3])
    f.field(*a, y, "Employee name", "", "Layla Mansour")
    f.field(*b, y, "Employee ID", "", "EMP-20417")
    y = f.nx(f.field(*c, y, "Department", "", "Procurement"))
    y = f.nx(f.checks(L, R, y, "Leave type", "", [("Annual leave", ""), ("Sick leave", ""), ("Unpaid leave", ""), ("Other", "")], 0))
    a, b, c = f.cols([3, 3, 2])
    f.field(*a, y, "First day of leave", "", "12/03/2026", lang="digits")
    f.field(*b, y, "Last day of leave", "", "20 March 2026")
    y = f.nx(f.field(*c, y, "Working days", "", "7", lang="digits"))
    y = f.nx(f.field(L, R, y, "Reason for leave", "", ["Family wedding in Alexandria. I will be", "back at my desk on 23 March."], lines=2))
    a, b = f.cols([2, 3])
    f.field(*a, y, "Phone during leave", "", "+20 100 555 0143", lang="digits")
    y = f.nx(f.field(*b, y, "Work handed over to", "", "Omar Farouk (ext. 214)"))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Employee signature", "", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    y = f.nx(f.field(*b, y, "Date signed", "", "5 March 2026"))
    y += 150
    f.text(L, y, "FOR MANAGER'S USE ONLY", 36, True)
    f.d.line((L, y + 14, R, y + 14), fill=120, width=3)
    y += 80
    y = f.nx(f.checks(L, R, y, "Decision", "", [("Approved", ""), ("Not approved", "")], 0))
    f.field(L, R, y, "Manager's remarks (margin note)", "", ["Approved. Omar to cover the approvals queue."], lines=1,
            note="Margin note: write it small, to the right, as a manager would.")
    return f


def f02() -> Form:
    f = Form("F02", "expense_claim", "EXPENSE CLAIM", "FIN/EX/2026/0233", "FIN", "en",
             "Employee lists trip expenses in a line-item table and signs.", "FIN-C93-S1-F0001")
    y = f.y0 + 50
    a, b, c = f.cols([4, 3, 3])
    f.field(*a, y, "Claimant name", "", "Layla Mansour")
    f.field(*b, y, "Cost centre", "", "CC-4410")
    y = f.nx(f.field(*c, y, "Claim date", "", "3 March 2026"))
    y = f.nx(f.field(L, R, y, "Purpose of trip", "", "Supplier visit, Cairo"))
    y += 20
    y = f.table(y, "Expenses", [
        {"en": "No.", "w": 1, "static": ["1", "2", "3", "4", "5"]},
        {"en": "Date", "w": 3, "lang": "digits"},
        {"en": "Description", "w": 7},
        {"en": "Amount (EGP)", "w": 3, "lang": "digits"},
    ], [
        ["02/03/2026", "Taxi to airport", "185.50"],
        ["02/03/2026", "Hotel, 2 nights", Cross("1,240.00", "1,420.00")],
        ["03/03/2026", "Client lunch", "312.75"],
        ["03/03/2026", "Parking", "45.00"],
        [None, None, None],
    ])
    y += 75
    a, b = f.cols([3, 2])
    f.field(*b, y, "TOTAL CLAIMED (EGP)", "", "1,963.25", lang="digits")
    f.field(*a, y, "Notes (margin note)", "", ["Taxi receipt to follow."], note="Margin note, written small.")
    y = f.nx(y + 14 + 130)
    f.field(*f.cols([3, 2])[0], y, "Claimant signature", "", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    f.field(*f.cols([3, 2])[1], y, "Date signed", "", "05/03/2026", lang="digits")
    return f


def f03() -> Form:
    f = Form("F03", "purchase_order", "PURCHASE ORDER", "FIN/PO/2026/0417", "FIN", "bi",
             "Order of office supplies from one supplier; item table in English and Arabic.", "FIN-C92-S1-F0001",
             title_ar="أمر شراء")
    y = f.y0 + 50
    a, b, c = f.cols([4, 3, 3])
    f.field(*a, y, "Supplier", "المورد", "Sunrise Office Supplies Ltd")
    f.field(*b, y, "Supplier code", "رمز المورد", "SUP-3381")
    y = f.nx(f.field(*c, y, "PO number", "رقم الأمر", "PO-2026-0417"))
    a, b, c = f.cols([3, 3, 4])
    f.field(*a, y, "Order date", "تاريخ الأمر", "12/03/2026", lang="digits")
    f.field(*b, y, "Delivery date", "تاريخ التسليم", "2026-03-26", lang="digits")
    y = f.nx(f.field(*c, y, "Deliver to", "التسليم إلى", "Main warehouse, Gate 3"))
    y += 20
    y = f.table(y, "Items", [
        {"en": "No.", "ar": "م", "w": 1, "static": ["1", "2", "3", "4"]},
        {"en": "Description", "ar": "الوصف", "w": 6},
        {"en": "Qty", "ar": "الكمية", "w": 2, "lang": "digits"},
        {"en": "Unit price", "ar": "سعر الوحدة", "w": 3, "lang": "digits"},
        {"en": "Line total", "ar": "الإجمالي", "w": 3, "lang": "digits"},
    ], [
        ["A4 copier paper, 5-ream box", "40", "18.75", "750.00"],
        ["Toner cartridge HP-85", "6", Cross("62.40", "64.20"), "385.20"],
        ["Stapler, heavy duty", "12", "7.95", "95.40"],
        [None, None, None, None],
    ])
    y += 75
    a, b = f.cols([3, 2])
    f.field(*b, y, "GRAND TOTAL (EGP)", "الإجمالي الكلي", "1,230.60", lang="digits")
    y = f.checks(a[0], a[1], y, "Payment terms", "شروط الدفع",
                 [("Cash", "نقداً"), ("30 days", "٣٠ يوماً"), ("60 days", "٦٠ يوماً")], 1)
    y = f.nx(y + 40)
    a, b = f.cols([3, 2])
    f.field(*a, y, "Approved by (signature)", "اعتمد (التوقيع)", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    f.field(*b, y, "Approver name", "اسم المعتمد", "Hana Saleh")
    return f


def f04() -> Form:
    f = Form("F04", "goods_received_note", "GOODS RECEIVED NOTE", "FIN/GR/2026/0102", "FIN", "en",
             "Warehouse records what arrived against the purchase order (the toner is short).", "FIN-C92-S1-F0001")
    y = f.y0 + 50
    a, b, c = f.cols([4, 3, 3])
    f.field(*a, y, "Supplier", "", "Sunrise Office Supplies Ltd")
    f.field(*b, y, "PO number", "", "PO-2026-0417")
    y = f.nx(f.field(*c, y, "Delivery note no.", "", "DN-88213"))
    a, b, c = f.cols([3, 3, 3])
    f.field(*a, y, "Date received", "", "26 March 2026")
    f.field(*b, y, "Driver name", "", "Karim Aziz")
    y = f.nx(f.field(*c, y, "Vehicle plate", "", "KLM 7305"))
    y += 20
    y = f.table(y, "Goods", [
        {"en": "No.", "w": 1, "static": ["1", "2", "3", "4"]},
        {"en": "Description", "w": 7},
        {"en": "Qty ordered", "w": 3, "lang": "digits"},
        {"en": "Qty received", "w": 3, "lang": "digits"},
    ], [
        ["A4 copier paper, 5-ream box", "40", "40"],
        ["Toner cartridge HP-85", "6", Cross("5", "4")],
        ["Stapler, heavy duty", "12", "12"],
        [None, None, None],
    ])
    y = f.nx(y + 20)
    y = f.nx(f.checks(L, R, y, "Condition on arrival", "",
                     [("All good", ""), ("Some damaged", ""), ("Rejected", "")], 1, purpose="Condition on arrival"))
    y = f.nx(f.field(L, R, y, "Remarks", "", ["Toner: 2 boxes short. Supplier to", "deliver the balance by 2 April."], lines=2))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Received by (signature)", "", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    f.field(*b, y, "Receiver name", "", "Omar Farouk")
    return f


def f05() -> Form:
    f = Form("F05", "bank_deposit_slip", "BANK DEPOSIT SLIP", "FIN/BD/2026/0058", "FIN", "en",
             "Cash count, cheques and total of a bank deposit: an amounts-heavy form.", "FIN-C93-S1-F0001")
    y = f.y0 + 50
    a, b = f.cols([5, 3])
    f.field(*a, y, "Account name", "", "Meridian Falak Group, Operating")
    y = f.nx(f.field(*b, y, "Deposit date", "", "12.03.2026", lang="digits"))
    a, b = f.cols([3, 3])
    f.field(*a, y, "Account number", "", "4471 0093 2258", lang="digits")
    y = f.nx(f.field(*b, y, "Bank branch", "", "Port Meridian Main"))
    y = f.table(y + 10, "Cash", [
        {"en": "Note", "w": 3, "static": ["200", "100", "50", "20"]},
        {"en": "Count", "w": 3, "lang": "digits"},
        {"en": "Amount (EGP)", "w": 4, "lang": "digits"},
    ], [["12", "2,400.00"], ["8", "800.00"], ["15", "750.00"], ["30", "600.00"]])
    y = f.table(y + 70, "Cheques", [
        {"en": "Cheque no.", "w": 3, "lang": "digits"},
        {"en": "Drawn on bank", "w": 5},
        {"en": "Amount (EGP)", "w": 4, "lang": "digits"},
    ], [["004512", "Nile Delta Bank", "3,200.00"], ["004519", "Port Meridian Bank", "1,150.50"]])
    y = f.nx(y + 20)
    a, b = f.cols([5, 3])
    f.field(*b, y, "TOTAL DEPOSIT (EGP)", "", Cross("8,090.50", "8,900.50"), lang="digits")
    y = f.nx(f.field(*a, y, "Total in words", "", ["Eight thousand nine hundred and fifty (50/100)"], size=34))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Depositor signature", "", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    f.field(*b, y, "Depositor name", "", "Tarek Nabil")
    return f


def f06() -> Form:
    f = Form("F06", "petty_cash_voucher", "PETTY CASH VOUCHER", "FIN/PC/2026/0319", "FIN", "bi",
             "Small cash payment with a mixed Arabic/English purpose line.", "FIN-C93-S1-F0001", title_ar="سند صرف نثرية")
    y = f.y0 + 50
    a, b, c = f.cols([3, 4, 3])
    f.field(*a, y, "Date", "التاريخ", "12/03/2026", lang="digits")
    f.field(*b, y, "Paid to", "المدفوع إلى", "محمود عادل", lang="ar")
    y = f.nx(f.field(*c, y, "Amount (EGP)", "المبلغ", "86.50", lang="digits"))
    y = f.nx(f.field(L, R, y, "Amount in words", "المبلغ كتابة", "Eighty-six and 50/100"))
    y = f.nx(f.field(L, R, y, "Purpose", "البيان", "رسوم شحن عبر FastRoute رقم 7741", lang="en+ar"))
    a, b = f.cols([2, 3])
    f.field(*a, y, "Account code", "رمز الحساب", "6120-04", lang="digits")
    y = f.nx(f.checks(*b, y, "Category", "التصنيف", [("Office", "مكتبي"), ("Transport", "نقل"), ("Other", "أخرى")], 0))
    y = f.nx(f.field(L, R, y, "Notes (margin note)", "ملاحظات", ["Receipt no. 4417 attached."], note="Margin note."))
    a, b = f.cols([1, 1])
    f.field(*a, y, "Received by (signature)", "المستلم (التوقيع)", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    f.field(*b, y, "Approved by (signature)", "المعتمد (التوقيع)", Sig(), lines=2, kind="signature", note="Sign with a different, shorter signature.")
    return f


def f07() -> Form:
    f = Form("F07", "weekly_timesheet", "WEEKLY TIMESHEET", "HR/TS/2026/W11", "HR", "en",
             "Hours worked Monday to Friday (a weekly grid with times and totals).", "HR-C92-S1-F0001")
    y = f.y0 + 50
    a, b, c = f.cols([4, 3, 3])
    f.field(*a, y, "Employee name", "", "Layla Mansour")
    f.field(*b, y, "Employee ID", "", "EMP-20417")
    y = f.nx(f.field(*c, y, "Week ending (Friday)", "", "13/03/2026", lang="digits"))
    y = f.table(y + 10, "Timesheet", [
        {"en": "Day", "w": 3, "static": ["Mon 09/03", "Tue 10/03", "Wed 11/03", "Thu 12/03", "Fri 13/03"]},
        {"en": "Start", "w": 2, "lang": "digits"},
        {"en": "End", "w": 2, "lang": "digits"},
        {"en": "Break (min)", "w": 2, "lang": "digits"},
        {"en": "Hours", "w": 2, "lang": "digits"},
    ], [
        ["08:30", "17:00", "30", "8.0"],
        ["08:45", "17:15", "30", "8.0"],
        ["09:00", "13:00", "0", "4.0"],
        ["08:30", "18:30", "60", "9.0"],
        ["08:30", "16:30", "30", "7.5"],
    ], note={(2, "Hours"): "Wednesday is a half day."})
    y += 75
    a, b = f.cols([3, 2])
    f.field(*a, y, "Notes (margin note)", "", ["Wed: dentist, left at 13:00."], note="Margin note.")
    y = f.nx(f.field(*b, y, "TOTAL HOURS", "", "36.5", lang="digits"))
    a, b = f.cols([1, 1])
    f.field(*a, y, "Employee signature", "", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    b2 = f.field(*b, y, "Supervisor signature", "", Sig(), lines=2, kind="signature", note="Sign with a different signature.")
    y = f.nx(b2)
    f.checks(L, R, y, "Supervisor decision", "", [("Approved", ""), ("Query", "")], 0)
    return f


def f08() -> Form:
    f = Form("F08", "meeting_minutes", "MEETING MINUTES", "FIN/MM/2026/0007", "FIN", "en",
             "Budget meeting: attendees, discussion with a margin-notes box, and an action-items table.", "FIN-C94-S1-F0001")
    y = f.y0 + 50
    a, b, c = f.cols([4, 3, 2])
    f.field(*a, y, "Meeting title", "", "Q1 budget review")
    f.field(*b, y, "Date", "", "11 March 2026")
    y = f.nx(f.field(*c, y, "Time", "", "10:30", lang="digits"))
    a, b = f.cols([2, 3])
    f.field(*a, y, "Location", "", "Meeting Room 2")
    y = f.nx(f.field(*b, y, "Attendees", "", ["Hana Saleh (chair), Omar Farouk,", "Layla Mansour, Tarek Nabil"], lines=2))
    a, b = f.cols([5, 2], gap=40)
    f.field(*a, y, "Discussion", "", ["Q1 budget ceiling set at 480,000.", "Travel spend is 12% over plan.",
                                      "Vendor contracts to be re-tendered.", "Next meeting: 25/03/2026 at 10:00."], lines=4)
    y = f.nx(f.field(*b, y, "Margin notes", "", ["check with Hana", "re: travel 12%?"], lines=4, note="Margin notes box. Write small."))
    y = f.table(y + 10, "Actions", [
        {"en": "No.", "w": 1, "static": ["1", "2", "3"]},
        {"en": "Action", "w": 7},
        {"en": "Owner", "w": 4},
        {"en": "Due date", "w": 3, "lang": "digits"},
    ], [
        ["Prepare revised travel policy", "Omar Farouk", "20/03/2026"],
        ["Send tender documents", "Tarek Nabil", "5 April 2026"],
        ["Reconcile Q1 accruals", "Layla Mansour", "2026-03-31"],
    ])
    y = f.nx(y + 20)
    a, b = f.cols([3, 2])
    f.field(*a, y, "Chair signature", "", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    return f


def f09() -> Form:
    f = Form("F09", "employee_info_update", "EMPLOYEE INFORMATION UPDATE", "HR/EI/2026/0094", "HR", "bi",
             "Employee corrects contact details and next of kin; mixed Arabic/English address.", "HR-C92-S1-F0001",
             title_ar="تحديث بيانات موظف")
    y = f.y0 + 50
    a, b = f.cols([1, 1])
    f.field(*a, y, "Full name (English)", "الاسم بالإنجليزية", "Layla Mansour")
    y = f.nx(f.field(*b, y, "Full name (Arabic)", "الاسم بالعربية", "ليلى منصور", lang="ar"))
    a, b, c = f.cols([3, 3, 3])
    f.field(*a, y, "Employee ID", "الرقم الوظيفي", "EMP-20417")
    f.field(*b, y, "Date of birth", "تاريخ الميلاد", "04/09/1991", lang="digits")
    y = f.nx(f.field(*c, y, "Effective from", "ساري من", "1 April 2026"))
    a, b = f.cols([1, 1])
    f.field(*a, y, "Mobile", "الهاتف المحمول", Cross("+20 100 555 0134", "+20 100 555 0143"), lang="digits")
    y = f.nx(f.field(*b, y, "Email", "البريد الإلكتروني", "layla.mansour@example.org"))
    y = f.nx(f.field(L, R, y, "Home address", "عنوان السكن", ["Flat 12, 7 Garden Street,", "الإسكندرية - Alexandria 21500"], lines=2, lang="en+ar"))
    y = f.nx(f.checks(L, R, y, "Marital status", "الحالة الاجتماعية", [("Single", "أعزب"), ("Married", "متزوج"), ("Other", "أخرى")], 1))
    a, b, c = f.cols([3, 2, 3])
    f.field(*a, y, "Emergency contact", "جهة الاتصال", "Samir Mansour")
    f.field(*b, y, "Relation", "الصلة", "Brother")
    y = f.nx(f.field(*c, y, "Contact phone", "هاتف الاتصال", "+20 122 555 0198", lang="digits"))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Employee signature", "توقيع الموظف", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    return f


def f10() -> Form:
    f = Form("F10", "visitor_log", "VISITOR LOG", "HR/VL/2026/0311", "HR", "bi",
             "Reception log: a table of visitors with times and signatures.", "HR-C93-S1-F0001", title_ar="سجل الزوار")
    y = f.y0 + 50
    a, b, c = f.cols([3, 3, 3])
    f.field(*a, y, "Date", "التاريخ", "12 Mar 2026")
    f.field(*b, y, "Receptionist", "موظف الاستقبال", "Dina Yousef")
    y = f.nx(f.field(*c, y, "Building", "المبنى", "Block A"))
    y = f.table(y + 10, "Visitors", [
        {"en": "No.", "ar": "م", "w": 1, "static": ["1", "2", "3", "4"]},
        {"en": "Visitor", "ar": "الزائر", "w": 4},
        {"en": "Company", "ar": "الجهة", "w": 4},
        {"en": "Visiting", "ar": "يزور", "w": 3},
        {"en": "In", "ar": "دخول", "w": 2, "lang": "digits"},
        {"en": "Out", "ar": "خروج", "w": 2, "lang": "digits"},
        {"en": "Signature", "ar": "التوقيع", "w": 3, "kind": "signature"},
    ], [
        ["Nadia Fawzy", "Delta Print", "Hana Saleh", "09:05", "09:50", Sig()],
        ["Robert Collins", "BlueArch Audit", "Omar Farouk", "10:15", "12:40", Sig()],
        ["خالد إبراهيم", "شركة النور", "ليلى منصور", "11:30", "11:55", Sig()],
        [None, None, None, None, None, None],
    ], note={(0, "Signature"): "Sign small, as a visitor would.", (2, "Visitor"): "Arabic name.", (2, "Company"): "Arabic.",
             (2, "Visiting"): "Arabic."})
    y = f.nx(y + 20)
    a, b = f.cols([2, 3])
    f.field(*a, y, "Visitors today", "عدد الزوار", "3", lang="digits")
    f.checks(*b, y, "All badges returned", "إرجاع البطاقات", [("Yes", "نعم"), ("No", "لا")], 0)
    return f


def f11() -> Form:
    f = Form("F11", "vehicle_maintenance_log", "VEHICLE MAINTENANCE LOG", "FIN/VM/2026/0045", "FIN", "en",
             "Service history of one fleet vehicle with costs.", "FIN-C94-S1-F0001")
    y = f.y0 + 50
    a, b, c = f.cols([2, 3, 3])
    f.field(*a, y, "Vehicle ID", "", "FLT-07")
    f.field(*b, y, "Plate", "", "KLM 7305")
    y = f.nx(f.field(*c, y, "Odometer today (km)", "", "84,215", lang="digits"))
    y = f.table(y + 10, "Service history", [
        {"en": "Date", "w": 3, "lang": "digits"},
        {"en": "Odometer (km)", "w": 3, "lang": "digits"},
        {"en": "Service performed", "w": 6},
        {"en": "Cost (EGP)", "w": 3, "lang": "digits"},
        {"en": "Garage", "w": 4},
    ], [
        ["15/01/2026", "81,030", "Oil and filter change", "420.00", "Al Amal Garage"],
        ["2 Feb 2026", "82,540", "Front brake pads", "1,180.00", "Al Amal Garage"],
        ["02/03/2026", "84,015", "Tyre rotation", "150.00", "QuickFit Port"],
        [None, None, None, None, None],
    ])
    y = f.nx(y + 20)
    a, b, c = f.cols([2, 2, 3])
    f.field(*a, y, "TOTAL COST (EGP)", "", "1,750.00", lang="digits")
    f.field(*b, y, "Next service at (km)", "", "90,000", lang="digits")
    y = f.nx(f.field(*c, y, "Next service month", "", "June 2026"))
    y = f.nx(f.checks(L, R, y, "Roadworthy", "", [("Yes", ""), ("No", "")], 0))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Mechanic remarks (margin note)", "", ["Squeak from rear left, recheck."], note="Margin note.")
    y = f.nx(f.field(*b, y, "Mechanic name", "", "Youssef Barakat"))
    f.field(*f.cols([3, 2])[0], y, "Mechanic signature", "", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    return f


def f12() -> Form:
    f = Form("F12", "invoice_approval_sheet", "INVOICE APPROVAL SHEET", "FIN/IA/2026/0188", "FIN", "en",
             "Stamp box and three signature blocks that approve a supplier invoice.", "FIN-C92-S1-F0001")
    y = f.y0 + 50
    a, b, c = f.cols([4, 3, 3])
    f.field(*a, y, "Supplier", "", "Sunrise Office Supplies Ltd")
    f.field(*b, y, "Invoice no.", "", "INV-55120")
    y = f.nx(f.field(*c, y, "Invoice date", "", "18 March 2026"))
    a, b, c = f.cols([3, 3, 3])
    f.field(*a, y, "PO number", "", "PO-2026-0417")
    f.field(*b, y, "Invoice amount (EGP)", "", "1,102.20", lang="digits")
    y = f.nx(f.field(*c, y, "Payment due", "", "19 April 2026"))
    y = f.nx(f.checks(L, R, y, "Three-way match", "", [("Matches PO and GRN", ""), ("Variance explained below", "")], 1))
    a, b = f.cols([3, 4])
    f.field(*a, y, "Received stamp (write in capitals)", "", ["RECEIVED", "20 MAR 2026", "FINANCE PORT MERIDIAN"], lines=3,
            note="Stands in for a rubber stamp. Capitals.", size=34)
    y2 = f.field(*b, y, "Variance explanation", "", ["Toner billed for 4 units, not 6.", "2 units outstanding on the PO."], lines=3,
                 note="Hand-written explanation.")
    y = f.nx(y2)
    for (xa, xb), role, who, date, style in zip(f.cols([1, 1, 1]), ["Prepared by", "Checked by", "Approved by"],
                                                  ["Layla Mansour", "Omar Farouk", "Hana Saleh"],
                                                  ["20/03/2026", "21 Mar 2026", "2026-03-22"], [0, 1, 2]):
        f.field(xa, xb, y, f"{role} (signature)", "", Sig(), lines=2, kind="signature", note="Sign with your normal signature; use a different style for each role.")
        f.field(xa, xb, y + 14 + 240 + 60, f"{role} (name)", "", who)
        f.field(xa, xb, y + 14 + 240 + 60 + 14 + 130 + 60, f"{role} (date)", "", date, lang="digits")
    return f


def f13() -> Form:
    f = Form("F13", "cheque_request_ar", "CHEQUE REQUEST", "FIN/CQ/2026/0231", "FIN", "ar",
             "Arabic form: request to pay the supplier invoice by cheque.", "FIN-C92-S1-F0001", title_ar="طلب صرف شيك")
    y = f.y0 + 50
    a, b = f.cols([3, 2])
    f.field(*a, y, "Beneficiary", "اسم المستفيد", "صن رايز لمستلزمات المكاتب")
    y = f.nx(f.field(*b, y, "Request date", "تاريخ الطلب", "١٢/٠٣/٢٠٢٦", lang="digits"))
    a, b = f.cols([2, 3])
    f.field(*a, y, "Amount in figures (EGP)", "المبلغ بالأرقام", Cross("١٢٣٠.٦٠", "١١٠٢.٢٠"), lang="digits")
    y = f.nx(f.field(*b, y, "Amount in words", "المبلغ كتابةً", "ألف ومئة وجنيهان وعشرون قرشاً"))
    a, b = f.cols([2, 3])
    f.field(*a, y, "Invoice number", "رقم الفاتورة", "INV-55120", lang="en")
    y = f.nx(f.field(*b, y, "Reason for payment", "سبب الصرف", ["سداد فاتورة مستلزمات مكتبية", "حسب أمر الشراء PO-2026-0417"], lines=2, lang="en+ar"))
    y = f.nx(f.checks(L, R, y, "Payment method", "طريقة الصرف", [("Cheque", "شيك"), ("Bank transfer", "تحويل بنكي"), ("Cash", "نقداً")], 0))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Requested by (signature)", "طالب الصرف (التوقيع)", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    y = f.nx(f.field(*b, y, "Requester name", "اسم طالب الصرف", "عمر فاروق"))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Finance manager decision (margin note)", "ملاحظات المدير المالي", ["يُسلَّم الشيك للمورد يداً بيد"], note="Margin note.")
    y = f.nx(f.field(*b, y, "Approval date", "تاريخ الاعتماد", "٢١ مارس ٢٠٢٦"))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Finance manager (signature)", "المدير المالي (التوقيع)", Sig(), lines=2, kind="signature", note="Sign with a different signature.")
    f.field(*b, y, "Manager name", "اسم المدير المالي", "هناء صالح")
    return f


def f14() -> Form:
    f = Form("F14", "official_memorandum_ar", "OFFICIAL MEMORANDUM", "HR/MEM/2026/0072", "HR", "ar",
             "Arabic memo (printed text) with a handwritten decision box.", "HR-C93-S1-F0001", title_ar="مذكرة رسمية")
    y = f.y0 + 40
    f.text(R, y, "من: مدير الموارد البشرية", 36, False, "r")
    f.text(R, y + 62, "إلى: جميع الإدارات والموظفين", 36, False, "r")
    f.text(R, y + 124, "الموضوع: ساعات الدوام الصيفي", 36, True, "r")
    f.d.line((L, y + 160, R, y + 160), fill=120, width=3)
    y = f.para(y + 240, "تعلن إدارة الموارد البشرية أن ساعات الدوام الرسمي خلال فصل الصيف ستكون من الثامنة صباحاً حتى الثانية "
                        "بعد الظهر، من الأحد إلى الخميس. يرجى من جميع المديرين إبلاغ فرقهم وتأكيد الالتزام بهذه المواعيد. "
                        "تبقى ترتيبات العمل عن بعد خاضعة لموافقة المدير المباشر.", 36)
    y += 100
    f.text(R, y, "قرار المدير العام (بخط اليد)", 36, True, "r")
    y += 30
    a, b = f.cols([5, 2], gap=40)
    y2 = f.field(*a, y + 30, "Decision", "القرار", ["تمت الموافقة على التعميم", "يُنفَّذ اعتباراً من ٠١/٠٦/٢٠٢٦", "يُعمَّم على جميع الإدارات."], lines=3)
    f.field(*b, y + 30, "Margin note", "ملاحظة جانبية", ["للمتابعة مع", "شؤون الموظفين"], lines=3, note="Margin note, small.")
    y = f.nx(y2)
    a, b = f.cols([3, 2])
    f.field(*a, y, "Issue number", "رقم الصادر", "٢٠٢٦/٠٧٢", lang="digits")
    y = f.nx(f.field(*b, y, "Date", "التاريخ", "٢٠٢٦/٠٣/١٥", lang="digits"))
    a, b = f.cols([3, 2])
    f.field(*a, y, "General manager (signature)", "المدير العام (التوقيع)", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    f.field(*b, y, "Name", "الاسم", "هبة الشريف")
    return f


def f15() -> Form:
    f = Form("F15", "leave_request_ar", "LEAVE REQUEST", "HR/LV/2026/0418", "HR", "ar",
             "Arabic leave request with Arabic-Indic digits and a manager decision.", "HR-C93-S1-F0001", title_ar="طلب إجازة")
    y = f.y0 + 50
    a, b, c = f.cols([4, 3, 3])
    f.field(*a, y, "Employee name", "اسم الموظف", "سامي عبد الله")
    f.field(*b, y, "Employee ID", "الرقم الوظيفي", "٣١٩٥٢", lang="digits")
    y = f.nx(f.field(*c, y, "Department", "القسم", "المحاسبة"))
    y = f.nx(f.checks(L, R, y, "Leave type", "نوع الإجازة", [("Annual", "اعتيادية"), ("Sick", "مرضية"), ("Unpaid", "بدون راتب")], 1))
    a, b, c = f.cols([3, 3, 2])
    f.field(*a, y, "From", "من تاريخ", "٠٢/٠٤/٢٠٢٦", lang="digits")
    f.field(*b, y, "To", "إلى تاريخ", "٠٦/٠٤/٢٠٢٦", lang="digits")
    y = f.nx(f.field(*c, y, "Days", "عدد الأيام", "٥", lang="digits"))
    y = f.nx(f.field(L, R, y, "Reason", "السبب", ["وعكة صحية، مرفق تقرير طبي", "من مستشفى الأمل رقم 5521"], lines=2, lang="en+ar"))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Employee signature", "توقيع الموظف", Sig(), lines=2, kind="signature", note="Sign with your normal signature.")
    y = f.nx(f.field(*b, y, "Date", "التاريخ", "٢٨ مارس ٢٠٢٦"))
    y += 150
    f.text(R, y, "لاستخدام المدير فقط", 36, True, "r")
    f.d.line((L, y + 14, R, y + 14), fill=120, width=3)
    y += 80
    y = f.nx(f.checks(L, R, y, "Decision", "القرار", [("Approved", "موافق"), ("Not approved", "غير موافق")], 0))
    a, b = f.cols([3, 2])
    f.field(*a, y, "Manager remarks (margin note)", "ملاحظات المدير", ["موافق مع تمنياتنا بالشفاء"], note="Margin note.")
    f.field(*b, y, "Manager name", "اسم المدير", "هناء صالح")
    return f


FORMS = [f01, f02, f03, f04, f05, f06, f07, f08, f09, f10, f11, f12, f13, f14, f15]
