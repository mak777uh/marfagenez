import io

p = "run.sh"
s = io.open(p, encoding="utf-8").read()

old = """  echo "--- corrected_model.py ---"
  python3 checks/corrected_model.py 2>&1 | tail -8 || rc=$?
  return $rc"""
new = """  echo "--- corrected_model.py ---"
  python3 checks/corrected_model.py 2>&1 | tail -8 || rc=$?
  echo
  echo "--- room_model.py ---"
  python3 checks/room_model.py 2>&1 | tail -8 || rc=$?
  return $rc"""
assert s.count(old) == 1
s = s.replace(old, new, 1)

old_hdr = '  section "Модели из laws/Medium (Budget, Corrected)"'
new_hdr = '  section "Модели из laws/Medium (Budget, Corrected, Child)"'
assert s.count(old_hdr) == 1
s = s.replace(old_hdr, new_hdr, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("run.sh: room_model.py wired into models")
