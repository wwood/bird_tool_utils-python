import sys
import types

build_manpages = types.ModuleType("build_manpages")
manpage = types.ModuleType("manpage")

class Manpage:  # minimal stub used in tests
    def __init__(self, *args, **kwargs):
        pass

    def __str__(self):
        return ""

manpage.Manpage = Manpage
build_manpages.manpage = manpage

sys.modules.setdefault("build_manpages", build_manpages)
sys.modules.setdefault("build_manpages.manpage", manpage)
