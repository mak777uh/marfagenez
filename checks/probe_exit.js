// Verify that a failing check makes the process exit non-zero.
//
// The earlier version of `verify_all.js` printed FAIL and returned success, so CI
// could not see the failure. This probe plants a failure and checks the exit code.

const fs = require('fs');
const { execFileSync } = require('child_process');

const src = fs.readFileSync('checks/verify_all.js', 'utf8');
// Force the first check to fail by making its tolerance impossible.
const forced = src.replace(
  'Math.abs(sd - th) / th < 0.03',
  'Math.abs(sd - th) / th < -1'
);
if (forced === src) {
  console.error('PROBE FAILED: could not plant the defect');
  process.exit(2);
}
fs.writeFileSync('/tmp/forced_fail.js', forced);

let code = 0;
try {
  execFileSync('node', ['/tmp/forced_fail.js'], { stdio: 'pipe' });
} catch (e) {
  code = e.status;
}

if (code === 0) {
  console.error('PROBE FAILED: a failing check exited 0, CI would see green');
  process.exit(1);
}
console.log(`PROBE PASSED: a failing check exits ${code}`);
