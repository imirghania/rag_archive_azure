# Grounded document assistant (MVP)

A document question-answering system for Azure. People upload **dossiers** (scanned pages, Word files, text files; Arabic and English; printed and handwritten). The system reads them, files them by department, and answers questions in plain language. **Every answer cites the exact lines it came from**, and the answer is checked against those lines before it is shown. When the evidence does not support an answer, the system says so instead of guessing.

## What it does

```
upload (web app)
   |
   v   intake -> digital text / page images -> OCR (Document Intelligence) -> second reader for handwriting (vision model)
   |   -> reconcile the two readings -> segment the dossier into documents -> metadata -> chunk + embed -> index (AI Search)
   v
review: stewards and experts settle lines the system is unsure about           (web app, Review)
   |
   v
ask: question -> router -> search (hybrid, with the user's department scope) -> answer agent -> 4-layer verifier -> cited answer
```

- **Trust tiers.** Every line records how it was read (digital source, clean print, handwriting two readers agreed on, unverified). Only lines that are reliable enough can be cited.
- **Four-layer verifier.** An answer is checked for structure, the trust tier of the cited lines, numbers (every figure must appear in the evidence) and entailment (the evidence supports the claim).
- **Access by department.** A person's rights come from their app role **and** their department's own security group. The same scope filters the search index, and PostgreSQL row-level security protects the review tasks. A Finance reader never sees an HR dossier.
- **Handwriting.** Document Intelligence reads the page, a vision model reads the handwritten lines again, and a rule set compares the two. Disagreements on digits and doubtful lines go to review.
- **Evidence you can check.** Each answer links to the pages it came from, one link per document and page, and the page opens with a box around every cited line.

It runs on Azure Container Apps (13 jobs and 8 apps from one image), Service Bus, PostgreSQL, AI Search, Azure AI Foundry, Entra ID and Key Vault, all created by the deployment in this repository.

## Where to go next

| You want to                                                                                 | Read                                           |
| ------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Deploy it to Azure** and see it running                                                   | [`docs/deploy-guide.md`](docs/deploy-guide.md) |
| Understand **how it is built**, what exists today and what comes next                       | [`docs/architecture.md`](docs/architecture.md) |
| **Test the deployed system**: which dossiers to upload, what to ask, what answers to expect | [`docs/tests/`](docs/tests/README.md)          |
