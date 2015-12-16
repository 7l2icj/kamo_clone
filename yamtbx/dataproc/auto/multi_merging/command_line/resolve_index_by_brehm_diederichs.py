"""
(c) RIKEN 2015. All rights reserved. 
Author: Keitaro Yamashita

This software is released under the new BSD License; see LICENSE.
"""
from yamtbx.dataproc.auto.multi_merging.resolve_reindex import BrehmDiederichs

if __name__ == "__main__":
    import sys
    lst = sys.argv[1]
    xac_files = map(lambda x:x.strip(), open(lst))

    rb = BrehmDiederichs(xac_files, log_out=sys.stdout)
    rb.assign_operators()
    rb.modify_xds_ascii_files()
