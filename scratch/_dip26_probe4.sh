#!/bin/bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
chk() {
  u="$1"
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1],safe=''))" "$u")
  j=$(curl -sS -L -A "$UA" --max-time 45 "http://archive.org/wayback/available?url=$enc")
  echo "AVAIL $u -> $j"
}
chk "https://www.mdpi.com/2076-3417/13/18/10210/pdf"
chk "https://downloads.hindawi.com/journals/mpe/2015/528726.pdf"
chk "https://www.rairo-ro.org/articles/ro/pdf/1993/03/ro1993270303371.pdf"
chk "https://www.rairo-ro.org/articles/ro/pdf/1980/03/ro1980140302491.pdf"
chk "https://www.mdpi.com/2227-7390/7/8/716/pdf"
