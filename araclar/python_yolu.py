"""Uygun bir Python ise (3.10-3.13) yolunu yazar, değilse hiçbir şey yazmaz."""
import sys

if (3, 10) <= sys.version_info[:2] <= (3, 13):
    print(sys.executable)
