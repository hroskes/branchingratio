#!/usr/bin/env python

from __future__ import print_function
from utilities import cache, cd, TFile
import contextlib, urllib, re, subprocess, os, numpy, math
import yellowhiggs #to get this, run: pip install --user -e git+git://github.com/hroskes/yellowhiggs.git@master#egg=yellowhiggs

basemass = 300

def GammaHZZ_YR3(mass):
  return yellowhiggs.width(mass)[0] * yellowhiggs.br(mass, "ZZ")[0]

def sgn(number):
  return math.copysign(1, number)

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
def GammaH_YR2(mass):
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
    multiplyweight = GammaHZZ_YR3(basemass) * GammaHZZ_JHU(t.GenHMass) / (GammaHZZ_JHU(basemass) * t.genHEPMCweight * GammaH_YR2(t.GenHMass))
    t.GetEntry(1)
    print("test should be equal:", multiplyweight, GammaHZZ_YR3(basemass) * GammaHZZ_JHU(t.GenHMass) / (GammaHZZ_JHU(basemass) * t.genHEPMCweight * GammaH_YR2(t.GenHMass)))

    BR, weights, weights_rwttoBW = \
      zip(*([multiplyweight * abs(t.genHEPMCweight), sgn(t.genHEPMCweight), sgn(t.genHEPMCweight)*t.p_Gen_CPStoBWPropRewgt] for entry in t))

    return numpy.average(BR, weights=weights), numpy.average(BR, weights=weights_rwttoBW)

if __name__ == "__main__":
  for p in "VBF",:
    for m in 300, 500:
      print(p, m, yellowhiggs.br(m, "ZZ")[0], *averageBR(p, m))
