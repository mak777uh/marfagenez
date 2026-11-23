#!/bin/bash
cd /root/marfagenez || exit 1
python3 _dip26_imperfect.py 2>&1 | head -120
