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
from RPFramework.RPFrameworkCommand import RPFrameworkCommand

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
				requestBody = {"intent": "googlehomegraph.UPDATE_DEVICE", "payload": {"agentId": reflectorUrl, "deviceUpdate": deviceUpdateXml}}
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
			except:
				self.logger.exception('Failed to request that device definitions re-synchronize with Google Home/Assistant')

		elif rpCommand.commandName == DOMOPADCOMMAND_SENDNOTIFICATION:
			self.logger.threaddebug(f"Push Notification Send Command: DevicePairID={rpCommand.commandPayload[0]}; Type={rpCommand.commandPayload[2]}; Message={rpCommand.commandPayload[1]}")

			# set up the defaults so that we know all the parameters have a value...
			query_string_params = { "devicePairingId": rpCommand.commandPayload[0],
									"notificationType": "Alert",
									"priority": rpCommand.commandPayload[2],
									"message": f"{rpCommand.commandPayload[1]}"}
			query_string_params["action1Name"] = ""
			query_string_params["action1Group"] = ""
			query_string_params["action2Name"] = ""
			query_string_params["action2Group"] = ""

			# build the query string as it must be URL encoded
			if rpCommand.commandPayload[3] != "" and rpCommand.commandPayload[4] != "":
				self.logger.threaddebug(f"Push Notification Send Action 1: {rpCommand.commandPayload[3]} => {rpCommand.commandPayload[4]}")
				query_string_params["action1Name"] = f"{rpCommand.commandPayload[3]}"
				query_string_params["action1Group"] = f"{rpCommand.commandPayload[4]}"
				query_string_params["notificationType"] = "ActionAlert"
			if rpCommand.commandPayload[5] != "" and rpCommand.commandPayload[6] != "":
				self.logger.threaddebug(f"Push Notification Send Action 2: {rpCommand.commandPayload[5]} => {rpCommand.commandPayload[6]}")
				query_string_params["action2Name"] = f"{rpCommand.commandPayload[5]}"
				query_string_params["action2Group"] = f"{rpCommand.commandPayload[6]}"
				query_string_params["notificationType"] = "ActionAlert"
			self.logger.threaddebug(f"Push Notification Payload={json.dumps(query_string_params)}")

			# this routine is executed asynchronously and thus can directly send the
			# request to the server
			api_endpoint_url = "https://com-duncanware-domopad.appspot.com/_ah/api/messaging/v1/sendActionablePushNotification"
			try:
				response = requests.post(api_endpoint_url, data=json.dumps(query_string_params))
				self.logger.threaddebug(f"Push notification Response: [{response.status_code}] {response.text}")

				if response.status_code == 204:
					self.logger.debug("Push notification sent successfully")
				else:
					self.logger.error("Error sending push notification.")
			except:
				self.logger.exception("Error sending push notification.")

		elif rpCommand.commandName == DOMOPADCOMMAND_CPDISPLAYNOTIFICATION:
			self.logger.threaddebug(f"Control Page Display Request Command: Id={rpCommand.commandPayload[0]}; Page={rpCommand.commandPayload[1]}")

			# load the control page name so that we may pass it along to the device
			requested_page = indigo.rawServerRequest('GetControlPage', {"ID": rpCommand.commandPayload[1]})
			cp_page_name   = requested_page["Name"]
			query_string_params = {"devicePairingId": rpCommand.commandPayload[0], "pageRequested": rpCommand.commandPayload[1], "pageName": cp_page_name}

			api_endpoint_url = "https://com-duncanware-domopad.appspot.com/_ah/api/messaging/v1/sendControlPageDisplayRequest"
			try:
				response = requests.post(api_endpoint_url, data=json.dumps(query_string_params))
				self.logger.threaddebug(f"Control Page Display Request Response: [{response.status_code}] {response.text}")

				if response.status_code == 204:
					self.logger.debug("Control page display request sent successfully")
				else:
					self.logger.error("Error sending control page display request")
			except:
				self.logger.exception("Error sending control page display request")

		# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process the Send Notification action... it will queue up the
	# command for the plugin to process asynchronously
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processSendNotification(self, action):
		rp_device        = self.managedDevices[action.deviceId]
		registration_id  = rp_device.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		message          = self.substitute(action.props.get("message"))
		importance_level = action.props.get("importanceLevel")

		action1_name  = action.props.get("action1Name" , "")
		action1_group = action.props.get("action1Group", "")
		action2_name  = action.props.get("action2Name" , "")
		action2_group = action.props.get("action2Group", "")

		if registration_id == "":
			indigo.server.log(f"Unable to send push notification to {rp_device.indigoDevice.deviceId}; the device is not paired.", isError=True)
		else:
			self.logger.threaddebug(f"Queuing push notification command for {action.deviceId}")
			self.pluginCommandQueue.put(RPFrameworkCommand(DOMOPADCOMMAND_SENDNOTIFICATION, commandPayload=(
				registration_id, message, importance_level, action1_name, action1_group, action2_name, action2_group)))

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the user has clicked to clear his/her selection of
	# an action in slot 1
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clearNotificationAction1(self, valuesDict, typeId, devId):
		valuesDict["action1Name"]  = ""
		valuesDict["action1Group"] = ""
		return valuesDict

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the user has clicked to clear his/her selection of
	# an action in slot 2
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clearNotificationAction2(self, valuesDict, typeId, devId):
		valuesDict["action2Name"] = ""
		valuesDict["action2Group"] = ""
		return valuesDict

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Speak Announcement command to an Android Device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processSpeakAnnouncementNotification(self, action):
		rp_device = self.managedDevices[action.deviceId]
		device_registration_id = rp_device.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		announcement_msg = action.props.get("announcement", "")

		if device_registration_id == "":
			self.logger.error(f"Unable to send speak announcement request notification to {rp_device.indigoDevice.deviceId}; the device is not paired.")
		elif announcement_msg == "":
			self.logger.error(f"Unable to send speak announcement request notification to {rp_device.indigoDevice.deviceId}; no announcement text was entered.")
		else:
			self.logger.threaddebug("Queuing peak announcement request notification command for {action.deviceId}")
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION, commandPayload=(device_registration_id, announcement_msg, rp_device)))

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Control Page Display Command to a Android device (in
	# order to request that a specific control page be shown on the device)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processControlPageDisplayNotification(self, action):
		rp_device = self.managedDevices[action.deviceId]
		device_registration_id = rp_device.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		control_page_id = int(action.props.get("controlPageId", "0"))

		if device_registration_id == "":
			self.logger.error(f"Unable to send control page display request notification to {rp_device.indigoDevice.deviceId}; the device is not paired.")
		elif control_page_id <= 0:
			self.logger.error(f"Unable to send control page display request notification to {rp_device.indigoDevice.deviceId}; no control page was selected.")
		else:
			self.logger.threaddebug(f"Queuing control page display request notification command for {action.deviceId}")
			self.pluginCommandQueue.put(RPFrameworkCommand(DOMOPADCOMMAND_CPDISPLAYNOTIFICATION, commandPayload=(device_registration_id, control_page_id)))

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Update Device Status request notification in order to ask
	# the device to update its status immediately (instead of waiting for its normal 15
	# minute update interval)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processRequestDeviceStatusNotification(self, action):
		#requestDeviceStatusNotification(action.deviceId)
		pass

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

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# When called, clears the current device pairing ID, disabling push notification and
	# updates from the old device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clearDevicePairing(self, valuesDict, typeId, devId):
		valuesDict["deviceRegistrationId"] = ""
		return valuesDict

	#/////////////////////////////////////////////////////////////////////////////////////
	# API Action Handlers
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Sets the Setpoint of a thermostat using the current thermostat mode (heating or
	# cooling)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def set_thermostat_setpoint(self, action, dev=None, callerWaitingForResult=None):
		try:
			device_id    = int(action.props["body_params"].get('deviceId', '0'))
			new_setpoint = float(action.props["body_params"].get('setpoint', '0.0'))
			is_success   = False
			message      = ''

			if device_id == 0 or new_setpoint == 0.0:
				self.logger.warning('Unable to process API request to set thermostat setpoint due to missing or invalid arguments')
				message = 'Unable to process API request to set thermostat setpoint due to missing or invalid arguments'
			else:
				device = indigo.devices[device_id]
				if device.hvacMode == indigo.kHvacMode.HeatCool or device.hvacMode == indigo.kHvacMode.ProgramHeatCool or device.hvacMode == indigo.kHvacMode.Cool or device.hvacMode == indigo.kHvacMode.ProgramCool:
					indigo.thermostat.setCoolSetpoint(device_id, value=new_setpoint)
					is_success = True
				elif device.hvacMode == indigo.kHvacMode.Heat or device.hvacMode == indigo.kHvacMode.ProgramHeat:
					indigo.thermostat.setHeatSetpoint(device_id, value=new_setpoint)
					is_success = True
				else:
					message = 'Thermostat is off or not in a mode that accepts setpoint changes'

			return f'{{ "result": "{is_success}", "message": "{message}" }}'
		except Exception as ex:
			self.logger.exception(f"Failed to set thermostat set point via API: {ex}")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# API call that allows the Android client to register itself against a specific Indigo
	# Android device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def register_android_device(self, action, dev=None, callerWaitingForResult=None):
		try:
			body_params = action.props["body_params"] if "body_params" in action.props else action.props["url_query_args"]
			device_id = body_params.get("deviceId", "")
			pairing_id = body_params.get("pairingId", "")
			overwrite = int(body_params.get("allowOverwrite", 0))

			if device_id == "" or pairing_id == "":
				return {"status": 400, "content": "Invalid or missing parameters supplied to pairing request"}

			android_dev = indigo.devices[int(device_id)]
			plugin_props = android_dev.pluginProps

			if plugin_props.get("deviceRegistrationId", "") == "" or overwrite == 1:
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
			self.logger.error("Failed to register android device via API")
			return {"status": 500, "content": f"{ex}"}

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# API call that allows the Android client to de-register itself against a device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def unregister_android_device(self, action, dev=None, callerWaitingForResult=None):
		try:
			body_params = action.props["body_params"] if "body_params" in action.props else action.props["url_query_args"]
			device_id = body_params.get("deviceId", "")
			pairing_id = body_params.get("pairingId", "")

			android_dev = indigo.devices[int(device_id)]
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
			self.logger.error("Unable to de-register Android device via API")
			return {"status": 500, "content": f"{ex}"}

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# API call allowing a client to update its status (battery, location, etc.)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def update_client_status(self, action, dev=None, callerWaitingForResult=None):
		try:
			body_params    = action.props["body_params"] if "body_params" in action.props else action.props["url_query_args"]
			pairing_id     = body_params.get("pairingId", "")
			device_model   = body_params.get("deviceModel", "")
			battery_status = body_params.get("batteryStatus", "")
			battery_level  = int(body_params.get("batteryLevel", "0"))
			longitude      = body_params.get("longitude", "")
			latitude       = body_params.get("latitude", "")
			location_time  = body_params.get("locationFixTime")

			# we need to find the proper devices based upon the pairing id; the default response will be
			# that the device was not found
			command_response = "ERROR: Device not found"
			dev_iter = indigo.devices.iter(filter="com.duncanware.domoPadMobileClient.domoPadAndroidClient")
			for dev in dev_iter:
				if dev.pluginProps.get('deviceRegistrationId', '') == pairing_id:
					updated_states = [
						{"key": "modelName", "value": device_model},
						{"key": "batteryStatus", "value": battery_status},
						{"key": "batteryLevel", "value": battery_level},
						{"key": "longitude", "value": longitude},
						{"key": "latitude", "value": latitude},
						{"key": "locationFixTime", "value": location_time}
					]
					dev.updateStatesOnServer(updated_states)
					command_response = "OK"

			if command_response != "OK":
				self.logger.error(f"Received status update for unknown device with Pairing ID: {pairing_id}")
			return {"status": 200, "content": command_response}
		except Exception as ex:
			self.logger.exception("Failed to update mobile client status via API")
			return {"status": 500, "content": f"Failed to update mobile client status: {ex}"}

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
