#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################################
# Domotics Pad Mobile Client Plugin by RogueProeliator <rp@rogueproeliator.com>
# Indigo plugin designed to interface with the various Google services supported by
# Domotics Pad, such as mobile clients and Google Home devices
#######################################################################################

# region Python imports
import json
import requests

import RPFramework
import domoPadDevices
import dicttoxml

from RPFramework.RPFrameworkPlugin import RPFrameworkPlugin
from RPFramework.RPFrameworkCommand import RPFrameworkCommand
# endregion

# region Constants and configuration variables
DOMOPADCOMMAND_SENDNOTIFICATION                = "SendNotification"
DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION   = "SendTextToSpeechNotification"
DOMOPADCOMMAND_CPDISPLAYNOTIFICATION           = "SendCPDisplayRequest"
DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION = "RequestDeviceStatusUpdate"
# endregion


#######################################################################################
# Plugin
# Primary Indigo plugin class that is universal for all devices (receivers) to be
# controlled
#######################################################################################
class Plugin(RPFrameworkPlugin):
	
	#######################################################################################
	# region Class construction and destruction methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class creation; setup the device tracking
	# variables for later use
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs):
		# RP framework base class's init method
		super().__init__(plugin_id, plugin_display_name, plugin_version, plugin_prefs, managed_device_class_module=domoPadDevices)

		# initialize the member variable that tracks whether we are reporting device
		# states back to Google Home
		self.report_state_to_assistant = plugin_prefs.get("sendUpdatesToGoogle", False)

	# endregion
	#######################################################################################

	#######################################################################################
	# region Indigo control methods
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# startup is called by Indigo whenever the plugin is first starting up (by a restart
	# of Indigo server or the plugin or an update
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def startup(self):
		super(Plugin, self).startup()

	# endregion
	#######################################################################################

	#######################################################################################
	# region Action/command processing routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to handle any unknown commands at the plugin level; it
	# can/should be overridden in the plugin implementation (if needed)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle_unknown_plugin_command(self, rp_command, requeue_commands_list):
		if rp_command.command_name == DOMOPADCOMMAND_SENDNOTIFICATION:
			self.logger.threaddebug(f"Push Notification Send Command: DevicePairID={rp_command.command_payload[0]}; Type={rp_command.command_payload[2]}; Message={rp_command.command_payload[1]}")

			# set up the defaults so that we know all the parameters have a value...
			query_string_params = { "devicePairingId": rp_command.command_payload[0],
									"notificationType": "Alert",
									"priority": rp_command.command_payload[2],
									"message": f"{rp_command.command_payload[1]}"}
			query_string_params["action1Name"]  = ""
			query_string_params["action1Group"] = ""
			query_string_params["action2Name"]  = ""
			query_string_params["action2Group"] = ""

			# build the query string as it must be URL encoded
			if rp_command.command_payload[3] != "" and rp_command.command_payload[4] != "":
				self.logger.threaddebug(f"Push Notification Send Action 1: {rp_command.command_payload[3]} => {rp_command.command_payload[4]}")
				query_string_params["action1Name"] = f"{rp_command.command_payload[3]}"
				query_string_params["action1Group"] = f"{rp_command.command_payload[4]}"
				query_string_params["notificationType"] = "ActionAlert"
			if rp_command.command_payload[5] != "" and rp_command.command_payload[6] != "":
				self.logger.threaddebug(f"Push Notification Send Action 2: {rp_command.command_payload[5]} => {rp_command.command_payload[6]}")
				query_string_params["action2Name"] = f"{rp_command.command_payload[5]}"
				query_string_params["action2Group"] = f"{rp_command.command_payload[6]}"
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

		elif rp_command.command_name == DOMOPADCOMMAND_CPDISPLAYNOTIFICATION:
			self.logger.threaddebug(f"Control Page Display Request Command: Id={rp_command.command_payload[0]}; Page={rp_command.command_payload[1]}")

			# load the control page name so that we may pass it along to the device
			requested_page = indigo.rawServerRequest("GetControlPage", {"ID": rp_command.command_payload[1]})
			cp_page_name   = requested_page["Name"]
			query_string_params = {"devicePairingId": rp_command.command_payload[0], "pageRequested": rp_command.command_payload[1], "pageName": cp_page_name}

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

		elif rp_command.command_name == DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION:
			self.logger.threaddebug(f"Device Status Update Request: Device Id={rp_command.command_payload}")
			query_string_params = {"devicePairingId": rp_command.command_payload}

			api_endpoint_url = "https://com-duncanware-domopad.appspot.com/_ah/api/messaging/v1/sendDeviceStatusUpdateRequest"
			try:
				response = requests.post(api_endpoint_url, data=json.dumps(query_string_params))
				self.logger.threaddebug(f"Device Status Update Request Response: [{response.status_code}] {response.text}")

				if response.status_code == 204:
					self.logger.debug("Device status update request sent successfully")
				else:
					self.logger.error("Error sending device status update request")
			except:
				self.logger.exception("Error requesting device status update")

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process the Send Notification action... it will queue up the
	# command for the plugin to process asynchronously
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def process_send_notification(self, action):
		rp_device        = self.managed_devices[action.deviceId]
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
			self.plugin_command_queue.put(RPFrameworkCommand(DOMOPADCOMMAND_SENDNOTIFICATION, command_payload=(
				registration_id, message, importance_level, action1_name, action1_group, action2_name, action2_group)))

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the user has clicked to clear his/her selection of
	# an action in slot 1
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clear_notification_action_1(self, values_dict, type_id, dev_id):
		values_dict["action1Name"]  = ""
		values_dict["action1Group"] = ""
		return values_dict

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the user has clicked to clear his/her selection of
	# an action in slot 2
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clear_notification_action_2(self, values_dict, type_id, dev_id):
		values_dict["action2Name"]  = ""
		values_dict["action2Group"] = ""
		return values_dict

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Speak Announcement command to an Android Device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def process_speak_announcement_notification(self, action):
		rp_device = self.managed_devices[action.deviceId]
		device_registration_id = rp_device.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		announcement_msg = action.props.get("announcement", "")

		if device_registration_id == "":
			self.logger.error(f"Unable to send speak announcement request notification to {rp_device.indigoDevice.deviceId}; the device is not paired.")
		elif announcement_msg == "":
			self.logger.error(f"Unable to send speak announcement request notification to {rp_device.indigoDevice.deviceId}; no announcement text was entered.")
		else:
			self.logger.threaddebug("Queuing peak announcement request notification command for {action.deviceId}")
			self.plugin_command_queue.put(RPFrameworkCommand(DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION, command_payload=(device_registration_id, announcement_msg, rp_device)))

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Control Page Display Command to a Android device (in
	# order to request that a specific control page be shown on the device)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def process_control_page_display_notification(self, action):
		rp_device = self.managed_devices[action.deviceId]
		device_registration_id = rp_device.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		control_page_id = int(action.props.get("controlPageId", "0"))

		if device_registration_id == "":
			self.logger.error(f"Unable to send control page display request notification to {rp_device.indigoDevice.deviceId}; the device is not paired.")
		elif control_page_id <= 0:
			self.logger.error(f"Unable to send control page display request notification to {rp_device.indigoDevice.deviceId}; no control page was selected.")
		else:
			self.logger.threaddebug(f"Queuing control page display request notification command for {action.deviceId}")
			self.plugin_command_queue.put(RPFrameworkCommand(DOMOPADCOMMAND_CPDISPLAYNOTIFICATION, command_payload=(device_registration_id, control_page_id)))

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Update Device Status request notification in order to ask
	# the device to update its status immediately (instead of waiting for its normal
	# 15-minute update interval)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def request_device_status_update(self, action):
		rp_device = self.managed_devices[action.deviceId]
		device_registration_id = rp_device.indigoDevice.pluginProps.get("deviceRegistrationId", "")

		if device_registration_id == "":
			self.logger.error(f"Unable to send status update request to {rp_device.indigoDevice.deviceId}; the device is not paired.")
		else:
			self.logger.threaddebug(f"Queuing device status update request notification command for {action.deviceId}")
			self.plugin_command_queue.put(RPFrameworkCommand(DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION, command_payload=device_registration_id))

	# endregion
	#######################################################################################

	#######################################################################################
	# region Configuration Dialog Callback Routines
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# When called, clears the current device pairing ID, disabling push notification and
	# updates from the old device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clear_device_pairing(self, values_dict, type_id, dev_id):
		values_dict["deviceRegistrationId"] = ""
		return values_dict

	# endregion
	#######################################################################################

	#######################################################################################
	# region API Action Handlers
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# API call that allows the Android client to register itself against a specific Indigo
	# Android device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def register_android_device(self, action, dev=None, caller_waiting_for_result=None):
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
	def unregister_android_device(self, action, dev=None, caller_waiting_for_result=None):
		try:
			body_params = action.props["body_params"] if "body_params" in action.props else action.props["url_query_args"]
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
			self.logger.error("Unable to de-register Android device via API")
			return {"status": 500, "content": f"{ex}"}

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# API call allowing a client to update its status (battery, location, etc.)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def update_client_status(self, action, dev=None, caller_waiting_for_result=None):
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
				if dev.pluginProps.get("deviceRegistrationId", "") == pairing_id:
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

	# endregion
	#######################################################################################
