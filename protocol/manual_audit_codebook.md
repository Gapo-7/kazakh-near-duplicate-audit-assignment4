# Manual audit codebook

Use this codebook for the cases selected by `src/prepare_audit.py`. The reviewer must inspect the two full texts in `results/audit_review_local.html` and record a label, error type, reason and reviewer name in `results/Appendix_B_Audit_Cases.csv`. The local HTML contains source text and must not be uploaded. The supplied CSV currently holds AI-assisted draft judgments, identified in its `reviewer` column. A bilingual student must check every decision against the local full texts and replace that reviewer field with their own name only after doing so.

## Labels

- `repeated_body`: the same substantive article or lesson text appears in both records, with only minor edits, added metadata, punctuation changes or formatting changes.
- `changed_version`: the substantive body is still mostly the same, but a page has been extended, shortened or revised. Count as a true near-duplicate for H1, and describe the version change.
- `shared_template_only`: headings, navigation, exercises or page boilerplate match, while the main content differs. Count as a false positive if an automatic method flagged the pair.
- `partial_overlap`: some substantive text matches but the documents are materially different as whole records. Count as a false positive for whole-document deduplication.
- `unrelated`: no meaningful repeated body; count as a false positive if automatically flagged.
- `uncertain`: the text is incomplete or mixed enough that no reliable decision is possible. Exclude from confirmed-duplicate counts and report separately.

An automatic pair is flagged by a method when that method's score is at least 0.80. A `repeated_body` or `changed_version` pair below 0.80 is a detected false negative in the reviewed candidate set. The audit sample is selected by high lexical similarity and cannot estimate the method's full recall. Record examples by row IDs and short non-sensitive descriptions; do not paste long source text into the public report.
