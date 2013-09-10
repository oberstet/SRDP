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

__all__ = ('ISrdpProvider',
           'ISrdpChannel')

import zope
from zope.interface import Interface, Attribute



class ISrdpProvider(zope.interface.Interface):

   def onChannelOpen(channel):
      """
      """

   def onRegisterRead(device, register, position, length):
      """
      """

   def onRegisterWrite(device, register, position, data):
      """
      """

   def onRegisterChange(device, register, position, data):
      """
      """

   def onChannelClose(reason):
      """
      """


class ISrdpChannel(zope.interface.Interface):

   def readRegister(device, register, position = 0, length = 0):
      """
      """

   def writeRegister(device, register, data, position = 0):
      """
      """

   def notifyRegister(device, register, position, length):
      """
      """

   def closeChannel():
      """
      """
