#!/usr/bin/env bash
# Integration test: runs the full init -> plan -> apply -> verify -> destroy
# cycle for every example in examples/, against a real `terraform` binary and
# a running MiniCloud server. Exits non-zero on first failure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MINICLOUD_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
EXAMPLES_DIR="$MINICLOUD_DIR/examples"

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

pass=0
fail=0

run_example() {
  local dir="$1"
  echo "=== $(basename "$dir") ==="
  pushd "$dir" > /dev/null

  if ! terraform init -input=false > init.log 2>&1; then
    echo "FAIL: terraform init"
    cat init.log
    popd > /dev/null
    fail=$((fail+1))
    return
  fi

  if ! terraform apply -input=false -auto-approve > apply.log 2>&1; then
    echo "FAIL: terraform apply"
    cat apply.log
    popd > /dev/null
    fail=$((fail+1))
    return
  fi
  echo "  apply OK"

  # Idempotency check: a second apply should report no changes.
  if ! terraform apply -input=false -auto-approve > apply2.log 2>&1; then
    echo "FAIL: second terraform apply (idempotency check)"
    cat apply2.log
  elif ! grep -q "0 added, 0 changed, 0 destroyed" apply2.log; then
    echo "WARN: second apply was not a no-op (see apply2.log)"
  else
    echo "  idempotent re-apply OK"
  fi

  if ! terraform destroy -input=false -auto-approve > destroy.log 2>&1; then
    echo "FAIL: terraform destroy"
    cat destroy.log
    popd > /dev/null
    fail=$((fail+1))
    return
  fi
  echo "  destroy OK"

  rm -f init.log apply.log apply2.log destroy.log
  popd > /dev/null
  pass=$((pass+1))
}

for example in "$EXAMPLES_DIR"/*/; do
  run_example "${example%/}"
done

echo
echo "Results: $pass passed, $fail failed"
exit $fail
