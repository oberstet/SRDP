import os

env = Environment(ENV = os.environ)
env.Append(CPPPATH = ['#/ansic/srdp', r"C:\\Program Files (x86)\\Microsoft SDKs\\Windows\\v7.0A\\"])

Export('env')

srdp = SConscript('#ansic/srdp/SConscript')

Export('srdp')

SConscript('#ansic/examples/udp_adapter/SConscript')
