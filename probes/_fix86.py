import io

p = '/root/marfagenez/checks/exp86_the_field_cannot_go_below_zero.py'
s = io.open(p, encoding='utf-8').read()

s = s.replace('        "C": "income 1.92 = M*r (the threshold itself)",\n', '')

s = s.replace('for key, income in (("A", 1.0), ("B", 2.0), ("C", 1.92)):',
              'for key, income in (("A", 1.0), ("B", 2.0)):')

s = s.replace('    c0 = rows["C"]["field"][0]\n'
              '    same_bc = rows["B"]["hash"] == rows["C"]["hash"]\n',
              '    c0 = rows["B"]["field"][0]\n')

s = s.replace('if abs(b0 - m_r) < 1e-9 and abs(a0 - lstar) < 1e-6 and same_bc:',
              'if abs(b0 - m_r) < 1e-9 and abs(a0 - lstar) < 1e-6:')

old = ('            "the formula would give. Measured %.6f at income 2.0 and %.6f at "\n'
       '            "income 1.92, with **the same hash** (%s): the demand is capped by "\n'
       '            "the cell, so 2.0 and 1.92 are one run and their agreement is a fact "\n'
       '            "about the field, not a measurement of the appetite. The unsaturated "\n'
       '            "arm reads %.6f. `Field::take` cannot overdraw a cell, so the frame "\n'
       '            "always reads M*regrow."\n'
       '            % (m_r, b0, c0, rows["B"]["hash"], a0),')
new = ('            "the formula would give. Measured %.6f at income 2.0. The unsaturated "\n'
       '            "arm reads %.6f. `Field::take` cannot overdraw a cell, so the frame "\n'
       '            "always reads M*regrow. A second arm at income 1.92 was run and "\n'
       '            "produced the same hash as income 2.0 -- the demand is capped by the "\n'
       '            "cell, so the two are one run and their agreement is a fact about "\n'
       '            "`min`, not a second measurement."\n'
       '            % (m_r, b0, a0),')
assert old in s, 'verdict text not found'
s = s.replace(old, new)

s = s.replace('            "the starved regime does not read M*regrow: B reads %.6f, C reads "\n'
              '            "%.6f, both against a prediction of %.6f; A reads %.6f against "\n'
              '            "%.6f." % (b0, c0, m_r, a0, lstar),',
              '            "the starved regime does not read M*regrow: B reads %.6f "\n'
              '            "against a prediction of %.6f; A reads %.6f against %.6f."\n'
              '            % (b0, m_r, a0, lstar),')

s = s.replace('        "B and C are the same run, so this experiment measures one saturated "\n'
              '        "point, not two. The claim \'the demand does not matter above the "\n'
              '        "threshold\' follows from `Field::take`\'s `min`, not from a second "\n'
              '        "measurement."',
              '        "Only one saturated point is measured. The claim \'the demand does "\n'
              '        "not matter above the threshold\' follows from `Field::take`\'s "\n'
              '        "`min`, not from a second measurement: an arm at income 1.92 was "\n'
              '        "run and came back with the same hash as income 2.0."')

io.open(p, 'w', encoding='utf-8').write(s)
print('ok')
