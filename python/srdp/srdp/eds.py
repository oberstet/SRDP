###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

__all__ = ("SrdpEds",
           "SrdpEdsDatabase",)


import struct, binascii
import json, os, re
from pprint import pprint

from twisted.python import log


class SrdpEds:

   SRDP_STYPE_TO_PTYPE = {'int8': 'b',
                          'uint8': 'B',
                          'int16': 'h',
                          'uint16': 'H',
                          'int32': 'l',
                          'uint32': 'L',
                          'int64': 'q',
                          'uint64': 'Q',
                          'float': 'f',
                          'double': 'd'}


   def __init__(self):
      for att in ['uri', 'label', 'desc', 'vendor', 'model']:
         setattr(self, att, None)
      self.registersByIndex = {}
      self.registersByPath = {}
      self.registerIncludes = []
      self.registersIncluded = False


   def load(self, filename):
      eds = json.loads(open(filename).read())

      for att in ['uri', 'label', 'desc', 'vendor', 'model']:
         if eds.has_key(att):
            setattr(self, att, eds[att])
         else:
            setattr(self, att, None)

      for r in eds['registers']:
         if type(r) in [str, unicode]:
            self.registerIncludes.append(r)
         else:
            self.registersByIndex[r['index']] = r
            self.registersByPath[r['path']] = r


   def getRegister(self, register):
      """
      Given a register path or index, return the register descriptor
      or None if register cannot be found.
      """
      reg = None
      if type(register) == int:
         reg = self.registersByIndex.get(register, None)
      elif type(register) in [str, unicode]:
         reg = self.registersByPath.get(register, None)
      return reg


   def unserialize(self, register, data):
      """
      Given a register path or index, unserialize the given data (octets)
      into a proper value according to the register type.
      """
      reg = self.getRegister(register)
      if reg is None:
         raise Exception("no such register")

      ## string
      ##
      if reg['type']  == 'char' and reg['count'] in ['uint8', 'uint16']:
         if reg['count'] == 'uint8':
            return reg, data[1:].decode('utf8')
         elif reg['count'] == 'uint16':
            return reg, data[2:].decode('utf8')

      elif type(reg['type']) == list:
         o = {}
         td = '<'
         for field in reg['type']:
            td += SrdpEds.SRDP_STYPE_TO_PTYPE[field['type']]
         tval = list(struct.unpack(td, data))
         for i in xrange(len(tval)):
            o[str(reg['type'][i]['field'])] = tval[i]

         return reg, o

      elif type(reg['count']) == int:
         if reg['count'] == 1:
            fmt = '<' + SrdpEds.SRDP_STYPE_TO_PTYPE[reg['type']]
            tval = struct.unpack(fmt, data)[0]
            return reg, tval
         else:
            if reg['type'] == 'uint8':
               return reg, '0x' + binascii.hexlify(data)

      else:
         return reg, '?'


   def serialize(self, register, value):
      """
      Given a register path or index, serialize the given value
      into data (octets) according to the register type.
      """
      reg = self.getRegister(register)
      if reg is None:
         raise Exception("no such register")

      ## string
      ##
      if reg['type']  == 'char' and reg['count'] in ['uint8', 'uint16']:
         if type(value) in [str, unicode]:
            s = value.encode('utf8')
            if reg['count'] == 'uint8':
               return reg, struct.pack('<B', len(s)) + s
            elif reg['count'] == 'uint16':
               return reg, struct.pack('<H', len(s)) + s
         else:
            raise Exception("expected str/unicode value")

      elif type(reg['type']) == list:
         o = []
         td = '<'
         for field in reg['type']:
            td += SrdpEds.SRDP_STYPE_TO_PTYPE[field['type']]
            o.append(value[field['field']])
         return reg, struct.pack(td, *o)

      elif type(reg['count']) == int:
         if reg['count'] == 1:
            fmt = '<' + SrdpEds.SRDP_STYPE_TO_PTYPE[reg['type']]
            return reg, struct.pack(fmt, value)

      raise Exception("serialize type not implemted")



class SrdpEdsDatabase:

   def __init__(self, debug = False):
      self.debug = debug
      self.reset()


   def reset(self):
      self._edsByUri = {}
      self._edsByFilename = {}


   def _includeRegisters(self, eds, uri):

      if self._edsByUri.has_key(uri):

         for r in self._edsByUri[uri].registersByIndex.values():

            if eds.registersByIndex.has_key(r['index']):
               msg = "Register overlap by index %d, %s, %s" % (r['index'], eds.uri, uri)
               raise Exception(msg)
            else:
               eds.registersByIndex[r['index']] = r

            if eds.registersByPath.has_key(r['path']):
               msg = "Register overlap by path %s, %s, %s" % (r['path'], eds.uri, uri)
               raise Exception(msg)
            else:
               eds.registersByPath[r['path']] = r

         eds.registersIncluded = True

         if not self._edsByUri[uri].registersIncluded:
            for u in self._edsByUri[uri].registerIncludes:
               self._includeRegisters(eds, u)

      else:
         raise Exception("Register include failed: no EDS with URI %s in database" % uri)


   def loadFromDir(self, dir):

      n = 0

      pat = re.compile("^.*\.json$")
      for root, dirs, files in os.walk(dir):
         for f in files:
            if pat.match(f):
               f = os.path.join(root, f)
               eds = SrdpEds()
               eds.load(f)
               eds.filename = f
               uri = str(eds.uri)
               if not self._edsByUri.has_key(uri):
                  self._edsByUri[uri] = eds
                  self._edsByFilename[str(f)] = eds
                  n += 1
               else:
                  print "Warning: EDS file with same URI was already loaded (skipping this one)"

      return n


   def check(self):

      for eds in self._edsByUri.values():
         if self.debug:
            log.msg("Postprocessing EDS %s [%s]" % (eds.uri, eds.filename))
         for i in eds.registerIncludes:
            self._includeRegisters(eds, i)

      return len(self._edsByUri)


   def getEdsByUri(self, uri):
      return self._edsByUri.get(uri, None)


   def getEdsByFilename(self, filename):
      return self._edsByFilename.get(filename, None)


   def pprint(self, uri = None):
      if uri is None:
         for eds in self._edsByUri.values():
            print "="*30
            print "EDS : ", eds.uri
            pprint(eds.registerIncludes)
            print
            pprint(eds.registersByIndex)
            print
            pprint(eds.registersByPath)
            print
      else:
         eds = self.getEdsByUri(uri)
         pprint(eds.registerIncludes)
         print
         pprint(eds.registersByIndex)
         print
         pprint(eds.registersByPath)
         print

   def toHtml(self, uri, filename):
      pass
