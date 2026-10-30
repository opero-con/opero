# Publication uploads and body links

Publication editors choose a PDF upload, a webpage link, or both. This is a Desk display choice, inferred from existing fields; it adds no stored publication mode and does not change website destination precedence. Switching choices never clears a file or link. Populated fields stay visible.

The PDF control accepts uploads instead of asking editors to paste file URLs. Existing externally hosted PDF references remain valid. Cover uploads remain optional and separate. Private attachments continue through the existing deploy export to public website media; saving drafts does not change attachment privacy.

Body links starting with an explicit www address gain https://. Other invalid links remain rejected, with the affected text and instructions to edit or remove the link in Body. This applies to other site text fields using the same body parser as well.

The reported PUB-00008 save failure was not captured in the stored record: its body is empty. A www body link reproduces the reported validation message, but the exact unsaved value is unknown. No production record repair is included.
