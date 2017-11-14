#!/usr/bin/env python

from __future__ import print_function
from utilities import cache, cd, TFile
import contextlib, urllib, re, subprocess, os, numpy

BR_YR4_125 = 5.897E-05
BR_YR3_125 = 5.93E-05

@cache
def setupJHUGen():
  if not os.path.exists("JHUGen/JHUGenerator"):
    with cd("JHUGen"):
      subprocess.check_call(["wget", "http://spin.pha.jhu.edu/Generator/JHUGenerator.v7.0.2.tar.gz"])
      subprocess.check_call(["tar" ,"xvzf", "JHUGenerator.v7.0.2.tar.gz"])
  with cd("JHUGen/JHUGenerator"):
    subprocess.check_call(["wget", "https://github.com/cms-sw/genproductions/raw/be7e09d66bb79807c5fe12cbb7b2504424f76079/bin/JHUGen/Pdecay/PMZZdistribution.out"])

    with open("makefile") as f:
      makefile = f.read()
    newmakefile = makefile.replace("linkMELA = Yes", "linkMELA = No")
    if newmakefile != makefile:
      with open("makefile", "w") as f:
        f.write(newmakefile)

    os.system("make")
    

@cache
def getBR_JHU(mass):
  setupJHUGen()
  with cd("JHUGen/JHUGenerator"):
    output = subprocess.check_output("./JHUGen ReadPMZZ PrintPMZZ={mass},{mass} ReweightDecay WidthScheme=3 PrintPMZZIntervals=0".format(mass=mass).split())
    for line in output.split("\n"):
      match = re.match(" *([0-9.]+) *([0-9.+-E]+)", line)
      if match and "%" not in line:  #why is % not in line needed?
        if float("{:.4f}".format(float(match.group(1)))) == float("{:.4f}".format(mass)):
          return float(match.group(2))
    assert False

def averageBR(productionmode, mass):
  if productionmode == "VBF": productionmode = "VBFH"
  folder = "{}{:d}".format(productionmode, mass)
  with TFile("root://lxcms03//data3/Higgs/171005/"+folder+"/ZZ4lAnalysis.root") as f:
    t = f.ZZTree.Get("candTree")
    t.SetBranchStatus("*", 0)
    t.SetBranchStatus("GenHMass", 1)
    t.SetBranchStatus("genHEPMCweight", 1)
    t.SetBranchStatus("p_Gen_CPStoBWPropRewgt", 1)
    t.GetEntry(0)
    multiplyweight = getBR_JHU(t.GenHMass) / t.genHEPMCweight * BR_YR3_125 / getBR_JHU(125)
    t.GetEntry(1)
#    print("test should be equal:", multiplyweight, getBR_JHU(t.GenHMass) / t.genHEPMCweight * BR_YR3_125 / getBR_JHU(125))

    BR, weights = zip(*([multiplyweight * t.genHEPMCweight, t.p_Gen_CPStoBWPropRewgt] for entry in t))

    return numpy.average(BR, weights=weights), numpy.average(BR)

if __name__ == "__main__":
  for p in "VBF",:
    for m in 300, 500:
      print(p, m, *averageBR(p, m))
