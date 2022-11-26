#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
# Domotics Pad Client Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	Indigo plugin designed to interface with the various Google services supported by
#   Domotics Pad, such as mobile clients and Google Home devices
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#region Python imports
from   distutils.dir_util import copy_tree
import json
import requests

import RPFramework
import domoPadDevices
import googleHomeDevices
import dicttoxml

from RPFramework.RPFrameworkPlugin import RPFrameworkPlugin

#endregion
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
#region Constants and configuration variables
DOMOPADCOMMAND_SENDNOTIFICATION                = 'SendNotification'
DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION   = 'SendTextToSpeechNotification'
DOMOPADCOMMAND_CPDISPLAYNOTIFICATION           = 'SendCPDisplayRequest'
DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION = 'RequestDeviceStatusUpdate'

GOOGLEHOME_SENDDEVICEUPDATE = 'SendHomeGraphUpdate'
GOOGLEHOME_REQUESTSYNC      = 'RequestHomeGraphSync'

INDIGO_SERVER_CLOUD_URL     = 'https://us-central1-domotics-pad-indigo-client.cloudfunctions.net/indigo-server-portal'

#endregion
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
# Plugin
#	Primary Indigo plugin class that is universal for all devices (receivers) to be
#	controlled
#/////////////////////////////////////////////////////////////////////////////////////////
class Plugin(RPFrameworkPlugin):
	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class creation; setup the device tracking
	# variables for later use
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		# RP framework base class's init method
		super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs, managedDeviceClassModule=domoPadDevices)

		# initialize the member variable that tracks whether we are reporting device
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
				reflectorUrl = f"{indigo.server.getReflectorURL()}/"
				deviceUpdateXml = dicttoxml.dicttoxml(rpCommand.commandPayload, True, "Device")
				requestBody = { "intent": "googlehomegraph.UPDATE_DEVICE", "payload": { "agentId": reflectorUrl, "deviceUpdate": deviceUpdateXml }}
				self.logger.info('Sending ' + json.dumps(requestBody))
				requests.post(INDIGO_SERVER_CLOUD_URL, data=json.dumps(requestBody))
			except:
				self.logger.exception('Failed to send device update to Google Home')

		elif rpCommand.commandName == GOOGLEHOME_REQUESTSYNC:
			try:
				reflectorUrl = f"{indigo.server.getReflectorURL()}/'"
				requestBody  = f'{{ "intent": "googlehomegraph.REQUEST_SYNC", "payload": {{ "agentId": "{reflectorUrl}" }} }}'
				self.logger.debug(f"Sending intent to Indigo Cloud for synchronization with {reflectorUrl}")
				requests.post(INDIGO_SERVER_CLOUD_URL, data=requestBody)
			except Exception:
				self.logger.exception('Failed to request that device definitions re-synchronize with Google Home/Assistant')

	#/////////////////////////////////////////////////////////////////////////////////////	
	# Plugin Event Overrides
	#/////////////////////////////////////////////////////////////////////////////////////	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called whenever a device updates... if it is one of the monitored devices then
	# send the updates to Google Home
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def deviceUpdated(self, origDev, newDev):
		self.logger.debug(f"Received device update for {newDev.name}")

		# call the base's implementation first just to make sure all the right things happen elsewhere
		indigo.PluginBase.deviceUpdated(self, origDev, newDev)

		# we only care about devices which are published to Google Home and only whenever
		# the option to send devices changes is checked
		if self.reportStateToAssistant == True and 'com.indigodomo.indigoserver' in newDev.globalProps:
			globalPropsDict = newDev.globalProps['com.indigodomo.indigoserver']
			if globalPropsDict.get('googleClientPublishHome', False) == True and globalPropsDict.get('googleClientSendUpdates', False) == True:
				try:
					# retrieve the device update from the server in the same format as the query for
					# the device status
					deviceUpdate = indigo.rawServerRequest("GetDevice", {"ID": newDev.id})

					# schedule a call to the Google Home Graph's update via the Cloud Function
					self.logger.info(f'Scheduling device update of {newDev.id} ({newDev.name}) with Google Home/Assistant')
					self.logger.debug(f'Sending device update: {dicttoxml.dicttoxml(deviceUpdate, True, "Device")}')
					self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(GOOGLEHOME_SENDDEVICEUPDATE, deviceUpdate))
				except:
					self.logger.exception(f'Failed to generate Google Home update for device {newDev.name}')

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
			if dev.sharedProps.get('googleClientPublishHome', False):
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
			
		publishedDeviceId = f'{valuesDict.get(u"publishedDevice", "")}'
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
			valuesDict["publishToGoogle"]            = device.sharedProps.get('googleClientPublishHome', False)
			valuesDict["deviceDetailsPublishedName"] = device.sharedProps.get('googleClientAsstName'   , '')
			valuesDict["deviceDetailsPublishedType"] = device.sharedProps.get('googleClientAsstType'   , '')
			valuesDict["sendUpdatesToGoogle"]        = device.sharedProps.get('googleClientSendUpdates', '')
			valuesDict["deviceDetailsPINCode"]       = device.sharedProps.get('googleClientPINCode'    , '')
		except:
			self.logger.exception('Failed to load published device properties')
		return valuesDict

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called whenever the user has clicked to update the published Google Home (such as
	# changing the device name or type)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def publishedHomeDevicesUpdate(self, valuesDict=None, typeId="", devId=0):
		try:
			device      = indigo.devices.get(int(valuesDict["publishedDevice"]), None)
			globalProps = device.sharedProps

			globalProps['googleClientPublishHome'] = valuesDict["publishToGoogle"]
			globalProps['googleClientAsstName']    = valuesDict["deviceDetailsPublishedName"]
			globalProps['googleClientAsstType']    = valuesDict["deviceDetailsPublishedType"]
			globalProps['googleClientSendUpdates'] = valuesDict["sendUpdatesToGoogle"]
			globalProps['googleClientPINCode']     = valuesDict["deviceDetailsPINCode"]
			device.replaceSharedPropsOnServer(globalProps)

			valuesDict["publishedDevice"]            = None
			valuesDict["publishToGoogle"]            = False
			valuesDict['publishedDeviceSelected']    = False
			valuesDict["deviceDetailsPublishedName"] = ''
			valuesDict["deviceDetailsPublishedType"] = None
			valuesDict["sendUpdatesToGoogle"]        = False
			valuesDict["deviceDetailsPINCode"]       = ''

			valuesDict["enableDeviceDetailUI"]       = False

			# let Google know that a synchronization is required
			
		except:
			self.logger.exception('Failed to update published device properties')
		return valuesDict

	#/////////////////////////////////////////////////////////////////////////////////////
	# API Action Handlers
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Sets the Setpoint of a thermostat using the current thermostat mode (heating or
	# cooling)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def apiSetThermostatSetpoint(self, action, dev=None, callerWaitingForResult=None):
		deviceId    = int(action.props["body_params"].get('deviceId', '0'))
		newSetpoint = float(action.props["body_params"].get('setpoint', '0.0'))
		isSuccess   = False
		message     = ''

		if deviceId == 0 or newSetpoint == 0.0:
			self.logger.warning('Unable to process API request to set thermostat setpoint due to missing or invalid arguments')
			message = 'Unable to process API request to set thermostat setpoint due to missing or invalid arguments'
		else:
			device = indigo.devices[deviceId]
			if device.hvacMode == indigo.kHvacMode.HeatCool or device.hvacMode == indigo.kHvacMode.ProgramHeatCool or device.hvacMode == indigo.kHvacMode.Cool or device.hvacMode == indigo.kHvacMode.ProgramCool:
				indigo.thermostat.setCoolSetpoint(deviceId, value=newSetpoint)
				isSuccess = True
			elif device.hvacMode == indigo.kHvacMode.Heat or device.hvacMode == indigo.kHvacMode.ProgramHeat:
				indigo.thermostat.setHeatSetpoint(deviceId, value=newSetpoint)
				isSuccess = True
			else:
				message = 'Thermostat is off or not in a mode that accepts setpoint changes'
		
		return f'{{ "result": "{isSuccess}", "message": "{message}" }}'

	#/////////////////////////////////////////////////////////////////////////////////////
	# Utility Routines
	#/////////////////////////////////////////////////////////////////////////////////////		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Processes the user requesting that the Google Home Graph re-sync the set of
	# published devices
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def requestResyncWithGoogle(self):
		# simply schedule a resynchronization request with the background processor
		self.logger.info('Scheduling re-synchronization request with Google Home/Assistant')
		self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(GOOGLEHOME_REQUESTSYNC))

	# /////////////////////////////////////////////////////////////////////////////////////
	# HTTP API Requests
	# /////////////////////////////////////////////////////////////////////////////////////
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# API call that allows the Android client to register itself against a specific Indigo
	# Android device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def register_android_device(self, action, dev=None, callerWaitingForResult = None):
		try:
			body_params = action.props.get("body_params", None)
			if body_params is None:
				body_params = action.props.get("url_query_args", indigo.Dict())

			device_id       = body_params.get("deviceId", "")
			pairing_id      = body_params.get("pairingId", "")
			allow_overwrite = int(body_params.get("allowOverwrite", 0))

			if device_id == "" or pairing_id == "":
				return {"status": 400}

			android_dev  = indigo.devices[int(device_id)]
			plugin_props = android_dev.pluginProps

			if plugin_props.get("deviceRegistrationId", "") == "" or allow_overwrite == 1:
				plugin_props["deviceRegistrationId"] = pairing_id
				android_dev.replacePluginPropsOnServer(plugin_props)
				android_dev.updateStateOnServer("isPaired", True, uiValue="Paired")
				command_response = "OK"
				indigo.server.log(f"Successfully paired Android device to Indigo Device {device_id}")
			else:
				indigo.server.log("Rejected device pairing - Indigo Device already paired to another Android device.", isError=True)
				command_response = "ERROR: Exception Processing Request"

			return {"status": 200, "content": command_response}
		except Exception as ex:
			return {"status": 500, "content": f"{ex}"}

	def unregister_android_device(self, action, dev=None, callerWaitingForResult=None):
		try:
			body_params = action.props.get("body_params", None)
			if body_params is None:
				body_params = action.props.get("url_query_args", indigo.Dict())

			device_id   = body_params.get("deviceId", "")
			pairing_id  = body_params.get("pairingId", "")

			android_dev  = indigo.devices[int(device_id)]
			plugin_props = android_dev.pluginProps

			if plugin_props.get("deviceRegistrationId", "") == pairing_id:
				plugin_props["deviceRegistrationId"] = ""
				android_dev.replacePluginPropsOnServer(plugin_props)
				android_dev.updateStateOnServer("isPaired", False, uiValue="Not Paired")
				command_response = "OK"
				indigo.server.log(f"Successfully un-aired Android device to Indigo Device {device_id}")
			else:
				indigo.server.log("Rejected device un-pairing request - Indigo Device not paired to device making the request", isError=True)
				command_response = "ERROR: Exception Processing Request"

			return {"status": 200, "content": command_response}
		except Exception as ex:
			return {"status": 500, "content": f"{ex}"}
