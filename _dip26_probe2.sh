#!/bin/bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
try() {
  u="$1"
  out="/tmp/p2_$(echo "$u" | md5sum | cut -c1-8).bin"
  code=$(curl -sS -o "$out" -w "%{http_code} %{size_download}" -L -A "$UA" -H "Accept: application/pdf,text/html,*/*" --max-time 60 "$u" 2>/dev/null)
  echo "$code | $(file -b "$out" | cut -c1-30) | $u"
}
# Springer OA
try "https://link.springer.com/content/pdf/10.1007/978-3-319-11137-7_1.pdf"
# MDPI HTML page
try "https://www.mdpi.com/2076-3417/13/18/10210"
# HAL search API
try "https://api.archives-ouvertes.fr/search/?q=title_t:%22age%20replacement%22&fl=title_s,doiId_s,fileMain_s&rows=5&wt=json"
# SciELO
try "https://www.scielo.br/j/pope/"
# Semantic scholar api
try "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1051/ro/1993270303371?fields=title,openAccessPdf,externalIds"
# Europe PMC fulltext search
try "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%22cost%20per%20unit%20time%22%20AND%20%22replacement%22&format=json&pageSize=5&resultType=core"
