import zope
from zope.interface import Interface, Attribute

__all__ = ('ISrdpProvider',
           'ISrdpChannel')


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
