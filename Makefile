# Debian-related rules in this makefile depend on stdeb, available on PyPI,
# and in Debian itself as python3-stdeb. The dh-python Debian package is
# also required.

.phony = clean, install, package_wheel, install_debian, package_debian, test

test:
	python3 -m unittest discover

install: test
	sudo python3 setup.py install

package_wheel: test
	python3 setup.py bdist_wheel
	mv dist/ovid-*.whl .

package_debian: test
	python3 setup.py --command-packages=stdeb.command bdist_deb
	mv deb_dist/python3-ovid_*.deb .

install_debian: test
	sudo python3 setup.py --command-packages=stdeb.command install_deb

clean:
	rm -rf dist build deb_dist *.egg-info MANIFEST *.tar.* *.deb *.whl
