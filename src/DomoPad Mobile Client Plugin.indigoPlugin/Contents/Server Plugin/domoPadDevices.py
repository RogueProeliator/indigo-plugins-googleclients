#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# Domotics Pad Client Plugin by RogueProeliator <adam@duncanwaredevelopment.com>
#######################################################################################

from RPFramework.RPFrameworkNonCommChildDevice import RPFrameworkNonCommChildDevice


class DomoPadAndroidClient(RPFrameworkNonCommChildDevice):

	#######################################################################################
	# Class construction and destruction methods
	#######################################################################################
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super().__init__(plugin, device)
		
		self.upgraded_device_properties.append(("SupportsBatteryLevel", True))
		
		self.upgraded_device_states.append("modelName")
		self.upgraded_device_states.append("batteryStatus")
		self.upgraded_device_states.append("batteryLevel")
		self.upgraded_device_states.append("longitude")
		self.upgraded_device_states.append("latitude")
		self.upgraded_device_states.append("locationFixTime")

	#######################################################################################
	# Overridden communications functions
	#######################################################################################
	def initiate_communications(self):
		super().initiate_communications()
		
		# update the state of the device to reflect the pairing status...
		current_pairing_prop = self.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		
		if current_pairing_prop == "":
			self.indigoDevice.updateStateOnServer("isPaired", False, uiValue="Not Paired")
		else:
			self.indigoDevice.updateStateOnServer("isPaired", True, uiValue="Paired")
			

class VideoCameraFeed(RPFrameworkNonCommChildDevice):

	#######################################################################################
	# Class construction and destruction methods
	#######################################################################################
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class receiving a command to start device
	# communication. The plugin will call other commands when needed, simply zero out the
	# member variables
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin, device):
		super().__init__(plugin, device)
			
		