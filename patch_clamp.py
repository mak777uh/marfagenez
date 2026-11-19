import pathlib

p = pathlib.Path('/root/marfagenez/core/src/organ.rs')
s = p.read_text(encoding='utf-8')

old = """        let done = (u * gate).min(missing).min(affordable).max(0.0);
        *energy = (*energy - done * self.cost).max(0.0);
        self.q = (self.q + done).min(1.0);
        done"""
assert s.count(old) == 1

new = """        let done = (u * gate).min(missing).min(affordable).max(0.0);
        *energy = (*energy - done * self.cost).max(0.0);
        self.q = (self.q + done).min(1.0);
        // A repair that covers the whole deficit makes the part WHOLE, not merely close to whole. Without this clamp a
        // rounding residue survives, and because the gate is a product along the chain the residue compounds: a
        // sixteen-part chain then starves its last part although every part in front reads 1.0000 (FINDING-285).
        if self.q >= 1.0 - 1e-12 {
            self.q = 1.0;
        }
        done"""

p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('whole-part clamp added')
