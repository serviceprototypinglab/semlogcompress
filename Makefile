PKGDIR=`python3 -c "import sys; print(sys.path[-1])"`

all:
	@echo Type 'make install' to install into $(PKGDIR) + /usr/local/bin

install:
	@sudo cp slc slcnotify slcgrep netlogserve /usr/local/bin
	@sudo cp semlogcompress.py $(PKGDIR)
	@sudo pip3 install -r dependencies.txt
