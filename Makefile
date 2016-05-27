# Debian-related rules in this makefile depend on stdeb, available on PyPI.

.phony = clean, install, install_debian, package_debian, test

test:
	python3 -m unittest discover

install: test
	sudo python3 setup.py install

package_debian: test
	python3 setup.py --command-packages=stdeb.command bdist_deb
	mv deb_dist/python3-ovid_*.deb .

install_debian: test
	sudo python3 setup.py --command-packages=stdeb.command install_deb

clean:
	rm -rf dist build deb_dist MANIFEST *.tar.* *.deb

