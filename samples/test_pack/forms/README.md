# Handwriting test forms (15 blank forms)

Printed forms to fill in BY HAND, then scan and upload as dossiers. All data is made up.

## Files

| File | Form | Language | Dept | Dossier | Zones | Use |
| --- | --- | --- | --- | --- | --- | --- |
| `F01_leave_request.pdf`, `F01_leave_request.png` | Leave Request | English | HR | HR-C92-S1-F0001 | 14 | Print, fill, scan, upload |
| `F02_expense_claim.pdf`, `F02_expense_claim.png` | Expense Claim | English | FIN | FIN-C93-S1-F0001 | 23 | Print, fill, scan, upload |
| `F03_purchase_order.pdf`, `F03_purchase_order.png` | Purchase Order | English + Arabic | FIN | FIN-C92-S1-F0001 | 26 | Print, fill, scan, upload |
| `F04_goods_received_note.pdf`, `F04_goods_received_note.png` | Goods Received Note | English | FIN | FIN-C92-S1-F0001 | 22 | Print, fill, scan, upload |
| `F05_bank_deposit_slip.pdf`, `F05_bank_deposit_slip.png` | Bank Deposit Slip | English | FIN | FIN-C93-S1-F0001 | 22 | Print, fill, scan, upload |
| `F06_petty_cash_voucher.pdf`, `F06_petty_cash_voucher.png` | Petty Cash Voucher | English + Arabic | FIN | FIN-C93-S1-F0001 | 10 | Print, fill, scan, upload |
| `F07_weekly_timesheet.pdf`, `F07_weekly_timesheet.png` | Weekly Timesheet | English | HR | HR-C92-S1-F0001 | 28 | Print, fill, scan, upload |
| `F08_meeting_minutes.pdf`, `F08_meeting_minutes.png` | Meeting Minutes | English | FIN | FIN-C94-S1-F0001 | 17 | Print, fill, scan, upload |
| `F09_employee_info_update.pdf`, `F09_employee_info_update.png` | Employee Information Update | English + Arabic | HR | HR-C92-S1-F0001 | 13 | Print, fill, scan, upload |
| `F10_visitor_log.pdf`, `F10_visitor_log.png` | Visitor Log | English + Arabic | HR | HR-C93-S1-F0001 | 29 | Print, fill, scan, upload |
| `F11_vehicle_maintenance_log.pdf`, `F11_vehicle_maintenance_log.png` | Vehicle Maintenance Log | English | FIN | FIN-C94-S1-F0001 | 30 | Print, fill, scan, upload |
| `F12_invoice_approval_sheet.pdf`, `F12_invoice_approval_sheet.png` | Invoice Approval Sheet | English | FIN | FIN-C92-S1-F0001 | 18 | Print, fill, scan, upload |
| `F13_cheque_request_ar.pdf`, `F13_cheque_request_ar.png` | Cheque Request | Arabic | FIN | FIN-C92-S1-F0001 | 13 | Print, fill, scan, upload |
| `F14_official_memorandum_ar.pdf`, `F14_official_memorandum_ar.png` | Official Memorandum | Arabic | HR | HR-C93-S1-F0001 | 6 | Print, fill, scan, upload |
| `F15_leave_request_ar.pdf`, `F15_leave_request_ar.png` | Leave Request | Arabic | HR | HR-C93-S1-F0001 | 13 | Print, fill, scan, upload |
| `WHAT_TO_WRITE.pdf` / `.md` | Exactly what to write in every zone, plus printing, pen, scanning, grouping and upload steps | | | | | Print next to the form. NOT uploaded |
| `answer_key.md` | What each zone should contain, to compare with what the system read | | | | | NOT uploaded |
| `questions.md` | 5 to 6 test questions per dossier with expected answers | | | | | NOT uploaded |
| `zones.json` | Zone positions at 300 dpi, same schema as `samples/templates/zones.json` plus `form` and `kind` | | | | | NOT uploaded |
| `preview_filled/PREVIEW_*.png` | Simulated handwriting, only to show what a filled form looks like | | | | | NEVER upload |

## What to print

Print the 15 forms (`F01` to `F15`, PDF or PNG) on A4, actual size (never Fit to page). Optionally print `WHAT_TO_WRITE.pdf` to keep beside you.

## What NOT to upload

`WHAT_TO_WRITE.*`, `answer_key.md`, `questions.md`, `zones.json`, anything in `preview_filled/`. Upload only your scans of the filled forms, grouped by dossier as described in `WHAT_TO_WRITE`.

Notes: every page has its own capital-letter title and `Ref:` line. The Arabic-only forms (F13, F14, F15) also carry the English capital title and Ref line, because the splitter looks for them. The local runtime cannot read real handwriting; use Azure.

## Regenerate

```bash
uv run python samples/test_pack/tools/forms/make_forms.py
```

Deterministic (the PDF bytes differ only by timestamps). Sources: `samples/test_pack/tools/forms/` (`lib.py` drawing, `forms.py` layouts and texts, `docs.py` documents, `make_forms.py`).
