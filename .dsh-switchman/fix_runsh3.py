import io

p = "run.sh"
s = io.open(p, encoding="utf-8").read()

# 1. Drop the `models` target from `all`: the three simulation scripts take
#    ~25 minutes each, which turns `run.sh all` into an hour-long job.
old_all = """    do_exp    || RC=$?
    do_models || RC=$?
    do_claims || RC=$?"""
new_all = """    do_exp    || RC=$?
    do_claims || RC=$?"""
assert s.count(old_all) == 1
s = s.replace(old_all, new_all, 1)

# 2. Note in the function why it is not part of `all`.
old_fn = """do_models() {
  section "Модели из laws/Medium (Budget, Corrected, Child)\""""
new_fn = """# Not part of `all`: the three simulations take ~25 minutes each.
# Run explicitly when the tables in laws/Medium/{Budget,Corrected,Child}.lean change.
do_models() {
  section "Модели из laws/Medium (Budget, Corrected, Child)\""""
assert s.count(old_fn) == 1
s = s.replace(old_fn, new_fn, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("run.sh: models removed from `all`, note added")
