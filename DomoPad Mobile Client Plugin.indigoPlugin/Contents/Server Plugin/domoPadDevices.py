#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Domotics Pad Google Client Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	See plugin.py for more plugin details and information
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
		super().__init__(plugin, device)
		
		self.upgradedDeviceProperties.append(("SupportsBatteryLevel", True))
		
		self.upgradedDeviceStates.append("modelName")
		self.upgradedDeviceStates.append("batteryStatus")
		self.upgradedDeviceStates.append("batteryLevel")
		self.upgradedDeviceStates.append("longitude")
		self.upgradedDeviceStates.append("latitude")
		self.upgradedDeviceStates.append("locationFixTime")
	
	
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
			
		