# Lixplore Exports Directory

This directory contains all exported search results organized by format.

## Export Folders:

- **bibtex/** - BibTeX format (.bib) for LaTeX citations
- **csv/** - CSV format (.csv) for Excel, Google Sheets
- **endnote_tagged/** - EndNote Tagged format (.enw) - native EndNote import
- **endnote_xml/** - EndNote XML format (.xml) - EndNote XML import
- **excel/** - Microsoft Excel format (.xlsx)
- **json/** - JSON format (.json) - structured data
- **ris/** - RIS format (.ris) - reference managers (Zotero, Mendeley)
- **xml/** - Generic XML format (.xml)

## Usage:

All exports are automatically saved to their designated folder:

```bash
lixplore -P -q "your query" -m 10 -e csv      # → csv/
lixplore -P -q "your query" -m 10 -e xlsx     # → excel/
lixplore -P -q "your query" -m 10 -e enw      # → endnote_tagged/
lixplore -P -q "your query" -m 10 -e endnote  # → endnote_xml/
```

Files are automatically organized - no manual management needed!
