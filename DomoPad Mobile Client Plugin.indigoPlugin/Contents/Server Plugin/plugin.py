#! /usr/bin/env python
# -*- coding: utf-8 -*-
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////
# Domotics Pad Client Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	Indigo plugin designed to interface with the various Google services supported by
#   Domotics Pad, such as mobile clients and Google Home devices
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////


# /////////////////////////////////////////////////////////////////////////////////////////
# Python imports
# /////////////////////////////////////////////////////////////////////////////////////////
import cgi
from distutils.dir_util import copy_tree
import os
import re
import socket
import socketserver
import threading
import requests
from requests.auth import HTTPDigestAuth
import urllib.parse as qsparse

import RPFramework
import domoPadDevices
import googleHomeDevices


# /////////////////////////////////////////////////////////////////////////////////////////
# Constants and configuration variables
# /////////////////////////////////////////////////////////////////////////////////////////
INCLUDED_IWS_VERSION                           = (1, 5)
DOMOPADCOMMAND_SENDNOTIFICATION                = u'SendNotification'
DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION   = u'SendTextToSpeechNotification'
DOMOPADCOMMAND_CPDISPLAYNOTIFICATION           = u'SendCPDisplayRequest'
DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION = u'RequestDeviceStatusUpdate'


# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////
# Plugin
#	Primary Indigo plugin class that is universal for all devices (receivers) to be
#	controlled
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////
class Plugin(RPFramework.RPFrameworkPlugin):
	
	# /////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	# /////////////////////////////////////////////////////////////////////////////////////
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor called once upon plugin class creation; setup the device tracking
	# variables for later use
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		# RP framework base class's init method
		super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs, managedDeviceClassModule=domoPadDevices)

	# /////////////////////////////////////////////////////////////////////////////////////
	# Indigo control methods
	# /////////////////////////////////////////////////////////////////////////////////////
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# startup is called by Indigo whenever the plugin is first starting up (by a restart
	# of Indigo server or the plugin or an update
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def startup(self):
		super(Plugin, self).startup()
		
		# check the IWS plugin currently installed and see if we need to install or upgrade
		# to the version included with this plugin
		self.processIWSUpdateCheck()
			
		# create the socket listener server that will listen for incoming commands to
		# be sent to the Plugin
		try:
			host = u''
			port = int(self.getGUIConfigValue(RPFramework.GUI_CONFIG_PLUGINSETTINGS, "remoteCommandPort", "9176"))
			self.socketServer = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
			
			self.logger.debug("Starting up connection listener")
			self.socketServerThread = threading.Thread(target=self.socketServer.serve_forever)
			self.socketServerThread.daemon = True
			self.socketServerThread.start()
		except:
			self.exceptionLog()

		# tell the Indigo server that we want to be notificed of all device
		# updates (so we can push to Google)
		indigo.devices.subscribeToChanges()
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# When the plugin is shutting down we must take down the socket server so that the
	# secondary thread will exit
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def shutdown(self):
		super(Plugin, self).shutdown()
		if not (self.socketServer is None):
			self.socketServer.shutdown()

	# /////////////////////////////////////////////////////////////////////////////////////
	# Action/command processing routines
	# /////////////////////////////////////////////////////////////////////////////////////
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to handle any unknown commands at the plugin level; it
	# can/should be overridden in the plugin implementation (if needed)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handleUnknownPluginCommand(self, rpCommand, reQueueCommandsList):
		if rpCommand.commandName == DOMOPADCOMMAND_SENDNOTIFICATION:
			# we are using HTTPS to communicate with the Google Cloud Messaging service, so we must have
			# Indigo v6.1 in order to user
			if float(indigo.server.apiVersion) < 1.19:
				self.logger.error("Push notifications require Indigo v6.1 or later")
			else:
				self.logger.threaddebug(f"Push Notification Send Command: DevicePairID={rpCommand.commandPayload[0]}; Type={rpCommand.commandPayload[2]}; Message={rpCommand.commandPayload[1]}")
			
				# setup the defaults so that we know all of the parameters have a value...
				queryStringParams = {"devicePairingId": rpCommand.commandPayload[0],
									"notificationType": "Alert",
									"priority"        : rpCommand.commandPayload[2],
									"message"         : rpCommand.commandPayload[1],
									"action1Name"     : "",
									"action1Group"    : "",
									"action2Name"     : "",
									"action2Group"    : ""}

				# build the query string as it must be URL encoded
				if rpCommand.commandPayload[3] != "" and rpCommand.commandPayload[4] != "":
					self.logger.threaddebug(f"Push Notification Send Action 1: {rpCommand.commandPayload[3]} => {rpCommand.commandPayload[4]}")
					queryStringParams["action1Name"]      = f"{rpCommand.commandPayload[3]}"
					queryStringParams["action1Group"]     = f"{rpCommand.commandPayload[4]}"
					queryStringParams["notificationType"] = "ActionAlert"
					targetApiMethod = "sendActionablePushNotification"
				if rpCommand.commandPayload[5] != "" and rpCommand.commandPayload[6] != "":
					self.logger.threaddebug(f"Push Notification Send Action 2: {rpCommand.commandPayload[5]} => {rpCommand.commandPayload[6]}")
					queryStringParams["action2Name"]      = f"{rpCommand.commandPayload[5]}"
					queryStringParams["action2Group"]     = f"{rpCommand.commandPayload[6]}"
					queryStringParams["notificationType"] = "ActionAlert"

				push_url      = "https://com-duncanware-domopad.appspot.com/_ah/api/messaging/v1/sendActionablePushNotification"
				response      = requests.post(push_url, data=queryStringParams)
				response_code = response.status_code
				response_text = response.text

				self.logger.threaddebug(f"Push notification Response: [{response_code}] {response_text}")
			
				try:
					if response_code == 204:
						self.logger.debug("Push notification sent successfully")
					else:
						self.logger.error("Error sending push notification.")
				except:
					self.logger.exception("Error sending push notification.")
					
		elif rpCommand.commandName == DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION:
			self.logger.threaddebug(f"Speak Announcement Notification Send Command: DevicePairID={RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[0])}; Msg={RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[1])}")
			
			message_expanded = self.substituteIndigoValues(RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[1]), rpCommand.commandPayload[2], [])
			data_params      = {"devicePairingId": rpCommand.commandPayload[0], "message": message_expanded}
			push_url         = "https://com-duncanware-domopad.appspot.com/_ah/api/messaging/v1/sendAnnounceTextRequest"
			response         = requests.post(push_url, data=data_params)
			response_code    = response.status_code
			response_text    = response.text

			self.logger.threaddebug(f"Speak announcement notification response: [{response_code}] {response_text}")
		
			try:
				if response_code == 204:
					self.logger.debug("Speak announcement notification sent successfully")
				else:
					self.logger.error("Error sending speak announcement notification.")	
			except:
				self.logger.exception("Error sending speak announcement notification.")	
					
		elif rpCommand.commandName == DOMOPADCOMMAND_CPDISPLAYNOTIFICATION:
			self.logger.threaddebug(f"Control Page Display Notification Send Command: DevicePairID={RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[0])}; Page={RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[1])}")

			# load the control page name so that we may pass it along to the deviceId
			# (may be needed for notification purposes)
			requestedPage = indigo.rawServerRequest("GetControlPage", {"ID" : rpCommand.commandPayload[1]})
			cpPageName    = requestedPage["Name"] 
			
			data_params   = {"devicePairingId": rpCommand.commandPayload[0], "pageRequested": rpCommand.commandPayload[1], "pageName": cpPageName}
			push_url      = "https://com-duncanware-domopad.appspot.com/_ah/api/messaging/v1/sendControlPageDisplayRequest"
			response      = requests.post(push_url, data=data_params)
			response_code = response.status_code
			response_text = response.text

			self.logger.threaddebug(f"Control page display notification response: [{response_code}] {response_text}")
		
			try:
				if response_code == 204:
					self.logger.debug("Control page display notification sent successfully")
				else:
					self.logger.error("Error sending control page display notification.")	
			except:
				self.logger.exception("Error sending control page display notification.")	
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process the Send Notification action... it will queue up the
	# command for the plugin to process asynchronously
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processSendNotification(self, action):
		rpDevice             = self.managedDevices[action.deviceId]
		deviceRegistrationId = rpDevice.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		messageToSend        = self.substitute(action.props.get("message"))
		importanceLevel      = action.props.get("importanceLevel")
		
		action1Name  = action.props.get("action1Name" , "")
		action1Group = action.props.get("action1Group", "")
		action2Name  = action.props.get("action2Name" , "")
		action2Group = action.props.get("action2Group", "")		

		if deviceRegistrationId == "":
			self.logger.error(f"Unable to send push notification to {rpDevice.indigoDevice.deviceId}; the device is not paired.")
		else:
			self.logger.threaddebug(f"Queuing push notification command for {action.deviceId}")
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand(DOMOPADCOMMAND_SENDNOTIFICATION, commandPayload=(deviceRegistrationId, messageToSend, importanceLevel, action1Name, action1Group, action2Name, action2Group)))
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Speak Announcement command to an Android Device
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processSpeakAnnouncementNotification(self, action):
		rpDevice             = self.managedDevices[action.deviceId]
		deviceRegistrationId = rpDevice.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		announcementMsg      = action.props.get("announcement", "")
		
		if deviceRegistrationId == "":
			self.logger.error(f"Unable to send speak announcement request notification to {rpDevice.indigoDevice.deviceId}; the device is not paired.")
		elif announcementMsg == "":
			self.logger.error(f"Unable to send speak announcement request notification to {rpDevice.indigoDevice.deviceId}; no announcement text was entered.")
		else:
			self.logger.threaddebug(f"Queuing peak announcement request notification command for {action.deviceId}")
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand(DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION, commandPayload=(deviceRegistrationId, announcementMsg, rpDevice)))
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Control Page Display Command to a Android device (in
	# order to request that a specific control page be shown on the device)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processControlPageDisplayNotification(self, action):
		rpDevice             = self.managedDevices[action.deviceId]
		deviceRegistrationId = rpDevice.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		controlPageId        = int(action.props.get("controlPageId", "0"))
		
		if deviceRegistrationId == "":
			self.logger.error(f"Unable to send control page display request notification to {rpDevice.indigoDevice.deviceId}; the device is not paired.")
		elif controlPageId <= 0:
			self.logger.error(f"Unable to send control page display request notification to {rpDevice.indigoDevice.deviceId}; no control page was selected.")
		else:
			self.logger.threaddebug(f"Queuing control page display request notification command for {action.deviceId}")
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand(DOMOPADCOMMAND_CPDISPLAYNOTIFICATION, commandPayload=(deviceRegistrationId, controlPageId)))
	
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Update Device Status request notification in order to ask
	# the device to update its status immediately (instead of waiting for its normal 15
	# minute update interval)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processRequestDeviceStatusNotification(self, action):
		self.requestDeviceStatusNotification(action.deviceId)

	# /////////////////////////////////////////////////////////////////////////////////////
	# Plugin Event Overrides
	# /////////////////////////////////////////////////////////////////////////////////////
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called whenever a device updates... if it is one of the monitored devices then
	# send the updates to Google Home
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def deviceUpdated(self, origDev, newDev):
		self.logger.info(f"Received device update for {newDev.name}")

		# call the base's implementation first just to make sure all the right things happen elsewhere
		indigo.PluginBase.deviceUpdated(self, origDev, newDev)

	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called back from the configuration dialog whenever the user has
	# clicked the button to clear the value of the device pairing
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clearDevicePairing(self, valuesDict, typeId, devId):
		valuesDict["deviceRegistrationId"] = ""
		return valuesDict
		
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
		valuesDict["action2Name"]  = ""
		valuesDict["action2Group"] = ""
		return valuesDict

	# /////////////////////////////////////////////////////////////////////////////////////
	# Utility Routines
	# /////////////////////////////////////////////////////////////////////////////////////
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will perform the update check and execute the update if needed
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processIWSUpdateCheck(self):
		# check the IWS plugin currently installed and see if we need to install or upgrade
		# to the version included with this plugin
		currentIWSPluginVersion = self.getIWSPluginVersion()
		self.logger.debug(f"Current IWS Plugin: v{currentIWSPluginVersion[0]}.{currentIWSPluginVersion[1]}")
		self.logger.debug(f"Included IWS Plugin: v{INCLUDED_IWS_VERSION[0]}.{INCLUDED_IWS_VERSION[1]}")
		
		if INCLUDED_IWS_VERSION[0] > currentIWSPluginVersion[0] or (INCLUDED_IWS_VERSION[0] == currentIWSPluginVersion[0] and INCLUDED_IWS_VERSION[1] > currentIWSPluginVersion[1]):
			# we need to perform the IWS upgrade now
			self.updateIWSPlugin()
	
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine obtains the current version of the IWS plugin as a tuple of version
	# numbers
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getIWSPluginVersion(self):
		try:
			versionUrl    = "http://localhost:{self.pluginPrefs.get(u'indigoPort')}/AndroidClientHelper/getVersionInfo"
			response      = requests.get(versionUrl, auth=HTTPDigestAuth(self.pluginPrefs.get("indigoUsername"), self.pluginPrefs.get("indigoPassword")))
			responseTText = response.text

			regex = re.compile("^v(?P<major>\d+)\.(?P<minor>\d+)$")
			match = regex.search(responseTText)
			
			if match is None:
				self.logger.warning(f"Connected to IWS, but current version not returned: {responseTText}")
				return (0,0)
			else:
				return (int(match.groupdict().get("major")), int(match.groupdict().get("minor")))
		except:
			# when an exception occurs we are going to have to assume that we need to copy
			# the plugin over...
			if self.debugLevel != RPFramework.DEBUGLEVEL_NONE:
				self.logger.error("Failed to retrieve current IWS plugin version:")
			else:
				self.logger.warning("Failed to retrieve current IWS plugin version:")
			return (0,0)
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will perform an update to the current IWS plugin by copying over the
	# version from this Plugin
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def updateIWSPlugin(self):	
		self.logger.info("Performing update of DomoPad''s IWS plugin...")
		
		# determine the IWS server directory
		indigoInstallPath = indigo.server.getInstallFolderPath()
		pluginBasePath    = os.getcwd()
		
		mainPluginHome = os.path.join(pluginBasePath, "AndroidClientHelper") 
		iwsPluginHome  = os.path.join(indigoInstallPath, "Web Assets/plugins/AndroidClientHelper")
		
		self.logger.info(f"Source IWS directory: {mainPluginHome}")
		self.logger.info(f"Target IWS directory: {iwsPluginHome}")
		
		# ensure that we have the correct source directory...
		if os.path.exists(mainPluginHome) == False:
			self.logger.error("ERROR: Source directory not found!  AndroidClientHelper IWS plugin install could not complete.")
			return
			
		# execute the directory copy now...
		try:
			copy_tree(mainPluginHome, iwsPluginHome, preserve_mode=1)
			self.logger.info("AndroidClientHelper successfully installed/updated. Restarting Indigo IWS server to complete install.")
			self.restartIWS()
		except:
			self.logger.error("Error copying AndroidClientHelper, AndroidClientHelper IWS plugin install could not complete.")
		
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will restart the IWS so that the plugin may be updated...
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def restartIWS(self):
		try:
			baseUrl    = f"http://localhost:{self.pluginPrefs.get('indigoPort')}/"
			restartUrl = baseUrl + "indigocommand?name=restart"
			response   = requests.get(restartUrl, auth=HTTPDigestAuth(self.pluginPrefs.get("indigoUsername"), self.pluginPrefs.get("indigoPassword")))
		except:
			pass
			
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Update Device Status request notification in order to ask
	# the device to update its status immediately (instead of waiting for its normal 15
	# minute update interval)
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def requestDeviceStatusNotification(self, deviceId):
		rpDevice             = self.managedDevices[deviceId]
		deviceRegistrationId = rpDevice.indigoDevice.pluginProps.get("deviceRegistrationId", "")
		
		if deviceRegistrationId == "":
			self.logger.error(f"Unable to send status update request notification to {rpDevice.indigoDevice.deviceId}; the device is not paired.")
		else:
			self.logger.threaddebug(f"Queuing device status update request notification command for {RPFramework.RPFrameworkUtils.to_unicode(deviceId)}")
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand(DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION, commandPayload=deviceRegistrationId))
		
		
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////
# Utility classes
#    This class does the work of fielding and responding to requests sent in to the 
#    remote/monitoring port
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////
class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called by the server to handle the request
	# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle(self):
		try:
			# self.request.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
			requestReceived = self.request.recv(1024).decode('utf-8')
		
			# attempt to parse the request to determine how to proceed from here
			commandParser = re.compile("GET (/{0,1}AndroidClientHelper){0,1}/{0,1}(?P<commandName>\w+)(\?(?P<arguments>.+)){0,1}\s+HTTP")
			commandMatch  = commandParser.search(requestReceived)
			
			# send back the proper HTML headers so that the browser knows the connection is good...
			self.request.sendall(b"HTTP/1.0 200 OK\nContent-Type: text/html\n\n")
			
			commandResponse = ""
			if commandMatch is None:
				commandResponse = "ERROR: No command received"
			else:
				commandName = commandMatch.groupdict().get("commandName")
				indigo.server.log(f"Process command: {commandName}")
			
				if commandName == "executePluginAction":
					commandArguments = self.parseArguments(commandMatch.groupdict().get("arguments"))
					# TODO: the plugin action parameters will be encrypted on the action line as an argument
				
					# required parameters are the plugin ID and device ID
					pluginId    = commandArguments.get("pluginId")[0]
					deviceId    = commandArguments.get("deviceId")[0]
					actionId    = commandArguments.get("actionId")[0]
					actionProps = commandArguments.get("actionProps")[0]
					indigo.server.log(actionProps)
					
					# get the plugin that was requested from the indigo server... if this is a domoPadMobileClient then we need
					# to access the plugin object directly to avoid an error dispatching the executeAction
					if pluginId == "com.duncanware.domoPadMobileClient":
						indigoPlugin = indigo.activePlugin
						
						if actionId == "sendUpdateStatusRequestNotification":
							indigoPlugin.requestDeviceStatusNotification(int(deviceId))
						else:
							indigo.server.log(f"Unknown action received for domoPadMobileClient: {actionId}")
					else:
						indigoPlugin = indigo.server.getPlugin(pluginId)
						if indigoPlugin is None:
							commandResponse = "ERROR: Invalid plugin specified"
						elif (actionProps is None) or (len(actionProps) == 0):
							indigoPlugin.executeAction(actionId, deviceId=int(deviceId))
							commandResponse = "OK"
						else:
							actionPropDict = eval(actionProps)
							indigoPlugin.executeAction(actionId, deviceId=int(deviceId), props=actionPropDict)
							commandResponse = "OK"

				elif commandName == "registerAndroidDevice":
					commandArguments = self.parseArguments(commandMatch.groupdict().get("arguments"))
					deviceId         = commandArguments.get("deviceId")[0]
					pairingId        = commandArguments.get("pairingId")[0]
					allowOverwrite   = int(commandArguments.get("allowOverwrite")[0])
					
					indigoAndroidDev = indigo.devices[int(deviceId)]
					pluginProps      = indigoAndroidDev.pluginProps;
					
					if pluginProps.get("deviceRegistrationId", "") == "" or allowOverwrite == 1:
						pluginProps["deviceRegistrationId"] = pairingId
						indigoAndroidDev.replacePluginPropsOnServer(pluginProps)
						indigoAndroidDev.updateStateOnServer("isPaired", True, uiValue="Paired")
						commandResponse = "OK"
						indigo.server.log(f"Successfully paired Android device to Indigo Device {deviceId}")
					else:
						indigo.server.log("Rejected device pairing - Indigo Device already paired to another Android device.", isError=True)
						commandResponse = "ERROR: Exception Processing Request"

				elif commandName == "unregisterAndroidDevice":	
					commandArguments = self.parseArguments(commandMatch.groupdict().get("arguments"))
					deviceId         = commandArguments.get("deviceId")[0]
					pairingId        = commandArguments.get("pairingId")[0]
					
					indigoAndroidDev = indigo.devices[int(deviceId)]
					pluginProps      = indigoAndroidDev.pluginProps
					
					# only de-register if the pairing IDs currently match...
					if pluginProps.get("deviceRegistrationId", "") == pairingId:
						pluginProps["deviceRegistrationId"] = ""
						indigoAndroidDev.replacePluginPropsOnServer(pluginProps)
						indigoAndroidDev.updateStateOnServer("isPaired", False, uiValue="Not Paired")
						commandResponse = "OK"
						indigo.server.log(f"Successfully un-paired Android device to Indigo Device {deviceId}")
					else:
						indigo.server.log(f"Rejected device un-pairing - Indigo Device does not match Android device.", isError=True)
						commandResponse = "ERROR: Exception Processing Request"

				elif commandName == u'updateMobileDeviceStates':
					commandArguments = self.parseArguments(commandMatch.groupdict().get("arguments"))
					pairingId        = commandArguments.get("pairingId")[0]
					modelName        = commandArguments.get("deviceModel")[0]
					batteryStatus    = commandArguments.get("batteryStatus")[0]
					batteryLevel     = int(commandArguments.get("batteryLevel")[0])
					longitude        = commandArguments.get("longitude")[0]
					latitude         = commandArguments.get("latitude")[0]
					locationFixTime  = commandArguments.get("locationFix", (""))[0]
					
					# we need to find the proper devices based upon the pairing id; the default response will be
					# that the device was not found
					commandResponse = "ERROR: Device not found"
					devIter = indigo.devices.iter(filter="com.duncanware.domoPadMobileClient.domoPadAndroidClient")
					for dev in devIter:
						if dev.pluginProps.get("deviceRegistrationId", "") == pairingId:
							dev.updateStateOnServer("modelName", modelName)
							dev.updateStateOnServer("batteryStatus", batteryStatus)
							dev.updateStateOnServer("batteryLevel", batteryLevel)
							dev.updateStateOnServer("longitude", longitude)
							dev.updateStateOnServer("latitude", latitude)
							dev.updateStateOnServer("locationFixTime", locationFixTime)
							
							commandResponse = "OK"
							
					if commandResponse != "OK":
						indigo.server.log(f"Received status update for unknown device with Pairing ID: {pairingId}", isError=True)
		
			# send whatever response was generated back to the caller
			self.request.sendall(commandResponse)
		
		except Exception as e:
			indigo.server.log(f"DomoPad Plugin Exception: Error processing remote request: {e}")
			self.request.sendall("ERROR: Exception Processing Request")
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will split out the "arguments" section of the request into name/value
	# pairs as standard query string arguments; note that this is now (Python 2.6+) in
	# the urlparse module and must be updated if python updates
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def parseArguments(self, qs_args):
		return qsparse.parse_qs(qs_args, keep_blank_values=True)


# /////////////////////////////////////////////////////////////////////////////////////////
# This class creates a concrete threaded TCP server in order to listen to and respond
# to requests from HousePad or the HousePad IWS plugin
# /////////////////////////////////////////////////////////////////////////////////////////
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	def serve_forever(self):
		self.__serving = True
		while self.__serving:
			self.handle_request()
			
	def shutdown(self):
		self.__serving = False
		shutdownSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		shutdownSocket.connect(self.server_address)
		shutdownSocket.shutdown(socket.SHUT_RDWR)
		shutdownSocket.close()
