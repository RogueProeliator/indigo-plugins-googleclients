#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# DomoPad Mobile Client Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	See plugin.py for more plugin details and information
#
# 	Version 0.8.15:
#		Initial release of DomoPad-branded plugin
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
# Python imports
#/////////////////////////////////////////////////////////////////////////////////////////
import os
import Queue
import re
import string
import sys
import threading

import indigo
import RPFramework

#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# DomoPadAndroidClient
#	Handles the information related to a specific Android client connected/talking to
#	Indigo and HousePad Plugins
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class DomoPadAndroidClient(RPFramework.RPFrameworkNonCommChildDevice.RPFrameworkNonCommChildDevice):

	#/////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super(DomoPadAndroidClient, self).__init__(plugin, device)
		
		self.upgradedDeviceProperties.append((u'SupportsBatteryLevel', True))
		
		self.upgradedDeviceStates.append(u'modelName')
		self.upgradedDeviceStates.append(u'batteryStatus')
		self.upgradedDeviceStates.append(u'batteryLevel')
		self.upgradedDeviceStates.append(u'longitude')
		self.upgradedDeviceStates.append(u'latitude')
		self.upgradedDeviceStates.append(u'locationFixTime')
	
	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Overridden communications functions
	#/////////////////////////////////////////////////////////////////////////////////////
	def initiateCommunications(self):
		super(DomoPadAndroidClient, self).initiateCommunications()
		
		# update the state of the device to reflect the pairing status...
		currentPairingState = self.indigoDevice.states.get("isPaired", False)
		currentPairingProp = self.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		
		if currentPairingProp == "":
			self.indigoDevice.updateStateOnServer("isPaired", False, uiValue="Not Paired")
		else:
			self.indigoDevice.updateStateOnServer("isPaired", True, uiValue="Paired")
			
			
			
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# VideoCameraFeed
#	Handles the specification of a video feed that can be shown within HousePad, such as
#	to show live security camera feeds
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class VideoCameraFeed(RPFramework.RPFrameworkNonCommChildDevice.RPFrameworkNonCommChildDevice):

	#/////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super(VideoCameraFeed, self).__init__(plugin, device)
			
		