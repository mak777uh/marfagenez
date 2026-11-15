import io

p = "run.sh"
s = io.open(p, encoding="utf-8").read()

old_fn = """do_claims() {"""
new_fn = """do_models() {
  section "Модели из laws/Medium (Budget, Corrected)"
  # Таблицы в Budget.lean и Corrected.lean были помечены [UNVERIFIED]: числа не
  # воспроизводились ни одним скриптом. Здесь они воспроизводятся.
  local rc=0
  echo "--- budget_model.py ---"
  python3 checks/budget_model.py 2>&1 | tail -8 || rc=$?
  echo
  echo "--- corrected_model.py ---"
  python3 checks/corrected_model.py 2>&1 | tail -8 || rc=$?
  return $rc
}

do_claims() {"""

assert s.count(old_fn) == 1
s = s.replace(old_fn, new_fn, 1)

old_case = """  claims) do_claims || RC=$? ;;"""
new_case = """  models) do_models || RC=$? ;;
  claims) do_claims || RC=$? ;;"""
assert s.count(old_case) == 1
s = s.replace(old_case, new_case, 1)

old_all = """    do_exp    || RC=$?
    do_claims || RC=$?"""
new_all = """    do_exp    || RC=$?
    do_models || RC=$?
    do_claims || RC=$?"""
assert s.count(old_all) == 1
s = s.replace(old_all, new_all, 1)

old_usage = """    echo "usage: run.sh [all|test|lean|reach|exp|claims|export]\""""
new_usage = """    echo "usage: run.sh [all|test|lean|reach|exp|models|claims|export]\""""
assert s.count(old_usage) == 1
s = s.replace(old_usage, new_usage, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("run.sh wired: models target added")
