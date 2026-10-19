"""兼容旧命令：python build_cards.py 现在等同 python build_site.py。

题库与课程的实际组装、教材依据校验都在 build_site.py 里。
"""

from build_site import main

if __name__ == "__main__":
    raise SystemExit(main())
