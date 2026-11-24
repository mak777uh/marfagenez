#!/bin/bash
cd /root/marfagenez || exit 1
for d in 10.1002/cnm.70212 10.1093/ismeco/ycag029 10.1098/rsif.2025.0010 10.1038/s42003-026-10531-2 10.1007/s11095-026-04129-w 10.1038/s41598-017-03341-4 10.1038/srep09190 10.3390/mi10020078 10.1038/npjbiofilms.2016.12 10.1002/bit.70095 10.1007/s00253-026-13779-0 10.1038/s41598-026-67006-x; do
  c=$(grep -rl "$d" literature/dips/reports 2>/dev/null | wc -l)
  echo "$c  $d"
done
echo "--- bio.integration reports:"
grep -rl "bio.integration" literature/dips/reports | head
