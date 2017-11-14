import contextlib, errno, functools, itertools, logging, os, tempfile

@contextlib.contextmanager
def cd(newdir):
  """http://stackoverflow.com/a/24176022/5228524"""
  prevdir = os.getcwd()
  os.chdir(os.path.expanduser(newdir))
  try:
    yield
  finally:
    os.chdir(prevdir)

class TFile(object):
  def __init__(self, *args, **kwargs):
    self.args, self.kwargs = args, kwargs
  def __enter__(self):
    import ROOT
    self.__tfile = ROOT.TFile.Open(*self.args, **self.kwargs)
    return self.__tfile
  def __exit__(self, *err):
    self.__tfile.Close()

def cache(function):
  cache = {}
  @functools.wraps(function)
  def newfunction(*args, **kwargs):
    try:
      return cache[args, tuple(sorted(kwargs.iteritems()))]
    except TypeError:
      print args, tuple(sorted(kwargs.iteritems()))
      raise
    except KeyError:
      cache[args, tuple(sorted(kwargs.iteritems()))] = function(*args, **kwargs)
      return newfunction(*args, **kwargs)
  return newfunction
