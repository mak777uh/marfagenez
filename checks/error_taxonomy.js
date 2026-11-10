// WHAT MAKES AN ERROR IMPOSSIBLE vs merely detectable?
// Let's enumerate the error classes we actually hit in this project,
// and see which ones a type system could have prevented.

const errors = [
  {
    id: 'E1',
    what: 'fold() used period 2B instead of 4B',
    caught: 'range check (values outside [-B,B])',
    couldTypesPrevent: 'YES — a `Fold` type constructed only through a checked constructor',
  },
  {
    id: 'E2',
    what: 'np.clip instead of reflect (atom at wall)',
    caught: 'comparing two models',
    couldTypesPrevent: 'YES — separate types `Clamp` and `Reflect`, no implicit conversion',
  },
  {
    id: 'E3',
    what: 'too few simulation steps to reach equilibrium',
    caught: 'nothing — looked like physics',
    couldTypesPrevent: 'PARTIAL — a `Converged` token only obtainable from a convergence test',
  },
  {
    id: 'E4',
    what: 'chi² compared to 0 instead of degrees of freedom',
    caught: 'knowing the statistic',
    couldTypesPrevent: 'YES — chi² returns a typed value carrying its dof',
  },
  {
    id: 'E5',
    what: 'theorem stated with wrong direction (max vs min)',
    caught: 'numerical check',
    couldTypesPrevent: 'NO — Lean proves what you state; types do not check intent',
  },
  {
    id: 'E6',
    what: 'theorem missing a hypothesis (k >= 0)',
    caught: 'counterexample search',
    couldTypesPrevent: 'NO — same reason',
  },
  {
    id: 'E7',
    what: 'optimisation reported from 4 noisy points',
    caught: 'seed replication',
    couldTypesPrevent: 'YES — an `Optimum` value only constructible from a replicated sweep',
  },
  {
    id: 'E8',
    what: 'mean and spread confused in the same panel',
    caught: 'reading the numbers',
    couldTypesPrevent: 'YES — `Mean` and `Spread` as distinct newtypes',
  },
];

console.log('=== ERROR CLASSES AND WHAT WOULD PREVENT THEM ===');
console.log();
for (const e of errors) {
  console.log(`${e.id}: ${e.what}`);
  console.log(`    caught by: ${e.caught}`);
  console.log(`    types prevent: ${e.couldTypesPrevent}`);
  console.log();
}

const prevent = errors.filter(e => e.couldTypesPrevent.startsWith('YES')).length;
const partial = errors.filter(e => e.couldTypesPrevent.startsWith('PARTIAL')).length;
const no = errors.filter(e => e.couldTypesPrevent.startsWith('NO')).length;

console.log(`=== SUMMARY ===`);
console.log(`types prevent outright: ${prevent}/${errors.length}`);
console.log(`types help partially:   ${partial}/${errors.length}`);
console.log(`types cannot help:      ${no}/${errors.length}`);
console.log();
console.log('=== The two that types cannot prevent ===');
console.log('E5/E6 are about INTENT: Lean proves what you state, not what you meant.');
console.log('No type system can check that you stated the right theorem.');
console.log('That gap is closed by counterexample search + numerical verification,');
console.log('which is what checks/verify_all.js does.');
console.log();
console.log('=== So the design is: ===');
console.log('1. Types make the mechanical errors impossible (E1,E2,E4,E7,E8)');
console.log('2. Tokens make unverified claims unconstructible (E3)');
console.log('3. Counterexample search + simulation covers intent (E5,E6)');
