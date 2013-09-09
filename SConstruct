import os

env = Environment(ENV = os.environ)
env.Append(CPPPATH = ['#/ansic/srdp'])

Export('env')

srdp = SConscript('#ansic/srdp/SConscript')

Export('srdp')

SConscript('#ansic/examples/udp_adapter/SConscript')
