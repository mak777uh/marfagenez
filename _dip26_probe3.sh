#!/bin/bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
for d in "10.1051/ro/1993270303371" "10.3390/app131810210" "10.1155/2015/528726" "10.1051/ro/1980140302491"; do
  echo "=== fatcat $d"
  curl -sS -L -A "$UA" --max-time 60 "https://api.fatcat.wiki/v0/release/lookup?doi=$d&expand=files&hide=refs,abstracts" | head -c 900
  echo
done
echo "=== S2 batch"
curl -sS -L -A "$UA" --max-time 60 "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,openAccessPdf,externalIds" -H "Content-Type: application/json" -d '{"ids":["DOI:10.1051/ro/1993270303371","DOI:10.3390/app131810210","DOI:10.1051/ro/1980140302491","DOI:10.1155/2015/528726"]}'
