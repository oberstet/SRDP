import os, sys

PLATFORM = None

if sys.platform.startswith('win32'):
   PLATFORM = 'windows'
elif sys.platform.startswith('linux'):
   PLATFORM = 'posix'
else:
   print "assuming Posix platform"
   PLATFORM = 'posix'

env = Environment(ENV = os.environ)

env.Append(CPPPATH = ['#/ansic/srdp'])

if PLATFORM == 'windows':
   env.Append(CPPPATH = [r"C:\\Program Files (x86)\\Microsoft SDKs\\Windows\\v7.0A\\"])

if PLATFORM == 'posix':
#   env.Append(CCFLAGS = ['-Wall', '-O3'])
#   env.Append(CCFLAGS = ['-std=c89', '-Wall', '-Wextra', '-Wno-unused-parameter'])
   # FIXME: we use "//"-style comments .. not supported on c89
   env.Append(CCFLAGS = ['-std=gnu89', '-Wall', '-Wextra', '-Wno-unused-parameter'])

Export('env')

srdp = SConscript('#ansic/srdp/SConscript')

Export('srdp')

if PLATFORM == 'posix':
   SConscript('#ansic/examples/udp_adapter/SConscript')
