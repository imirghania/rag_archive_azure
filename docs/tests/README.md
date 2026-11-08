# Testing the deployed system

You have deployed the app and want to know whether it behaves. This folder tells you what to upload, who uploads it, what to ask, and what a correct answer looks like. Everything is meant to be run in the browser against the real deployment. The sample files are in `samples/dossiers/<dossier-id>` (folders `typed`, `forms`, `mixed` and `handwritten`); every path below is relative to that folder.

The files here:

- `finance.md`: the Finance dossiers, with their questions and expected answers.
- `hr.md`: the HR dossiers, their questions, and the department-isolation and role checks.
- `access-and-workflow.md`: behaviours that are not a question and an answer: who may do what, review tasks, hints, reprocessing, dossier states, and where to look when something fails.

## How to test, in six lines

1. Use one private browser window per person. Sign in as that person only in that window.
2. The first time each test user signs in, Microsoft asks them to change the generated password (and may ask for a second factor). Do that once.
3. After a user's groups change in Entra, they must sign out and sign in again, or their old token keeps the old groups.
4. Upload as the right person: Sara uploads Finance, Huda uploads HR. Anyone else is refused.
5. Ask as the right person too: Layla reads Finance, Huda reads HR. Each must see only their own department.
6. Write down what you saw next to the expected answer. A wrong number, a missing citation or an invented answer is a failure.

## The people

| Person | Role    | Departments    | May do                                                                                                                      |
| ------ | ------- | -------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Layla  | Reader  | Finance        | Ask questions about Finance documents                                                                                       |
| Sara   | Expert  | Finance        | Ask, upload Finance dossiers, settle review tasks, submit hints                                                             |
| Rana   | Steward | Finance and HR | Ask (she is also a reader in both), approve or reject hints, settle escalated review tasks, restrict who may read a dossier |
| Yousef | Admin   | none           | See dossier status, reprocess a dossier. Sees no document content and cannot ask questions                                  |
| Huda   | Expert  | HR             | Ask, upload HR dossiers, settle HR review tasks, submit HR hints                                                            |

A capability always needs two things: the role and the department's own group. A person with the right role but not the department's group gets "You are not allowed to do that."

## Upload a dossier

1. Sign in as the uploader and open **Upload**.
2. Type the **Department** (`FIN` or `HR`). The field is pre-filled with `FIN`, so Huda must change it to `HR`.
3. Leave **Mode** on **By dossier**. Bulk mode is for loose files and generates its own IDs; the tests do not use it.
4. Type the **Dossier ID**, for example `FIN-C90-S1-F0001`. The shape is department, `-C` and two digits, `-S` and one digit, `-F` and four digits, and it must start with the department you typed.
5. Choose the files listed for that dossier. Never choose a `dossier.json` (if it exists), an answer key or a questions file; `dossier.json` is refused. Allowed types are tif, tiff, pdf, doc, docx and txt, up to 500 MB each.
6. Press **Check files**. The page reads the files in your browser and tells you whether the dossier is new ("This dossier does not exist yet") or exists ("your files will replace it as revision N"). Uploading an existing ID again makes a new revision; the old one is kept until the new one is swapped in.
7. Press **Confirm and upload**. The files go up in blocks, then the page opens the upload status. It shows the upload status and, once committed, a table with the dossier, its revision and its status.
8. Wait. Typed dossiers take a minute or two; scans and handwriting take longer. The dossier is ready when its status is `completed`. `partial` means some pages could not be read but the rest is searchable.

If the dossier does not reach `completed`, look in this order:

- The upload status page: a rejected upload shows the reason (wrong type, file name, mismatch with what was announced).
- Yousef's **Admin** page: status and pages done out of total, with failed pages in red.
- The job that handles the stage that stopped. List its runs with `az containerapp job execution list -g rg-docai-dev -n job-ocr-online -o table` (other jobs: `job-intake`, `job-preprocess`, `job-digital`, `job-handwriting-online`, `job-reconcile`, `job-segment`, `job-metadata`, `job-chunk-embed`, `job-index`, `job-post-review`) and its console log through the Log Analytics workspace.
- The dead-letter queue of that stage in Service Bus. A page that failed five times is dead-lettered, and the watchdog job then marks that page `failed`.
- To try again, ask Yousef to press **Reprocess** on the dossier. It starts a new revision from the files already uploaded.

`access-and-workflow.md` has the commands and the meaning of each status.

## Ask a question and read the answer

Open **Ask** (the home page), type the question in any language, press **Ask**. Questions can be in Arabic over an English document and the other way round; that is part of the tests.

A good answer is the answer text, followed by **Sources**. Each source is one link per document and page, labelled with the document ID and the page, for example `FIN-C90-S1-F0001-r1-D02, page 1`. Under the link are the quoted lines the answer used, and a small crop of the first cited line. Click the link: you see the whole page as scanned with a box around each cited line on that page. If an answer cites two pages, there are two links.

What else you can see:

- **Not in the documents.** The text says it could not find supporting evidence in the documents you have access to. This is a pass for questions marked "not in documents". No invented value may appear.
- **Cannot be stated yet.** For a handwritten line that an expert has not verified, the answer says a handwritten note exists but its content still awaits expert verification. This is correct behaviour, not a failure.
- **Part left out.** If part of an answer could not be checked against the documents, the answer says so and leaves that part out.
- **Out of scope.** A question that is not about the documents (small talk, an unrelated task) is declined with a one-line explanation of what the system answers.
- **Expert hint.** When an answer is an abstention, experts also see an **Add expert hint** link under it.
- Thumbs up and down record feedback.

## Order to run things

1. Typed documents first (`typed/`). They are cheap, have no handwriting, and show whether the whole path works.
2. Filled forms next (`forms/`).
3. Handwriting last (`handwritten/`). Real handwriting costs an OCR call per page and a vision call per handwritten line.

Start with one dossier, check it end to end, then continue. The first Azure test, `FIN-C90-S1-F0001`, completed with 4 documents. Chat answers on Azure have not been confirmed yet, so the first question you ask is itself part of the test.

## Pass and fail checklist

- Every dossier reaches `completed` (or `partial` with a reason you understand).
- Each expected number, date and name matches, in the language asked.
- A crossed-out value is never the answer; the corrected value is.
- A "not in documents" question gets the "cannot find" answer, never a guess.
- A question about the other department's facts is refused or finds nothing, and none of the other department's values appears.
- Every answer that states a fact has Sources, and the source page shows the box on the right line.
- A person without the role or the group is refused at upload, review and hints.
- Nothing shows an error page or a stack trace.

## Open points on the test material

The sample question files and the answer keys were written before the first Azure run. Where this guide and the sample files differ, the sample documents themselves are the ground truth. Each question file here ends with its own list of open points.
