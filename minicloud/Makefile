.PHONY: build test run clean install

install:
	pip install -e .

build:
	docker build -t minicloud:latest .

run:
	minicloud start

run-background:
	minicloud start --background

stop:
	minicloud stop

status:
	minicloud status

test:
	python -m pytest tests/test_api.py -v

test-terraform:
	bash tests/test_terraform_examples.sh

clean:
	minicloud reset --force || true
	rm -f minicloud.db minicloud.log .minicloud.pid
	rm -rf examples/*/.terraform examples/*/.terraform.lock.hcl examples/*/terraform.tfstate examples/*/terraform.tfstate.backup
