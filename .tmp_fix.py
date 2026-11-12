import io
L='/root/marfagenez/laws/Medium/Field.lean'
W='/mnt/c/Users/Admin/Documents/Qoder/2026-10-18/82ab86cd/marfagenez/laws/Medium/Field.lean'
s=io.open(L,encoding='utf-8').read()
old='''theorem more_taken_lower {M r t₁ t₂ : ℝ} (hr : 0 < r) (hr1 : r ≤ 1) (h : t₁ < t₂) :'''
new='''theorem more_taken_lower {M r t₁ t₂ : ℝ} (hr : 0 < r) (hr1 : r < 1) (h : t₁ < t₂) :'''
assert old in s, 'A'
s=s.replace(old,new)
old2='''  have hpos : 0 < 1 - r := sub_pos.mpr hr1
'''
new2='''  have hpos : 0 < 1 - r := by linarith
'''
assert old2 in s, 'B'
s=s.replace(old2,new2)
io.open(L,'w',encoding='utf-8').write(s)
io.open(W,'w',encoding='utf-8').write(s)
print('ok')
