import sys
p = '/root/marfagenez/core/src/life.rs'
s = open(p, encoding='utf-8').read()
s = s.replace('assert_eq!(poor.energy, 0.3,', 'assert_eq!(poor.energy(), 0.3,')
s = s.replace('let before = o.energy;', 'let before = o.energy();')
s = s.replace('assert_eq!(o.energy, before,', 'assert_eq!(o.energy(), before,')
s = s.replace('after_step[0].last_direction', 'after_step[0].direction')
open(p, 'w', encoding='utf-8').write(s)
print('patched')
