"""
(c) RIKEN 2015. All rights reserved. 
Author: Keitaro Yamashita

This software is released under the new BSD License; see LICENSE.
"""
from yamtbx.dataproc.auto.html_report import amcharts_root
from yamtbx.util.xtal import CellConstraints
from yamtbx.dataproc.xds import xscalelp

import libtbx.phil
import libtbx.load_env
from cctbx.array_family import flex
from cctbx import sgtbx

import time
import os
import shutil

class HtmlReportMulti:
    def __init__(self, root):
        self.root = root

        jsdir = os.path.join(self.root, "js")
        shutil.copytree(libtbx.env.find_in_repositories("yamtbx/dataproc/auto/js/d3-3.5.10"), jsdir)

        self.html_head = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="%(amcharts_root)s/amcharts.js" charset="utf-8"></script>
<script src="%(amcharts_root)s/serial.js" charset="utf-8"></script>
<script src="%(amcharts_root)s/xy.js" charset="utf-8"></script>

<script>
  var toggle_show = function(obj_id) {
    var trg = document.getElementById(obj_id);
    if (trg.style.display === 'block' || trg.style.display === '')
      trg.style.display = 'none';
    else
      trg.style.display = 'block';
  }

  var toggle_show2 = function(caller, obj_id) {
    var trg = document.getElementById(obj_id);
    if (trg.style.display === 'block' || trg.style.display === '') {
      trg.style.display = 'none';
      trg.style.padding = '0px';
      caller.innerHTML= '&#x25bc;';
    } else {
      trg.style.display = '';
      trg.style.padding = '7px';
      caller.innerHTML= '&#x25b2;';
    }
  }

  var show_or_hide = function(caller_id, obj_id, flag) { 
    var trg = document.getElementById(obj_id);
    if (flag) { 
      trg.style.display = 'none';  
      trg.style.padding = '0px';   
      document.getElementById(caller_id).innerHTML= '&#x25bc;';   
    } else {    
      trg.style.display = '';      
      trg.style.padding = '7px';   
      document.getElementById(caller_id).innerHTML= '&#x25b2;';   
    }
  }
</script>

<style>
.cells_table {
    font-family: "Trebuchet MS", Arial, Helvetica, sans-serif;
    width: 100%%;
    border-collapse: collapse;
}

.cells td, .dataset_table th,
.merge td {
    font-size: 1em;
    #border: 1px solid #98bf21;
    padding: 4px 7px 4px 7px;
}

.cells th,
.merge th {
    font-size: 1.1em;
    text-align: center;
    padding: 4px;
    background-color: #A7C942;
    color: #ffffff;
}

#.cells tr.alt td {
#    color: #000000;
#    background-color: #EAF2D3;
#}

.merge tr:nth-child(4n+3),
.merge tr:nth-child(4n),
.cells tr:nth-child(odd) {
    color: #000000;
    background-color: #EAF2D3;
}
.merge tr:nth-child(4n+1),
.merge tr:nth-child(4n+2),
.cells tr:nth-child(even) {
    #color: #f8fbf1;
    background-color: #f8fbf1;
}

.node circle {
  fill: #fff;
  stroke: steelblue;
  stroke-width: 1.5px;
}

.node {
 font: 15px sans-serif;
}

.link {
  fill: none;
  stroke: #ccc;
  stroke-width: 1.5px;
}

.d3-tip {
  line-height: 1;
  font-weight: bold;
  padding: 12px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  border-radius: 2px;
}

.node--source {
  fill: #2ca02c;
}

.node--target {
  fill: #d62728;
}

.link--source,
.link--target {
  stroke-opacity: 1;
  stroke-width: 2px;
}

.link--source {
  stroke: #d62728;
}

.link--target {
  stroke: #2ca02c;
}

</style>
</head>
<body>
<h1>KAMO.MULTI_MERGE report</h1>
<div align="right">
workdir: %(wd)s<br />
created on %(cdate)s
</div>
<hr>
""" % dict(wd=self.root, cdate=time.strftime("%Y-%m-%d %H:%M:%S"), amcharts_root=amcharts_root)

        self.html_params = ""
        self.html_inputfiles = ""
        self.html_clustering = ""
        self.html_merge_results = []
        self.html_merge_plot_data = []
        self.params = None
        self.cells = None
    # __init__()

    def add_params(self, params, master_params_str):
        self.params = params
        self.html_params = """
<h2>Parameters</h2>
<a href="#" onClick="toggle_show('div-params'); return false;">Show/Hide</a>
<div id="div-params" style="display:none;">
<pre>
%s
</pre>
</div>
""" % libtbx.phil.parse(master_params_str).format(params).as_str(prefix=" ")
        self.write_html()
    # add_params()

    def add_cells_and_files(self, cells, symm_str):
        self.cells = cells
        # Table
        table_str = ""
        for idx, xac in enumerate(cells):
            cell = cells[xac]
            table_str += "<tr>\n"
            table_str += " <td>%.4d</td><td>%s</td>" % (idx+1, xac) # idx, file
            table_str += "".join(map(lambda x: "<td>%.2f</td>"%x, cell))
            table_str += "\n</tr>\n"

        # Hist
        cellconstr = CellConstraints(sgtbx.space_group_info(symm_str).group())
        show_flags = (True, not cellconstr.is_b_equal_a(), not cellconstr.is_c_equal_a_b(),
                      not cellconstr.is_angle_constrained("alpha"),
                      not cellconstr.is_angle_constrained("beta"),
                      not cellconstr.is_angle_constrained("gamma"))
        names = ("a", "b", "c", "&alpha;", "&beta;", "&gamma;")

        hist_str = ""
        label1 = ""
        for i, (name, show) in enumerate(zip(names, show_flags)):
            tmp = ""
            if i in (0,3): tmp += "<tr>"
            if show: tmp += "<th>%s</th>" % name
            if i in (2,5): tmp += "</tr>"

            if i < 3: hist_str += tmp
            else: label1 += tmp

        hist_str += "\n<tr>\n"

        for idx, (name, show) in enumerate(zip(names, show_flags)):
            if idx==3: hist_str += "</tr>" + label1 + "<tr>"
            if not show: continue
            vals = flex.double(map(lambda x: x[idx], cells.values()))
            if len(vals) == 0: continue
            nslots = max(30, int((max(vals) - min(vals)) / 0.5))
            hist = flex.histogram(vals, n_slots=nslots)
            x_vals = map(lambda i: hist.data_min() + hist.slot_width() * (i+.5), xrange(len(hist.slots())))
            y_vals = hist.slots()
            hist_str += """
<td>
<div id="chartdiv_cell%(idx)d" style="width: 500px; height: 400px;"></div>
<script>
 var chart_cell%(idx)d = AmCharts.makeChart("chartdiv_cell%(idx)d", {
    "type": "serial",
    "theme": "none",  
    "legend": {
        "useGraphSettings": true,
        "markerSize":12,
        "valueWidth":0,
        "verticalGap":0
    },
    "dataProvider": [%(data)s],
    "valueAxes": [{
        "minorGridAlpha": 0.08,
        "minorGridEnabled": true,
        "position": "top",
        "axisAlpha":0
    }],
    "graphs": [{
        "balloonText": "[[category]]: [[value]]",
        "title": "%(name)s",
        "type": "column",
        "fillAlphas": 0.8,
        "valueField": "yval"
    }],
    "rotate": false,
    "categoryField": "xval",
    "categoryAxis": {
        "gridPosition": "start",
        "title": ""
    }
});
</script>
</td>
""" % dict(idx=idx, name=name,
           data=",".join(map(lambda x: '{"xval":%.2f,"yval":%d}'%x, zip(x_vals,y_vals)))
           )

        hist_str += "</tr>"

        self.html_inputfiles = """
<h2>Input files</h2>
%d files for merging in %s symmetry

<h3>Unit cell histogram</h3>
<table>
%s
</table>

<h3>Files</h3>
<a href="#" onClick="toggle_show('div-input-files'); return false;">Show/Hide</a>
<div id="div-input-files" style="display:none;">
<table class="cells">
<tr>
 <th>idx</th> <th>file</th> <th>a</th> <th>b</th> <th>c</th> <th>&alpha;</th> <th>&beta;</th> <th>&gamma;</th>
</tr>
%s
</table>
</div>
""" % (len(cells), symm_str, hist_str, table_str)
        self.write_html()
    # add_files()

    def add_clutering_result(self, clusters, method):
        assert method in ("cc_clustering", "blend")

        if method == "cc_clustering":
            clsdat = os.path.join(self.root, "cc_clustering", "cc_cluster_summary.dat")
        else:
            clsdat = os.path.join(self.root, "blend", "blend_cluster_summary.dat")
            
        header = None
        data = ""
        for l in open(clsdat):
            if header is None and not l.startswith("#"):
                header = "".join(map(lambda x: "<th>%s</th>" % x, l.split()))
            elif header is not None:
                data += "<tr>%s</tr>" % "".join(map(lambda x: "<td>%s</td>" % x, l.split()))

        treejson = os.path.join(self.root, method, "dendro.json")
        treedata = open(treejson).read() if os.path.isfile(treejson) else ""

        cluster_descr, file_descr = [], []
        IDs_set = set()
        for vv in clusters:
            if method == "cc_clustering":
                clno, IDs, clh, cmpl, redun, acmpl, aredun = vv
                cluster_descr.append('"%s":"Cluster_%.4d (%d files)<br />ClH: %5.2f<br />Cmpl= %5.1f%%, Redun=%5.1f<br />ACmpl= %5.1f%%, ARedun=%5.1f"' % (clno, clno, len(IDs), clh, cmpl, redun, acmpl, aredun))
            else:
                clno, IDs, clh, cmpl, redun, acmpl, aredun, LCV, aLCV = vv
                cluster_descr.append('"%s":"Cluster_%.4d (%d files)<br />ClH: %5.2f, LCV: %5.2f%%, aLCV: %5.2f &Aring;<br />Cmpl= %5.1f%%, Redun=%5.1f<br />ACmpl= %5.1f%%, ARedun=%5.1f"' % (clno, clno, len(IDs), clh, LCV, aLCV, cmpl, redun, acmpl, aredun))

            IDs_set.update(IDs)

        xac_files = self.cells.keys()
        for idx in IDs_set:
            file_descr.append('%s:"%s"' % (idx, xac_files[idx-1]))

        if method == "cc_clustering":
            self.html_clustering = "<h2>CC-based clustering</h2>"
        else:
            self.html_clustering = "<h2>Cell-based clustering by BLEND</h2>"

        self.html_clustering += """
<a href="%(method)s/tree.png">See original cluster dendrogram</a>
<div id="tree-svg-div">
<script src="js/d3.min.js"></script>
<script src="js/index.js"></script>
<script type="application/json" id="treedata">%(treedata)s</script>
<script>
  
  var data = document.getElementById('treedata').innerHTML;
  root = JSON.parse(data);
  
  var merged_clusters = [%(merged_clusters)s];
  var cluster_descr = {%(cluster_descr)s};
  var file_descr = {%(file_descr)s};

  var width = 1500, height = 600;
  var cluster = d3.layout.cluster()
      .size([width-20, height-40]);

  var diagonal = d3.svg.diagonal()
      .projection(function(d) { return [d.x, d.y]; });

  var svg = d3.select("#tree-svg-div").append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", "translate(0,20)");
  
  var nodes = cluster.nodes(root),
  links = cluster.links(nodes);
  var link = svg.selectAll(".link")
  .data(links)
  .enter().append("path")
  .attr("class", "link")
  .attr("d", diagonal);
  
  var node = svg.selectAll(".node")
  .data(nodes)
  .enter().append("g")
  .attr("class", "node")
  .on("mouseover", mouseovered)
  .on("mouseout", mouseouted)
  .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

  node.append("circle")
  .attr("r", function(d) { return d.children ? 4.5 : 3; });

  var tip = d3.tip()
   .attr('class', 'd3-tip')
   .offset([-10, 0]);
  svg.call(tip);

  node.append("text")
   .attr("dx", function(d) { return d.children ? 12 : 0; })
   .attr("dy", function(d) { return d.children ? 3 : 12; })
   .attr("text-anchor", "middle")
   .style("font-size", function(d) { return d.children ? "14px" : "10px"; })
   .style("font-weight", function(d) { return d.children ? "bold" : ""; })
   .style("fill", function(d) { return d.children && merged_clusters.indexOf(d.name)!=-1 ? "red" : ""; })
   .text(function(d) { return d.name; });
  
// http://bl.ocks.org/mbostock/7607999
function mouseovered(d) {
  node
      .each(function(n) { n.target = n.source = false; });
  link
     .classed("link--source", function(l) { if (l.source === d) return l.target.target = true; });
  if (d.children)
     d.children.forEach(function(n) {
        link.classed("link--source", function(n) { if (n.source.target || n.target.target) return n.target.target = true; }); node.classed("node--source", function(n) { if (!n.children && n.target) return true; }) 
     });
  if (d.children) tip.html(cluster_descr[d.name]);
  else tip.html("file number " + d.name + "<br />" +file_descr[d.name]);
  tip.show();
}

 // hint? http://mbostock.github.io/d3/talk/20111018/tree.html

function mouseouted(d) {
  link
      .classed("link--target", false)
      .classed("link--source", false);

  node
      .classed("node--target", false)
      .classed("node--source", false);
 tip.hide();
}

  d3.select(self.frameElement).style("height", height + "px");
</script></div>
<a href="#" onClick="toggle_show('div-cc-clusters'); return false;">Show/Hide cluster list</a>
<div id="div-cc-clusters" style="display:none;">
<table class="cells">
<tr>%(header)s</tr>
%(data)s
</table>
</div>
""" % dict(treedata=treedata, merged_clusters=",".join(map(lambda x:'"%s"'%x[0], clusters)),
           file_descr=",".join(file_descr), cluster_descr=",".join(cluster_descr),
           header=header, data=data, method=method)
        self.write_html()
    # add_clutering_result()

    def _make_merge_table_framework(self):
        return """
<h2>Merging summary</h2>

<table class="merge">
 <tr>
  <th rowspan="2" colspan="2">cluster</th><th rowspan="2" title="Cluster height">ClH</th><th rowspan="2" title="Linear Cell Variation defined in BLEND">LCV</th><th rowspan="2" title="absolute Linear Cell Variation defined in BLEND">aLCV</th><th rowspan="2" title="Number of all datasets in the cluster">#DS<br />all</th><th rowspan="2" title="Number of actually merged datasets in the cluster">#DS<br />used</th>
  <th colspan="5">Overall</th>
  <th colspan="5">Outer shell</th>
  <th colspan="7">Inner shell</th>
  <th rowspan="2" title="ML estimate of isotropic Wilson B-factor by phenix.xtriage"><i>B</i><sub>Wilson</sub></th>
  <th rowspan="2" title="Anisotropy defined in phenix.xtriage">Aniso</sub></th>
 </tr>
 <tr>
  <th>Cmpl</th><th>Redun</th><th>I/&sigma;(I)</th><th><i>R</i><sub>meas</sub></th><th>CC<sub>1/2</sub></th>
  <th>Cmpl</th><th>Redun</th><th>I/&sigma;(I)</th><th><i>R</i><sub>meas</sub></th><th>CC<sub>1/2</sub></th>
  <th>Cmpl</th><th>Redun</th><th>I/&sigma;(I)</th><th><i>R</i><sub>meas</sub></th><th>CC<sub>1/2</sub></th><th>SigAno</th><th>CC<sub>ano</sub></th>
 </tr>
 %s
</table>
"""
    # _make_merge_table_framework()

    def _make_merge_plot_framework(self):
        axis_opts = "ClH   LCV aLCV ds.all ds.used  Cmpl Redun I/sigI Rmeas CC1/2 Cmpl.ou Red.ou I/sig.ou Rmeas.ou CC1/2.ou Cmpl.in Red.in I/sig.in Rmeas.in CC1/2.in SigAno.in CCano.in WilsonB Aniso".split()

        axis_opts_x, axis_opts_y = [], []
        for a in axis_opts:
            es = ' selected="selected"' if a=="Redun" else ""
            axis_opts_x.append('<option value="%s"%s>%s</option>'%(a,es,a))
            es = ' selected="selected"' if a=="CC1/2" else ""
            axis_opts_y.append('<option value="%s"%s>%s</option>'%(a,es,a))
            
        return """
<form name="merge_plot_selector">
<table>
<tr>
<td>
<div id="chartdiv_merge" style="width: 800px; height: 600px;"></div>
<script>
 var chart_merge = AmCharts.makeChart("chartdiv_merge", {
    "type": "xy",
    "theme": "none",  
    "legend": {
        "useGraphSettings": true,
    },
    "dataProvider": [%(data)s],
    "valueAxes": [{
        "position":"bottom",
        "axisAlpha": 0,
        "dashLength": 1,
        "title": "Redun"
    }, { 
        "axisAlpha": 0,
        "dashLength": 1,
        "position": "left",
        "title": "CC1/2"
    }],
    "graphs": [{
        "balloonText": "[[description]]: x=[[x]], y=[[y]]",
        "bullet": "round",
        "bulletSize": 8,
        "lineAlpha": 0,
        "xField": "Redun",
        "yField": "CC1/2",
        "descriptionField": "cls",
        "title": "Clusters",
        "hidden": false,
        "lineColor": "#FF6600",
        "fillAlphas": 0
    }],
    "chartScrollbar": {},
});
</script>
</td>
<td>X-axis:<br \>
<select name="xaxis" style="width: 150px" size="24" onChange="chart_merge.graphs[0].xField=this.value; chart_merge.valueAxes[0].title=this.value; chart_merge.validateNow(); chart_merge.validateData();">
%(axis_opts_x)s
</select>
</td>
<td>Y-axis:<br \>
<select name="xaxis" style="width: 150px" size="24" onChange="chart_merge.graphs[0].yField=this.value; chart_merge.valueAxes[1].title=this.value; chart_merge.validateNow(); chart_merge.validateData();">
%(axis_opts_y)s
</select>
</td>
</tr>
</table>
</form>
""" % dict(axis_opts_x="\n".join(axis_opts_x), axis_opts_y="\n".join(axis_opts_y), data="%s")
    # _make_merge_plot_framework()

    def add_merge_result(self, workdir, clh, LCV, aLCV, xds_files, used_files, stats):
        axis_opts = "cls ClH   LCV aLCV ds.all ds.used  Cmpl Redun I/sigI Rmeas CC1/2 Cmpl.ou Red.ou I/sig.ou Rmeas.ou CC1/2.ou Cmpl.in Red.in I/sig.in Rmeas.in CC1/2.in SigAno.in CCano.in WilsonB Aniso".split()

        cls = os.path.relpath(workdir, self.params.workdir)
        tmps = "%12s %5.2f %4.1f %4.1f %6d %7d %5.1f %5.1f %6.2f %5.1f %5.1f %7.1f %6.1f % 8.2f % 8.1f %8.1f %7.1f %6.1f % 8.2f % 8.1f %8.1f %9.1f %8.1f %7.2f %.1e"
        tmps = tmps % (cls, clh, LCV, aLCV,
                       len(xds_files), len(used_files),
                       stats["cmpl"][0],
                       stats["redundancy"][0],
                       stats["i_over_sigma"][0],
                       stats["r_meas"][0],
                       stats["cc_half"][0],
                       stats["cmpl"][2],
                       stats["redundancy"][2],
                       stats["i_over_sigma"][2],
                       stats["r_meas"][2],
                       stats["cc_half"][2],
                       stats["cmpl"][1],
                       stats["redundancy"][1],
                       stats["i_over_sigma"][1],
                       stats["r_meas"][1],
                       stats["cc_half"][1],
                       stats["sig_ano"][1],
                       stats["cc_ano"][1],
                       stats["xtriage_log"].wilson_b,
                       stats["xtriage_log"].anisotropy,
                       )

        tmptmp = tmps.replace("nan",'"nan"').split()
        tmptmp[0] = '"%s"' % tmptmp[0]
        self.html_merge_plot_data.append("{%s}"%",".join(map(lambda x: '"%s":%s'%tuple(x), zip(axis_opts, tmptmp))))

        tmps = "".join(map(lambda x: "<td>%s</td>"%x, tmps.split()))
        idno = len(self.html_merge_results)
        if self.params.program == "xscale":
            table_snip = xscalelp.snip_stats_table(stats["lp"])
        else:
            table_snip = ""
        tmps2 = """ <tr><td onClick="toggle_show2(this, 'merge-td-%d');" id="merge-td-mark-%d"">&#x25bc;</td>%s</tr>\n""" %(idno,idno,tmps)
        tmps2 += """ <tr><td style="padding: 0px;"><td colspan="25" style="display:none;padding:0px;" id="merge-td-%d"><pre style="font-size: 1.1em;">%s</pre></td></tr>""" % (idno, table_snip)

        self.html_merge_results.append(tmps2)
        
    # add_merge_result()

    def write_html(self):
        ofs = open(os.path.join(self.root, "report.html"), "w")
        ofs.write(self.html_head)
        ofs.write(self.html_params)
        ofs.write(self.html_inputfiles)
        ofs.write(self.html_clustering)

        # merging table
        ofs.write(self._make_merge_table_framework()%"".join(self.html_merge_results))
        tmps = ";".join(map(lambda x:"show_or_hide('merge-td-mark-%d', 'merge-td-%d', 0)"%(x,x), xrange(len(self.html_merge_results))))
        ofs.write("""<a href="#" onClick="%s;return false;">Expand all</a> / """ % tmps)
        tmps = ";".join(map(lambda x:"show_or_hide('merge-td-mark-%d', 'merge-td-%d', 1)"%(x,x), xrange(len(self.html_merge_results))))
        ofs.write("""<a href="#" onClick="%s;return false;">Collapse all</a>\n""" % tmps)

        # merging plot
        ofs.write(self._make_merge_plot_framework()%",".join(self.html_merge_plot_data))

        ofs.write("\n</body></html>")
        ofs.close()
    # write_html()

# class HtmlReportMulti
