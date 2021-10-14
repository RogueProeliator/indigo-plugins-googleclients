#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Domotics Pad Client Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	Indigo plugin designed to interface with the various Google services supported by
#   Domotics Pad, such as mobile clients and Google Home devices
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
# Python imports
#/////////////////////////////////////////////////////////////////////////////////////////
import cgi
from   distutils.dir_util import copy_tree
import os
import re
import simplejson as json
import socket
import string
import threading
import urllib
import inspect
import requests

import RPFramework
import domoPadDevices
import googleHomeDevices
import dicttoxml


#/////////////////////////////////////////////////////////////////////////////////////////
# Constants and configuration variables
#/////////////////////////////////////////////////////////////////////////////////////////
DOMOPADCOMMAND_SENDNOTIFICATION                = u'SendNotification'
DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION   = u'SendTextToSpeechNotification'
DOMOPADCOMMAND_CPDISPLAYNOTIFICATION           = u'SendCPDisplayRequest'
DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION = u'RequestDeviceStatusUpdate'

GOOGLEHOME_SENDDEVICEUPDATE = u'SendHomeGraphUpdate'
GOOGLEHOME_REQUESTSYNC      = u'RequestHomeGraphSync'

INDIGO_SERVER_CLOUD_URL     = u'https://us-central1-domotics-pad-indigo-client.cloudfunctions.net/indigo-server-portal'


#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Plugin
#	Primary Indigo plugin class that is universal for all devices (receivers) to be
#	controlled
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class Plugin(RPFramework.RPFrameworkPlugin.RPFrameworkPlugin):
	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class creation; setup the device tracking
	# variables for later use
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		# RP framework base class's init method
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs, managedDeviceClassModule=domoPadDevices)

		# initialize the member variable that tracks whether or not we are reporting device
		# states back to Google Home
		self.reportStateToAssistant = pluginPrefs.get("sendUpdatesToGoogle", False)
		
		
	#/////////////////////////////////////////////////////////////////////////////////////
	# Indigo control methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# startup is called by Indigo whenever the plugin is first starting up (by a restart
	# of Indigo server or the plugin or an update
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def startup(self):
		super(Plugin, self).startup()
		
		# subscribe to all devices changes so that we may push them up to Google Home
		# (if so configured)
		indigo.devices.subscribeToChanges()
		
		
	#/////////////////////////////////////////////////////////////////////////////////////
	# Action/command processing routines
	#/////////////////////////////////////////////////////////////////////////////////////	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to handle any unknown commands at the plugin level; it
	# can/should be overridden in the plugin implementation (if needed)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handleUnknownPluginCommand(self, rpCommand, reQueueCommandsList):
		if rpCommand.commandName == GOOGLEHOME_SENDDEVICEUPDATE:
			try:
				reflectorUrl = indigo.server.getReflectorURL() + u'/'
				deviceUpdateXml = dicttoxml.dicttoxml(rpCommand.commandPayload, True, "Device")
				requestBody = { "intent": "googlehomegraph.UPDATE_DEVICE", "payload": { "agentId": reflectorUrl, "deviceUpdate": deviceUpdateXml }}
				self.logger.info('Sending ' + json.dumps(requestBody))
				requests.post(INDIGO_SERVER_CLOUD_URL, data=json.dumps(requestBody))
			except:
				self.logger.exception(u'Failed to send device update to Google Home')

		elif rpCommand.commandName == GOOGLEHOME_REQUESTSYNC:
			try:
				reflectorUrl = indigo.server.getReflectorURL() + u'/'
				requestBody  = '{ "intent": "googlehomegraph.REQUEST_SYNC", "payload": { "agentId": "' + reflectorUrl + '" } }'
				self.logger.debug(u'Sending intent to Indigo Cloud for synchronization with {0}'.format(reflectorUrl))
				requests.post(INDIGO_SERVER_CLOUD_URL, data=requestBody)
			except Exception:
				self.logger.exception(u'Failed to request that device definitions re-synchronize with Google Home/Assistant')
			

	#/////////////////////////////////////////////////////////////////////////////////////	
	# Plugin Event Overrides
	#/////////////////////////////////////////////////////////////////////////////////////	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called whenever a device updates... if it is one of the monitored devices then
	# send the updates to Google Home
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def deviceUpdated(self, origDev, newDev):
		self.logger.debug(u'Received device update for ' + newDev.name)

		# call the base's implementation first just to make sure all the right things happen elsewhere
		indigo.PluginBase.deviceUpdated(self, origDev, newDev)

		# we only care about devices which are published to Google Home and only whenever
		# the option to send devices changes is checked
		if self.reportStateToAssistant == True and 'com.indigodomo.indigoserver' in newDev.globalProps:
			globalPropsDict = newDev.globalProps['com.indigodomo.indigoserver']
			if globalPropsDict.get(u'googleClientPublishHome', False) == True and globalPropsDict.get(u'googleClientSendUpdates', False) == True:
				try:
					# retrieve the device update from the server in the same format as the query for
					# the device status
					deviceUpdate = indigo.rawServerRequest("GetDevice", {"ID": newDev.id})

					# schedule a call to the Google Home Graph's update via the Cloud Function
					self.logger.info(u'Scheduling device update of {0} ({1}) with Google Home/Assistant'.format(newDev.id, newDev.name))
					self.logger.debug(u'Sending device update: ' + dicttoxml.dicttoxml(deviceUpdate, True, "Device"))
					self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(GOOGLEHOME_SENDDEVICEUPDATE, deviceUpdate))
				except:
					self.logger.exception(u'Failed to generate Google Home update for device ' + unicode(newDev.name))
					
			
	#/////////////////////////////////////////////////////////////////////////////////////
	# Configuration Dialog Callback Routines
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Retrieves the list of all indigo devices which may be published to the Google Home
	# application; sorted by its published status
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getGoogleHomeDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
		publishedHomeDevices = []
		availableHomeDevices = []

		for dev in indigo.devices:
			if dev.sharedProps.get(u'googleClientPublishHome', False):
				publishedHomeDevices.append((dev.id, dev.name))
			else:
				availableHomeDevices.append((dev.id, dev.name))

		# build the complete list of devices
		returnList = []
		returnList.append((-1, "%%disabled:Devices available for publishing%%"))
		returnList.extend(availableHomeDevices)

		returnList.append((-2, u"%%separator%%"))
		returnList.append((-3, "%%disabled:Devices already published to Google Assistant%%"))
		returnList.extend(publishedHomeDevices)
		return returnList

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Retrieves the list of available (supported) devices types as defined by the
	# Google Assistant
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getGoogleDeviceTypes(self, filter="", valuesDict=None, typeId="", targetId=0):
		if valuesDict is None:
			return []
			
		publishedDeviceId = unicode(valuesDict.get(u"publishedDevice", ""))
		if publishedDeviceId is None or publishedDeviceId == "":
			return []

		device = indigo.devices.get(int(publishedDeviceId), None)
		if device is None:
			return []
		else:
			return googleHomeDevices.getAvailableSubtypesForDevice(device)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called whenever the user has selected a device from the list of published Google
	# Assistant devices... show the "Google" device details
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def publishedHomeDeviceSelected(self, valuesDict=None, typeId="", devId=0):
		try:
			device = indigo.devices.get(int(valuesDict["publishedDevice"]), None)

			valuesDict["enableDeviceDetailUI"]       = True
			valuesDict["publishToGoogle"]            = device.sharedProps.get(u'googleClientPublishHome', False)
			valuesDict["deviceDetailsPublishedName"] = device.sharedProps.get(u'googleClientAsstName'   , u'')
			valuesDict["deviceDetailsPublishedType"] = device.sharedProps.get(u'googleClientAsstType'   , u'')
			valuesDict["sendUpdatesToGoogle"]        = device.sharedProps.get(u'googleClientSendUpdates', u'')
			valuesDict["deviceDetailsPINCode"]       = device.sharedProps.get(u'googleClientPINCode'    , u'')
		except:
			self.logger.exception(u'Failed to load published device properties')
		return valuesDict

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called whenever the user has clicked to update the published Google Home (such as
	# changing the device name or type)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def publishedHomeDevicesUpdate(self, valuesDict=None, typeId="", devId=0):
		try:
			device      = indigo.devices.get(int(valuesDict["publishedDevice"]), None)
			globalProps = device.sharedProps

			globalProps[u'googleClientPublishHome'] = valuesDict["publishToGoogle"]
			globalProps[u'googleClientAsstName']    = valuesDict["deviceDetailsPublishedName"]
			globalProps[u'googleClientAsstType']    = valuesDict["deviceDetailsPublishedType"]
			globalProps[u'googleClientSendUpdates'] = valuesDict["sendUpdatesToGoogle"]
			globalProps[u'googleClientPINCode']     = valuesDict["deviceDetailsPINCode"]
			device.replaceSharedPropsOnServer(globalProps)

			valuesDict["publishedDevice"]            = None
			valuesDict["publishToGoogle"]            = False
			valuesDict['publishedDeviceSelected']    = False
			valuesDict["deviceDetailsPublishedName"] = u''
			valuesDict["deviceDetailsPublishedType"] = None
			valuesDict["sendUpdatesToGoogle"]        = False
			valuesDict["deviceDetailsPINCode"]       = u''

			valuesDict["enableDeviceDetailUI"]       = False

			# let Google know that a synchronization is required
			
		except:
			self.logger.exception(u'Failed to update published device properties')
		return valuesDict


	#/////////////////////////////////////////////////////////////////////////////////////
	# API Action Handlers
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Sets the Setpoint of a thermostat using the current thermostat mode (heating or
	# cooling)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def apiSetThermostatSetpoint(self, action, dev=None, callerWaitingForResult=None):
		deviceId    = int(action.props["body_params"].get(u'deviceId', '0'))
		newSetpoint = float(action.props["body_params"].get(u'setpoint', '0.0'))
		isSuccess   = False
		message     = u''

		if deviceId == 0 or newSetpoint == 0.0:
			self.logger.warning(u'Unable to process API request to set thermostat setpoint due to missing or invalid arguments')
			message = u'Unable to process API request to set thermostat setpoint due to missing or invalid arguments'
		else:
			device = indigo.devices[deviceId]
			if device.hvacMode == indigo.kHvacMode.HeatCool or device.hvacMode == indigo.kHvacMode.ProgramHeatCool or device.hvacMode == indigo.kHvacMode.Cool or device.hvacMode == indigo.kHvacMode.ProgramCool:
				indigo.thermostat.setCoolSetpoint(deviceId, value=newSetpoint)
				isSuccess = True
			elif device.hvacMode == indigo.kHvacMode.Heat or device.hvacMode == indigo.kHvacMode.ProgramHeat:
				indigo.thermostat.setHeatSetpoint(deviceId, value=newSetpoint)
				isSuccess = True
			else:
				message = u'Thermostat is off or not in a mode that accepts setpoint changes'
		
		return '{{ "result": "{0}", "message": "{1}" }}'.format(isSuccess, message)

	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Utility Routines
	#/////////////////////////////////////////////////////////////////////////////////////		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Processes the user requesting that the Google Home Graph re-sync the set of
	# published devices
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def requestResyncWithGoogle(self):
		# simply schedule a resynchronization request with the background processor
		self.logger.info(u'Scheduling re-synchronization request with Google Home/Assistant')
		self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(GOOGLEHOME_REQUESTSYNC))
	