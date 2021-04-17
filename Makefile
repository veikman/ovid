.PHONY = clean, wheel, test

test:
	python3 -m pytest

wheel: test
	python3 -m build
	mv dist/ovid-*.whl .

clean:
	rm -rf dist build deb_dist *.egg-info MANIFEST *.tar.* *.whl
