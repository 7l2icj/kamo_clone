# LIBTBX_SET_DISPATCHER_NAME kamo.resolve_indexing_ambiguity
"""
(c) RIKEN 2015. All rights reserved. 
Author: Keitaro Yamashita

This software is released under the new BSD License; see LICENSE.
"""

from yamtbx.dataproc.auto.multi_merging.resolve_reindex import ReferenceBased, BrehmDiederichs, KabschSelectiveBreeding
from yamtbx.util import read_path_list
from libtbx.utils import multi_out
import iotbx.phil
import libtbx.phil
import sys
import os

master_params_str = """
lstin = None
 .type = path
 .help = list of XDS_ASCII.HKL
method = brehm_diederichs *selective_breeding reference
 .type = choice(multi=False)
 .help = Method to resolve ambiguity
logfile = "reindexing.log"
 .type = path
 .help = logfile name
nproc = 1
 .type = int
 .help = number of processors

d_min = 3
 .type = float
 .help = high resolution cutoff used in the method
min_ios = None
 .type = float
 .help = minimum I/sigma(I) cutoff used in the method
max_delta = 3
 .type = float
 .help = maximum obliquity used in determining the lattice symmetry, using a modified Le-Page algorithm.

max_cycles = 100
 .type = int(value_min=1)
 .help = Maximum number of cycles for selective_breeding algorithm.

reference_file = None
 .type = path
 .help = Only needed when method=reference
reference_label = None
 .type = str
 .help = data label of reference_file
"""

def run(params):
    log_out = multi_out()
    log_out.register("log", open(params.logfile, "w"), atexit_send_to=None)
    log_out.register("stdout", sys.stdout)

    libtbx.phil.parse(master_params_str).format(params).show(out=log_out, prefix=" ")

    xac_files = read_path_list(params.lstin, only_exists=True, err_out=log_out)

    if len(xac_files) == 0:
        print >>log_out, "No (existing) files in the list: %s" % params.lstin
        return
    
    if params.method == "brehm_diederichs":
        rb = BrehmDiederichs(xac_files, max_delta=params.max_delta,
                             d_min=params.d_min, min_ios=params.min_ios,
                             nproc=params.nproc, log_out=log_out)
    elif params.method == "selective_breeding":
        rb = KabschSelectiveBreeding(xac_files, max_delta=params.max_delta,
                                     d_min=params.d_min, min_ios=params.min_ios,
                                     nproc=params.nproc, log_out=log_out)
    elif params.method == "reference":
        rb = ReferenceBased(xac_files, params.reference_file, params.reference_label, max_delta=params.max_delta,
                            d_min=params.d_min, min_ios=params.min_ios,
                            nproc=params.nproc, log_out=log_out)
    else:
        raise "Unknown method: %s" % params.method

    if params.method == "selective_breeding":
        rb.assign_operators(max_cycle=params.max_cycles)
    else:
        rb.assign_operators()

    new_files = rb.modify_xds_ascii_files()

    lstout = os.path.splitext(os.path.basename(params.lstin))[0]+"_reindexed.lst"
    ofs = open(lstout, "w")
    ofs.write("\n".join(new_files)+"\n")
    ofs.close()
    print >>log_out, "Reindexing done. For merging, use %s instead!" % lstout

    if params.method == "brehm_diederichs":
        print >>log_out, """
CCTBX-implementation (by Richard Gildea) of the "algorithm 2" of the following paper was used.
For publication, please cite:
 Brehm, W. and Diederichs, K. Breaking the indexing ambiguity in serial crystallography.
 Acta Cryst. (2014). D70, 101-109
 http://dx.doi.org/10.1107/S1399004713025431"""
    elif params.method == "selective_breeding":
        print >>log_out, """
"Selective breeding" algorithm was used. For publication, please cite:
 Kabsch, W. Processing of X-ray snapshots from crystals in random orientations.
 Acta Cryst. (2014). D70, 2204-2216
 http://dx.doi.org/10.1107/S1399004714013534"""

# run()

def show_help():
    print """
Use this command to resolve indexing ambiguity

Case 1) Reference-based (when you have isomorphous data)
  kamo.resolve_indexing_ambiguity formerge.lst method=reference reference_file=yourdata.mtz [d_min=3]

Case 2) Using selective-breeding algorithm (when you don't have reference data)
  kamo.resolve_indexing_ambiguity formerge.lst method=selective_breeding [d_min=3]

Case 3) Using Brehm & Diederichs algorithm (when you don't have reference data)
  kamo.resolve_indexing_ambiguity formerge.lst method=brehm_diederichs [d_min=3]

You can also give min_ios= to cutoff data by I/sigma(I).
"""
    iotbx.phil.parse(master_params_str).show(prefix="  ", attributes_level=1)
    print 
# show_help()

if __name__ == "__main__":
    import sys

    if "-h" in sys.argv or "--help" in sys.argv:
        show_help()
        quit()
  
    cmdline = iotbx.phil.process_command_line(args=sys.argv[1:],
                                              master_string=master_params_str)
    params = cmdline.work.extract()
    args = cmdline.remaining_args

    for arg in args:
        if os.path.isfile(arg) and params.lstin is None:
            params.lstin = arg

    if params.lstin is None:
        show_help()
        print "Error: Give .lst of XDS_ASCII files"
        quit()

    if params.method is None:
        show_help()
        print "Error: Give method="
        quit()

    if params.method == "reference" and params.reference_file is None:
        show_help()
        print "Error: Give reference_file= when you use params.method=reference"
        quit()

    if params.method == "brehm_diederichs" and params.reference_file is not None:
        show_help()
        print "Error: You can't give reference_file= when you use params.method=brehm_diederichs"
        quit()
        
    run(params)
