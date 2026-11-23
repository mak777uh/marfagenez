#!/bin/bash
cd /tmp || exit 1
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
try() {
  u="$1"
  out="/tmp/probe_$(echo "$u" | md5sum | cut -c1-8).bin"
  code=$(curl -sS -o "$out" -w "%{http_code} %{size_download}" -L -A "$UA" -H "Accept: application/pdf,*/*" --max-time 90 "$u" 2>/dev/null)
  echo "$code | $(file -b "$out" | cut -c1-40) | $u"
}
try "https://mdpi-res.com/d_attachment/app/app-13-10210/article_deploy/app-13-10210.pdf"
try "https://www.mdpi.com/2076-3417/13/18/10210/pdf"
try "https://www.rairo-ro.org/articles/ro/pdf/1993/03/ro1993270303371.pdf"
try "https://projecteuclid.org/journals/brazilian-journal-of-probability-and-statistics/volume-31/issue-2/A-bivariate-optimal-replacement-policy-with-cumulative/10.1214/16-BJPS317.pdf"
try "https://www.rairo-ro.org/articles/ro/pdf/1980/03/ro1980140302491.pdf"
try "https://downloads.hindawi.com/journals/mpe/2015/528726.pdf"
try "https://doi.org/10.26408/srsp-2023-11"
