#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# DomoPad Android Client Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	Indigo plugin designed to interface with the DomoPad Mobile Client in order to
#	provide backend services to the client
#	
#	Version 0.8.15:
#		Initial release of the DomoPad-branded plugin to Indigo users
#
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
# Python imports
#/////////////////////////////////////////////////////////////////////////////////////////
import cgi
from distutils.dir_util import copy_tree
import httplib
import os
import re
import simplejson as json
import socket
import SocketServer
import string
import threading
import urllib
import urllib2

import RPFramework
import domoPadDevices
#from googleapiclient.discovery import build


#/////////////////////////////////////////////////////////////////////////////////////////
# Constants and configuration variables
#/////////////////////////////////////////////////////////////////////////////////////////
INCLUDED_IWS_VERSION = (1,2)
DOMOPADCOMMAND_SENDNOTIFICATION = "SendNotification"


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
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs, u'http://www.duncanware.com/Downloads/IndigoHomeAutomation/Plugins/DomoPadMobileClient/DomoPadMobileClientVersionInfo.html', managedDeviceClassModule=domoPadDevices)
		
		
	#/////////////////////////////////////////////////////////////////////////////////////
	# Indigo control methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# startup is called by Indigo whenever the plugin is first starting up (by a restart
	# of Indigo server or the plugin or an update
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def startup(self):
		super(Plugin, self).startup()
		
		# check the IWS plugin currently installed and see if we need to install or upgrade
		# to the version included with this plugin
		self.processIWSUpdateCheck()
			
		# create the socket listener server that will listen for incoming commands to
		# be sent to the Plugin
		try:
			host = u''
			port = int(self.getGUIConfigValue(RPFramework.RPFrameworkPlugin.GUI_CONFIG_PLUGINSETTINGS, u'remoteCommandPort', u'9176'))
			self.socketServer = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
			
			self.logDebugMessage(u'Starting up connection listener', RPFramework.RPFrameworkPlugin.DEBUGLEVEL_MED)
			self.socketServerThread = threading.Thread(target=self.socketServer.serve_forever)
			self.socketServerThread.daemon = True
			self.socketServerThread.start()
		except:
			self.exceptionLog()
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# When the plugin is shutting down we must take down the socket server so that the
	# secondary thread will exit
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def shutdown(self):
		super(Plugin, self).shutdown()
		if not (self.socketServer is None):
			self.socketServer.shutdown()
		
		
	#/////////////////////////////////////////////////////////////////////////////////////
	# Action/command processing routines
	#/////////////////////////////////////////////////////////////////////////////////////	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called to handle any unknown commands at the plugin level; it
	# can/should be overridden in the plugin implementation (if needed)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handleUnknownPluginCommand(self, rpCommand, reQueueCommandsList):
		if rpCommand.commandName == DOMOPADCOMMAND_SENDNOTIFICATION:
			# we are using HTTPS to communicate with the Google Cloud Messaging service, so we must have
			# Indigo v6.1 in order to user
			if float(indigo.server.apiVersion) < 1.19:
				indigo.server.log(u'Push notifications require Indigo v6.1 or later', isError=True)	
			else:
				self.logDebugMessage(u'Push Notification Send Command: DevicePairID=' + RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[0]) + u'; Type=' + rpCommand.commandPayload[2] + u'; Message=' + rpCommand.commandPayload[1], RPFramework.RPFrameworkPlugin.DEBUGLEVEL_HIGH)
			
				# setup the defaults so that we know all of the parameters have a value...
				queryStringParams = { u'devicePairingId' : rpCommand.commandPayload[0], u'notificationType' : u'Alert', u'priority' : rpCommand.commandPayload[2], u'message' : rpCommand.commandPayload[1] }
				queryStringParams[u'action1Name'] = u''
				queryStringParams[u'action1Group'] = u''
				queryStringParams[u'action2Name'] = u''
				queryStringParams[u'action2Group'] = u''
			
				# build the query string as it must be URL encoded
				if rpCommand.commandPayload[3] != u'' and rpCommand.commandPayload[4] != u'':
					self.logDebugMessage(u'Push Notification Send Action 1: ' + rpCommand.commandPayload[3] + u' => ' + rpCommand.commandPayload[4], RPFramework.RPFrameworkPlugin.DEBUGLEVEL_HIGH)
					queryStringParams[u'action1Name'] = rpCommand.commandPayload[3]
					queryStringParams[u'action1Group'] = rpCommand.commandPayload[4]
					queryStringParams[u'notificationType'] = u'ActionAlert'
					targetApiMethod = u'sendActionablePushNotification'
				if rpCommand.commandPayload[5] != u'' and rpCommand.commandPayload[6] != u'':
					self.logDebugMessage(u'Push Notification Send Action 2: ' + rpCommand.commandPayload[5] + u' => ' + rpCommand.commandPayload[6], RPFramework.RPFrameworkPlugin.DEBUGLEVEL_HIGH)
					queryStringParams[u'action2Name'] = rpCommand.commandPayload[5]
					queryStringParams[u'action2Group'] = rpCommand.commandPayload[6]
					queryStringParams[u'notificationType'] = u'ActionAlert'
			
				queryStringEncoded = urllib.urlencode(queryStringParams)
				self.logDebugMessage(u'Push Notification Payload=' + queryStringEncoded, RPFramework.RPFrameworkPlugin.DEBUGLEVEL_HIGH)
		
				# this routine is executed asynchronously and thus can directly send the
				# request to the server
				conn = httplib.HTTPSConnection("com-duncanware-domopad.appspot.com")
				conn.connect()
				conn.putrequest("POST", "/_ah/api/messaging/v1/sendActionablePushNotification")
				conn.putheader("Content-Type", "application/x-www-form-urlencoded")
				conn.putheader("Content-Length", "%d" % len(queryStringEncoded))
				conn.endheaders()
				conn.send(queryStringEncoded)

				response = conn.getresponse()
				responseText = response.read()
				self.logDebugMessage(u'Push notification Response: [' + RPFramework.RPFrameworkUtils.to_unicode(response.status) + u'] ' + responseText, RPFramework.RPFrameworkPlugin.DEBUGLEVEL_HIGH)
			
				try:
					if response.status == 204:
						self.logDebugMessage(u'Push notification sent successfully', RPFramework.RPFrameworkPlugin.DEBUGLEVEL_MED)
					else:
						indigo.server.log(u'Error sending push notification.', isError=True)	
				except:
					indigo.server.log(u'Error sending push notification.', isError=True)	
					self.exceptionLog()
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will process the Send Notification action... it will queue up the
	# command for the plugin to process asynchronously
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processSendNotification(self, action):
		rpDevice = self.managedDevices[action.deviceId]
		deviceRegistrationId = rpDevice.indigoDevice.pluginProps.get(u'deviceRegistrationId', u'')
		messageToSend = self.substitute(action.props.get(u'message'))
		importanceLevel = action.props.get(u'importanceLevel')
		
		action1Name = action.props.get(u'action1Name', u'')
		action1Group = action.props.get(u'action1Group', u'')
		action2Name = action.props.get(u'action2Name', u'')
		action2Group = action.props.get(u'action2Group', u'')
		
		if deviceRegistrationId == u'':
			indigo.server.log(u'Unable to send push notification to ' + RPFramework.RPFrameworkUtils.to_unicode(rpDevice.indigoDevice.deviceId) + u'; the device is not paired.', isError=True)
		else:
			self.logDebugMessage(u'Queuing push notification command for ' + RPFramework.RPFrameworkUtils.to_unicode(action.deviceId), RPFramework.RPFrameworkPlugin.DEBUGLEVEL_HIGH)
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(DOMOPADCOMMAND_SENDNOTIFICATION, commandPayload=(deviceRegistrationId, messageToSend, importanceLevel, action1Name, action1Group, action2Name, action2Group)))
		
			
	#/////////////////////////////////////////////////////////////////////////////////////
	# Configuration Dialog Callback Routines
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called back from the configuration dialog whenever the user has
	# clicked the button to clear the value of the device pairing
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clearDevicePairing(self, valuesDict, typeId, devId):
		valuesDict[u'deviceRegistrationId'] = u''
		return valuesDict
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called when the plugin's configuration dialog closes; we need
	# to check for the IWS plugin now since the username/password may have been updated
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		super(Plugin, self).closedPrefsConfigUi(valuesDict, userCancelled)
		self.processIWSUpdateCheck()
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the user has clicked to clear his/her selection of
	# an action in slot 1
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clearNotificationAction1(self, valuesDict, typeId, devId):
		valuesDict[u'action1Name'] = u''
		valuesDict[u'action1Group'] = u''
		return valuesDict
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called whenever the user has clicked to clear his/her selection of
	# an action in slot 2
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clearNotificationAction2(self, valuesDict, typeId, devId):
		valuesDict[u'action2Name'] = u''
		valuesDict[u'action2Group'] = u''
		return valuesDict
	
	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Utility Routines
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will perform the update check and execute the update if needed
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processIWSUpdateCheck(self):
		# check the IWS plugin currently installed and see if we need to install or upgrade
		# to the version included with this plugin
		currentIWSPluginVersion = self.getIWSPluginVersion()
		self.logDebugMessage(u'Current IWS Plugin: v' + RPFramework.RPFrameworkUtils.to_unicode(currentIWSPluginVersion[0]) + u'.' + RPFramework.RPFrameworkUtils.to_unicode(currentIWSPluginVersion[1]), RPFramework.RPFrameworkPlugin.DEBUGLEVEL_MED)
		self.logDebugMessage(u'Included IWS Plugin: v' + RPFramework.RPFrameworkUtils.to_unicode(INCLUDED_IWS_VERSION[0]) + u'.' + RPFramework.RPFrameworkUtils.to_unicode(INCLUDED_IWS_VERSION[1]), RPFramework.RPFrameworkPlugin.DEBUGLEVEL_MED)
		
		if INCLUDED_IWS_VERSION[0] > currentIWSPluginVersion[0] or (INCLUDED_IWS_VERSION[0] == currentIWSPluginVersion[0] and INCLUDED_IWS_VERSION[1] > currentIWSPluginVersion[1]):
			# we need to perform the IWS upgrade now
			self.updateIWSPlugin()
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine obtains the current version of the IWS plugin as a tuple of version
	# numbers
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getIWSPluginVersion(self):
		try:
			# create a password manager
			indigoPassMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
			indigoPassMgr.add_password(None, u'http://localhost:' + self.pluginPrefs.get(u'indigoPort') + u'/', self.pluginPrefs.get(u'indigoUsername'), self.pluginPrefs.get(u'indigoPassword'))
			handler = urllib2.HTTPDigestAuthHandler(indigoPassMgr)

			# create "opener" (OpenerDirector instance)
			opener = urllib2.build_opener(handler)
			responseToQuery = opener.open(u'http://localhost:' + self.pluginPrefs.get(u'indigoPort') + u'/AndroidClientHelper/getVersionInfo')
			responseToQueryText = responseToQuery.read()

			regex = re.compile("^v(?P<major>\d+)\.(?P<minor>\d+)$")
			match = regex.search(responseToQueryText)
			
			if match is None:
				self.logDebugMessage(u'Connected to IWS, but current version not returned: ' + responseToQueryText, RPFramework.RPFrameworkPlugin.DEBUGLEVEL_LOW)
				return (0,0)
			else:
				return (int(match.groupdict().get(u'major')), int(match.groupdict().get(u'minor')))
				
		except urllib2.HTTPError, e:
			# if this is a 404 error then the client is not installed and we can return the
			# version as empty
			if e.code == 404:
				return (0,0)
			else:
				self.logDebugMessage(u'Failed to retrieve current IWS plugin version:', RPFramework.RPFrameworkPlugin.DEBUGLEVEL_LOW)
				if self.debug:
					self.exceptionLog()
				return (0,0)
		except:
			# when an exception occurs we are going to have to assume that we need to copy
			# the plugin over...
			self.logDebugMessage(u'Failed to retrieve current IWS plugin version:', RPFramework.RPFrameworkPlugin.DEBUGLEVEL_LOW)
			if self.debug:
				self.exceptionLog()
			return (0,0)
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will perform an update to the current IWS plugin by copying over the
	# version from this Plugin
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def updateIWSPlugin(self):	
		indigo.server.log(u'Performing update of DomoPad''s IWS plugin...')
		
		# determine the IWS server directory
		indigoInstallPath = indigo.server.getInstallFolderPath()
		
		mainPluginHome = os.path.join(indigoInstallPath, "Plugins/DomoPad Mobile Client.indigoPlugin/Contents/Server Plugin/AndroidClientHelper") 
		iwsPluginHome = os.path.join(indigoInstallPath, "IndigoWebServer/plugins/AndroidClientHelper")
		
		indigo.server.log(u'Source IWS directory: ' + mainPluginHome)
		indigo.server.log(u'Target IWS directory: ' + iwsPluginHome)
		
		# ensure that we have the correct source directory...
		if os.path.exists(mainPluginHome) == False:
			indigo.server.log(u'ERROR: Source directory not found!  AndroidClientHelper IWS plugin install could not complete.', isError=True)
			return
			
		# execute the directory copy now...
		try:
			copy_tree(mainPluginHome, iwsPluginHome, preserve_mode=1)
			indigo.server.log(u'AndroidClientHelper successfully installed/updated. Restarting Indigo IWS server to complete install.')
			self.restartIWS()
		except:
			indigo.server.log(u'Error copying AndroidClientHelper, AndroidClientHelper IWS plugin install could not complete.', isError=True)
			self.exceptionLog()
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will restart the IWS so that the plugin may be updated...
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def restartIWS(self):
		try:
			baseUrl = "http://localhost:" + self.pluginPrefs.get("indigoPort") +"/"
			restartUrl = baseUrl + "indigocommand?name=restart"
			
			# create a password manager
			indigoPassMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
			indigoPassMgr.add_password(None, baseUrl, self.pluginPrefs.get(u'indigoUsername'), self.pluginPrefs.get(u'indigoPassword'))
			handler = urllib2.HTTPDigestAuthHandler(indigoPassMgr)

			# create "opener" (OpenerDirector instance)
			opener = urllib2.build_opener(handler)
			responseToQuery = opener.open(restartUrl)
			responseToQueryText = responseToQuery.read()
		except:
			pass
		
		
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Utility classes
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# This class does the work of fielding and responding to requests sent in to the 
# remote/monitoring port
#/////////////////////////////////////////////////////////////////////////////////////////
class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will be called by the server to handle the request
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def handle(self):
		try:
			#self.request.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
			requestReceived = self.request.recv(1024)
		
			# attempt to parse the request to determine how to proceed from here
			commandParser = re.compile("GET (/{0,1}AndroidClientHelper){0,1}/{0,1}(?P<commandName>\w+)(\?(?P<arguments>.+)){0,1}\s+HTTP")
			commandMatch = commandParser.search(requestReceived)
			
			# send back the proper HTML headers so that the browser knows the connection is good...
			self.request.sendall("HTTP/1.0 200 OK\nContent-Type: text/html\n\n")
			
			commandResponse = ""
			if commandMatch is None:
				commandResponse = u'ERROR: No command received'
			else:
				commandName = commandMatch.groupdict().get(u'commandName')
				indigo.server.log(u'Process command: ' + commandName)
			
				if commandName == u'executePluginAction':
					commandArguments = self.parseArguments(commandMatch.groupdict().get(u'arguments'))
					# TODO: the plugin action parameters will be encrypted on the action line as an argument
				
					# required parameters are the plugin ID and device ID
					pluginId = commandArguments.get(u'pluginId')[0]
					deviceId = commandArguments.get(u'deviceId')[0]
					actionId = commandArguments.get(u'actionId')[0]
					actionProps = commandArguments.get(u'actionProps')[0]
					indigo.server.log(actionProps)
					
					# get the plugin that was requested from the indigo server
					indigoPlugin = indigo.server.getPlugin(pluginId)
					
					if indigoPlugin is None:
						commandResponse = u'ERROR: Invalid plugin specified'
					elif (actionProps is None) or (len(actionProps) == 0):
						indigoPlugin.executeAction(actionId, deviceId=int(deviceId))
						commandResponse = u'OK'
					else:
						actionPropDict = eval(actionProps)
						indigoPlugin.executeAction(actionId, deviceId=int(deviceId), props=actionPropDict)
						commandResponse = u'OK'
				elif commandName == u'registerAndroidDevice':
					commandArguments = self.parseArguments(commandMatch.groupdict().get(u'arguments'))
					deviceId = commandArguments.get(u'deviceId')[0]
					pairingId = commandArguments.get(u'pairingId')[0]
					allowOverwrite = int(commandArguments.get(u'allowOverwrite')[0])
					
					indigoAndroidDev = indigo.devices[int(deviceId)]
					pluginProps = indigoAndroidDev.pluginProps;
					
					if pluginProps.get(u'deviceRegistrationId', u'') == u'' or allowOverwrite == 1:
						pluginProps[u'deviceRegistrationId'] = pairingId
						indigoAndroidDev.replacePluginPropsOnServer(pluginProps)
						indigoAndroidDev.updateStateOnServer(u'isPaired', True, uiValue=u'Paired')
						commandResponse = u'OK'
						indigo.server.log(u'Successfully paired Android device to Indigo Device ' + RPFramework.RPFrameworkUtils.to_unicode(deviceId))
					else:
						indigo.server.log(u'Rejected device pairing - Indigo Device already paired to another Android device.', isError=True)
						commandResponse = u'ERROR: Exception Processing Request'
				elif commandName == u'unregisterAndroidDevice':	
					commandArguments = self.parseArguments(commandMatch.groupdict().get(u'arguments'))
					deviceId = commandArguments.get(u'deviceId')[0]
					pairingId = commandArguments.get(u'pairingId')[0]
					
					indigoAndroidDev = indigo.devices[int(deviceId)]
					pluginProps = indigoAndroidDev.pluginProps;
					
					# only de-register if the pairing IDs currently match...
					if pluginProps.get(u'deviceRegistrationId', u'') == pairingId:
						pluginProps[u'deviceRegistrationId'] = u''
						indigoAndroidDev.replacePluginPropsOnServer(pluginProps)
						indigoAndroidDev.updateStateOnServer(u'isPaired', False, uiValue=u'Not Paired')
						commandResponse = u'OK'
						indigo.server.log(u'Successfully un-paired Android device to Indigo Device ' + RPFramework.RPFrameworkUtils.to_unicode(deviceId))
					else:
						indigo.server.log(u'Rejected device un-pairing - Indigo Device does not match Android device.', isError=True)
						commandResponse = u'ERROR: Exception Processing Request'
				elif commandName == u'updateMobileDeviceStates':
					commandArguments = self.parseArguments(commandMatch.groupdict().get(u'arguments'))
					pairingId = commandArguments.get(u'pairingId')[0]
					modelName = commandArguments.get(u'deviceModel')[0]
					batteryStatus = commandArguments.get(u'batteryStatus')[0]
					batteryLevel = int(commandArguments.get(u'batteryLevel')[0])
					longitude = commandArguments.get(u'longitude')[0]
					latitude = commandArguments.get(u'latitude')[0]
					locationFixTime = commandArguments.get(u'locationFix', (u''))[0]
					
					# we need to find the proper devices based upon the pairing id; the default response will be
					# that the device was not found
					commandResponse = u'ERROR: Device not found'
					devIter = indigo.devices.iter(filter="com.duncanware.domoPadMobileClient.domoPadAndroidClient")
					for dev in devIter:
						if dev.pluginProps.get('deviceRegistrationId', '') == pairingId:
							dev.updateStateOnServer(u'modelName', modelName)
							dev.updateStateOnServer(u'batteryStatus', batteryStatus)
							dev.updateStateOnServer(u'batteryLevel', batteryLevel)
							dev.updateStateOnServer(u'longitude', longitude)
							dev.updateStateOnServer(u'latitude', latitude)
							dev.updateStateOnServer(u'locationFixTime', locationFixTime)
							
							commandResponse = u'OK'
							
					if commandResponse != u'OK':
						indigo.server.log(u'Received status update for unknown device with Pairing ID: ' + pairingId, isError=True)
		
			# send whatever response was generated back to the caller
			self.request.sendall(commandResponse)
		
		except Exception, e:
			indigo.server.log(u'DomoPad Plugin Exception: Error processing remote request: ' + RPFramework.RPFrameworkUtils.to_unicode(e))
			self.request.sendall(u'ERROR: Exception Processing Request')
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will split out the "arguments" section of the request into name/value
	# pairs as standard query string arguments; note that this is now (Python 2.6+) in
	# the urlparse module and must be updated if python updates
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def parseArguments(self, qsArguments):
		return cgi.parse_qs(qsArguments, keep_blank_values=1)


#/////////////////////////////////////////////////////////////////////////////////////////
# This class creates a concrete threaded TCP server in order to listen to and respond
# to requests from HousePad or the HousePad IWS plugin
#/////////////////////////////////////////////////////////////////////////////////////////
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	def serve_forever(self):
		self.__serving = True
		while self.__serving:
			self.handle_request()
			
	def shutdown(self):
		self.__serving = False
		shutdownSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		shutdownSocket.connect(self.server_address)
		shutdownSocket.sendall("shutdown")
		shutdownSocket.close()
