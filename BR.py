#!/usr/bin/env python

from __future__ import print_function
from utilities import cache, cd, TFile
import contextlib, urllib, re, subprocess, os, numpy

GammaHany_YR3_300 = 8.43E+00
BRHZZ_YR3_300 = 3.07E-01

GammaHZZ_YR3_300 = GammaHany_YR3_300*BRHZZ_YR3_300

@cache
def setupJHUGen():
  if not os.path.exists("JHUGen/JHUGenerator"):
    with cd("JHUGen"):
      subprocess.check_call(["wget", "http://spin.pha.jhu.edu/Generator/JHUGenerator.v7.0.2.tar.gz"])
      subprocess.check_call(["tar" ,"xvzf", "JHUGenerator.v7.0.2.tar.gz"])
  with cd("JHUGen/JHUGenerator"):
    if not os.path.exists("PMZZdistribution.out"):
      subprocess.check_call(["wget", "https://github.com/cms-sw/genproductions/raw/be7e09d66bb79807c5fe12cbb7b2504424f76079/bin/JHUGen/Pdecay/PMZZdistribution.out"])

    with open("makefile") as f:
      makefile = f.read()
    newmakefile = makefile.replace("linkMELA = Yes", "linkMELA = No")
    if newmakefile != makefile:
      with open("makefile", "w") as f:
        f.write(newmakefile)

    with open("mod_PMZZ.F90") as f:
      modPMZZ = f.read()
    newmodPMZZ = modPMZZ.replace(" call HTO_gridHt(EHat/GeV,BigGamma)", " BigGamma = 1\n             !call HTO_gridHt(EHat/GeV,BigGamma)")
    if newmodPMZZ != modPMZZ:
      with open("mod_PMZZ.F90", "w") as f:
        f.write(newmodPMZZ)

    os.system("make")

@cache
def setupBigGamma():
  setupJHUGen()
  with cd("BigGamma"):
    subprocess.check_call(["gfortran", "-o", "BigGamma", "-J", "modules", "BigGamma.F90", "../JHUGen/JHUGenerator/CPS/CALLING_cpHTO.f"])

@cache
def GammaHZZ_JHU(mass):
  setupJHUGen()
  with cd("JHUGen/JHUGenerator"):
    output = subprocess.check_output("./JHUGen ReadPMZZ PrintPMZZ={mass},{mass} ReweightDecay WidthScheme=3 PrintPMZZIntervals=0".format(mass=mass).split())
    for line in output.split("\n"):
      match = re.match(" *([0-9.]+) *([0-9.+-E]+)", line)
      if match and "%" not in line:  #why is % not in line needed?
        if float("{:.4f}".format(float(match.group(1)))) == float("{:.4f}".format(mass)):
          return float(match.group(2))
    assert False

@cache
def GammaHZZ_YR2(mass):
  setupBigGamma()
  with cd("BigGamma"):
    return float(subprocess.check_output(["./BigGamma", str(mass)]))

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
    multiplyweight = getGammaZZ_JHU(t.GenHMass) / t.genHEPMCweight * BR_YR3_125 / getGammaZZ_JHU(125)
    t.GetEntry(1)
#    print("test should be equal:", multiplyweight, getGammaZZ_JHU(t.GenHMass) / t.genHEPMCweight * BR_YR3_125 / getGammaZZ_JHU(125))

    BR, weights = zip(*([multiplyweight * t.genHEPMCweight, t.p_Gen_CPStoBWPropRewgt] for entry in t))

    return numpy.average(BR, weights=weights), numpy.average(BR)

if __name__ == "__main__":
  print(GammaHZZ_YR2(125))
#  for p in "VBF",:
#    for m in 300, 500:
#      print(p, m, *averageBR(p, m))
