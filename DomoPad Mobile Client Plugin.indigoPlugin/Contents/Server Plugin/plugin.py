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
#	Version 1.2.19:
#		Migrated updater to GitHub
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
import inspect

import RPFramework
import domoPadDevices
import googleHomeDevices


#/////////////////////////////////////////////////////////////////////////////////////////
# Constants and configuration variables
#/////////////////////////////////////////////////////////////////////////////////////////
INCLUDED_IWS_VERSION = (1,4)
DOMOPADCOMMAND_SENDNOTIFICATION = u'SendNotification'
DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION = u'SendTextToSpeechNotification'
DOMOPADCOMMAND_CPDISPLAYNOTIFICATION = u'SendCPDisplayRequest'
DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION = u'RequestDeviceStatusUpdate'


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
			
			self.logger.debug(u'Starting up connection listener')
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
				self.logger.error(u'Push notifications require Indigo v6.1 or later')	
			else:
				self.logger.threaddebug(u'Push Notification Send Command: DevicePairID=' + RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[0]) + u'; Type=' + rpCommand.commandPayload[2] + u'; Message=' + rpCommand.commandPayload[1])
			
				# setup the defaults so that we know all of the parameters have a value...
				queryStringParams = { u'devicePairingId' : rpCommand.commandPayload[0], u'notificationType' : u'Alert', u'priority' : rpCommand.commandPayload[2], u'message' : RPFramework.RPFrameworkUtils.to_str(rpCommand.commandPayload[1]) }
				queryStringParams[u'action1Name'] = u''
				queryStringParams[u'action1Group'] = u''
				queryStringParams[u'action2Name'] = u''
				queryStringParams[u'action2Group'] = u''
			
				# build the query string as it must be URL encoded
				if rpCommand.commandPayload[3] != u'' and rpCommand.commandPayload[4] != u'':
					self.logger.threaddebug(u'Push Notification Send Action 1: ' + rpCommand.commandPayload[3] + u' => ' + rpCommand.commandPayload[4])
					queryStringParams[u'action1Name'] = RPFramework.RPFrameworkUtils.to_str(rpCommand.commandPayload[3])
					queryStringParams[u'action1Group'] = RPFramework.RPFrameworkUtils.to_str(rpCommand.commandPayload[4])
					queryStringParams[u'notificationType'] = "ActionAlert"
					targetApiMethod = u'sendActionablePushNotification'
				if rpCommand.commandPayload[5] != u'' and rpCommand.commandPayload[6] != u'':
					self.logger.threaddebug(u'Push Notification Send Action 2: ' + rpCommand.commandPayload[5] + u' => ' + rpCommand.commandPayload[6])
					queryStringParams[u'action2Name'] = RPFramework.RPFrameworkUtils.to_str(rpCommand.commandPayload[5])
					queryStringParams[u'action2Group'] = RPFramework.RPFrameworkUtils.to_str(rpCommand.commandPayload[6])
					queryStringParams[u'notificationType'] = "ActionAlert"
			
				queryStringEncoded = urllib.urlencode(queryStringParams)
				self.logger.threaddebug(u'Push Notification Payload=' + queryStringEncoded)
		
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
				self.logger.threaddebug(u'Push notification Response: [' + RPFramework.RPFrameworkUtils.to_unicode(response.status) + u'] ' + responseText)
			
				try:
					if response.status == 204:
						self.logger.debug(u'Push notification sent successfully')
					else:
						self.logger.error(u'Error sending push notification.')	
				except:
					self.logger.exception(u'Error sending push notification.')	
					
		elif rpCommand.commandName == DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION:
			self.logger.threaddebug(u'Speak Announcement Notification Send Command: DevicePairID=' + RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[0]) + u'; Msg=' + RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[1]))
			
			messageExpanded = self.substituteIndigoValues(RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[1]), rpCommand.commandPayload[2], [])
			queryStringParams = { u'devicePairingId' : rpCommand.commandPayload[0], u'message' : RPFramework.RPFrameworkUtils.to_unicode(messageExpanded) }
			queryStringEncoded = urllib.urlencode(queryStringParams, 'utf-8')
			self.logger.threaddebug(u'Push Notification Payload=' + queryStringEncoded)
			
			# this routine is executed asynchronously and thus can directly send the
			# request to the server
			conn = httplib.HTTPSConnection("com-duncanware-domopad.appspot.com")
			conn.connect()
			conn.putrequest("POST", "/_ah/api/messaging/v1/sendAnnounceTextRequest")
			conn.putheader("Content-Type", "application/x-www-form-urlencoded")
			conn.putheader("Content-Length", "%d" % len(queryStringEncoded))
			conn.endheaders()
			conn.send(queryStringEncoded)

			response = conn.getresponse()
			responseText = response.read()
			self.logger.threaddebug(u'Speak announcement notification response: [' + RPFramework.RPFrameworkUtils.to_unicode(response.status) + u'] ' + responseText)
		
			try:
				if response.status == 204:
					self.logger.debug(u'Speak announcement notification sent successfully')
				else:
					self.logger.error(u'Error sending speak announcement notification.')	
			except:
				self.logger.exception(u'Error sending speak announcement notification.')	
					
		elif rpCommand.commandName == DOMOPADCOMMAND_CPDISPLAYNOTIFICATION:
			self.logger.threaddebug(u'Control Page Display Notification Send Command: DevicePairID=' + RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[0]) + u'; Page=' + RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[1]))

			# load the control page name so that we may pass it along to the deviceId
			# (may be needed for notification purposes)
			requestedPage = indigo.rawServerRequest('GetControlPage', {"ID" : rpCommand.commandPayload[1]})
			cpPageName = requestedPage["Name"] 
			
			queryStringParams = { u'devicePairingId' : rpCommand.commandPayload[0], u'pageRequested' : RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload[1]), u'pageName' : cpPageName }
			
			queryStringEncoded = urllib.urlencode(queryStringParams)
			self.logger.threaddebug(u'Push Notification Payload=' + queryStringEncoded)
			
			# this routine is executed asynchronously and thus can directly send the
			# request to the server
			conn = httplib.HTTPSConnection("com-duncanware-domopad.appspot.com")
			conn.connect()
			conn.putrequest("POST", "/_ah/api/messaging/v1/sendControlPageDisplayRequest")
			conn.putheader("Content-Type", "application/x-www-form-urlencoded")
			conn.putheader("Content-Length", "%d" % len(queryStringEncoded))
			conn.endheaders()
			conn.send(queryStringEncoded)

			response = conn.getresponse()
			responseText = response.read()
			self.logger.threaddebug(u'Control page display notification response: [' + RPFramework.RPFrameworkUtils.to_unicode(response.status) + u'] ' + responseText)
		
			try:
				if response.status == 204:
					self.logger.debug(u'Control page display notification sent successfully')
				else:
					self.logger.error(u'Error sending control page display notification.')	
			except:
				self.logger.exception(u'Error sending control page display notification.')	
		
		elif rpCommand.commandName == DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION:
			self.logger.threaddebug(u'Status Update Request Notification Send Command: DevicePairID=' + RPFramework.RPFrameworkUtils.to_unicode(rpCommand.commandPayload))
			queryStringParams = { u'devicePairingId' : rpCommand.commandPayload }
			queryStringEncoded = urllib.urlencode(queryStringParams)
			self.logger.threaddebug(u'Push Notification Payload=' + queryStringEncoded)
			
			# this routine is executed asynchronously and thus can directly send the
			# request to the server
			conn = httplib.HTTPSConnection("com-duncanware-domopad.appspot.com")
			conn.connect()
			conn.putrequest("POST", "/_ah/api/messaging/v1/sendDeviceStatusUpdateRequest")
			conn.putheader("Content-Type", "application/x-www-form-urlencoded")
			conn.putheader("Content-Length", "%d" % len(queryStringEncoded))
			conn.endheaders()
			conn.send(queryStringEncoded)
			
			response = conn.getresponse()
			responseText = response.read()
			self.logger.threaddebug(u'Status update request notification response: [' + RPFramework.RPFrameworkUtils.to_unicode(response.status) + u'] ' + responseText)
		
			try:
				if response.status == 204:
					self.logger.debug(u'Status update request notification sent successfully')
				else:
					self.logger.error(u'Error sending status update request notification.')	
			except:
				self.logger.exception(u'rror sending status update request notification.')
			
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
			self.logger.error(u'Unable to send push notification to ' + RPFramework.RPFrameworkUtils.to_unicode(rpDevice.indigoDevice.deviceId) + u'; the device is not paired.')
		else:
			self.logger.threaddebug(u'Queuing push notification command for ' + RPFramework.RPFrameworkUtils.to_unicode(action.deviceId))
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(DOMOPADCOMMAND_SENDNOTIFICATION, commandPayload=(deviceRegistrationId, messageToSend, importanceLevel, action1Name, action1Group, action2Name, action2Group)))
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Speak Announcement command to an Android Device
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processSpeakAnnouncementNotification(self, action):
		rpDevice = self.managedDevices[action.deviceId]
		deviceRegistrationId = rpDevice.indigoDevice.pluginProps.get(u'deviceRegistrationId', u'')
		announcementMsg = action.props.get(u'announcement', '')
		
		if deviceRegistrationId == u'':
			self.logger.error(u'Unable to send speak announcement request notification to ' + RPFramework.RPFrameworkUtils.to_unicode(rpDevice.indigoDevice.deviceId) + u'; the device is not paired.')
		elif announcementMsg == u'':
			self.logger.error(u'Unable to send speak announcement request notification to ' + RPFramework.RPFrameworkUtils.to_unicode(rpDevice.indigoDevice.deviceId) + u'; no announcement text was entered.')
		else:
			self.logger.threaddebug(u'Queuing peak announcement request notification command for ' + RPFramework.RPFrameworkUtils.to_unicode(action.deviceId))
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION, commandPayload=(deviceRegistrationId, announcementMsg, rpDevice)))
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Control Page Display Command to a Android device (in
	# order to request that a specific control page be shown on the device)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processControlPageDisplayNotification(self, action):
		rpDevice = self.managedDevices[action.deviceId]
		deviceRegistrationId = rpDevice.indigoDevice.pluginProps.get(u'deviceRegistrationId', u'')
		controlPageId = int(action.props.get(u'controlPageId', '0'))
		
		if deviceRegistrationId == u'':
			self.logger.error(u'Unable to send control page display request notification to ' + RPFramework.RPFrameworkUtils.to_unicode(rpDevice.indigoDevice.deviceId) + u'; the device is not paired.')
		elif controlPageId <= 0:
			self.logger.error(u'Unable to send control page display request notification to ' + RPFramework.RPFrameworkUtils.to_unicode(rpDevice.indigoDevice.deviceId) + u'; no control page was selected.')
		else:
			self.logger.threaddebug(u'Queuing control page display request notification command for ' + RPFramework.RPFrameworkUtils.to_unicode(action.deviceId))
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(DOMOPADCOMMAND_CPDISPLAYNOTIFICATION, commandPayload=(deviceRegistrationId, controlPageId)))
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Update Device Status request notification in order to ask
	# the device to update its status immediately (instead of waiting for its normal 15
	# minute update interval)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def processRequestDeviceStatusNotification(self, action):
		requestDeviceStatusNotification(action.deviceId)
		
			
	#/////////////////////////////////////////////////////////////////////////////////////
	# Configuration Dialog Callback Routines
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called in order to load the list of devices which have been selected for publishing
	# to Google Home/Assistant
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getPublishedHomeDevices(self, filter="", valuesDict=None, typeId="", targetId=0):
		# loop through each defined device and capture the ones that have
		# been flagged for publishing
		publishedDevicesLst = []
		for device in indigo.devices:
			if device.sharedProps.get('googleClientPublishHome', False) == True:
				deviceDispName = device.sharedProps['googleClientAsstName']
				if device.name != deviceDispName:
					deviceDispName = deviceDispName + " (" + device.name + ")"
				publishedDevicesLst.append((device.id, deviceDispName))
		
		# return the list of devices as a dynamic menu return
		return publishedDevicesLst

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called in order to load the list of devices which are NOT published to Google
	# Home
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getNonPublishedHomeDevices(self, filter="", valuesDict=None, typeId="", targetId=0):
		# loop through all Indigo devices, returning those without the googleClientPublishHome
		# or set to False
		nonPublishedDevices = []
		for device in indigo.devices.iter(filter="indigo.relay,indigo.dimmer,indigo.thermostat,indigo.sensor"):
			if device.sharedProps.get('googleClientPublishHome', False) == False:
				nonPublishedDevices.append((device.id, device.name))
		return nonPublishedDevices

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Retrieves the list of available (supported) devices types as defined by the
	# Google Assistant
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getGoogleDeviceTypes(self, filter="", valuesDict=None, typeId="", targetId=0):
		listItems = []
		for deviceType in sorted(googleHomeDevices.googleDeviceTypesDefn.iterkeys()):
			deviceDefn = googleHomeDevices.googleDeviceTypesDefn[deviceType]
			listItems.append((deviceType, deviceDefn['Device']))
		return listItems

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called whenever the user has selected a device from the list of published Google
	# Assistant devices... show the "Google" device details
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def publishedHomeDeviceSelected(self, valuesDict=None, typeId="", devId=0):
		try:
			device = indigo.devices.get(int(valuesDict["publishedDevices"]), None)
			valuesDict["deviceDetailsPublishedName"] = device.sharedProps['googleClientAsstName']
			valuesDict["deviceDetailsPublishedType"] = device.sharedProps['googleClientAsstType']
			valuesDict['publishedDeviceSelected'] = True
		except:
			self.logger.exception(u'Failed to load published device properties')
		return valuesDict

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called whenever the user has clicked to update the published Google Home (such as
	# changing the device name or type)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def publishedHomeDevicesUpdate(self, valuesDict=None, typeId="", devId=0):
		try:
			device = indigo.devices.get(int(valuesDict["publishedDevices"]), None)
			globalProps = device.sharedProps

			globalProps['googleClientAsstName'] = valuesDict["deviceDetailsPublishedName"]
			globalProps['googleClientAsstType'] = valuesDict["deviceDetailsPublishedType"]
			device.replaceSharedPropsOnServer(globalProps)

			valuesDict["publishedDevices"] = None
			valuesDict['publishedDeviceSelected'] = False
			valuesDict["deviceDetailsPublishedName"] = ''
			valuesDict["deviceDetailsPublishedType"] = None
		except:
			self.logger.exception(u'Failed to update published device properties')
		return valuesDict

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Publishes the selected device to Google Home; it should add the proper global
	# properties and reload to the Published Device interface with it selected so that
	# the user may finish configuration
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def addPublishedHomeDevice(self, valuesDict=None, typeId="", devId=0):
		# pull the device... the selected value in the add should be the Indigo device ID
		selectedId = int(valuesDict.get('addPublishedDeviceSelect', 0))
		if selectedId > 0:
			device = indigo.devices[selectedId]
			globalProps = device.sharedProps
			globalProps['googleClientPublishHome'] = True
			globalProps['googleClientAsstName'] = device.name
			globalProps['googleClientAsstType'] = googleHomeDevices.mapIndigoDeviceToGoogleType(device)
			device.replaceSharedPropsOnServer(globalProps)
		return valuesDict

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called back from the configuration dialog whenever the user has
	# clicked the button to clear the value of the device pairing
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def clearDevicePairing(self, valuesDict, typeId, devId):
		valuesDict[u'deviceRegistrationId'] = u''
		return valuesDict
		
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
		self.logger.debug(u'Current IWS Plugin: v' + RPFramework.RPFrameworkUtils.to_unicode(currentIWSPluginVersion[0]) + u'.' + RPFramework.RPFrameworkUtils.to_unicode(currentIWSPluginVersion[1]))
		self.logger.debug(u'Included IWS Plugin: v' + RPFramework.RPFrameworkUtils.to_unicode(INCLUDED_IWS_VERSION[0]) + u'.' + RPFramework.RPFrameworkUtils.to_unicode(INCLUDED_IWS_VERSION[1]))
		
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
				self.logger.warning(u'Connected to IWS, but current version not returned: ' + responseToQueryText)
				return (0,0)
			else:
				return (int(match.groupdict().get(u'major')), int(match.groupdict().get(u'minor')))
				
		except urllib2.HTTPError, e:
			# if this is a 404 error then the client is not installed and we can return the
			# version as empty
			if e.code == 404:
				return (0,0)
			else:
				if self.debugLevel != RPFramework.RPFrameworkPlugin.DEBUGLEVEL_NONE:
					self.logger.error(u'Failed to retrieve current IWS plugin version:')
				else:
					self.logger.warning(u'Failed to retrieve current IWS plugin version:')
				return (0,0)
		except:
			# when an exception occurs we are going to have to assume that we need to copy
			# the plugin over...
			if self.debugLevel != RPFramework.RPFrameworkPlugin.DEBUGLEVEL_NONE:
				self.logger.error(u'Failed to retrieve current IWS plugin version:')
			else:
				self.logger.warning(u'Failed to retrieve current IWS plugin version:')
			return (0,0)
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will perform an update to the current IWS plugin by copying over the
	# version from this Plugin
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def updateIWSPlugin(self):	
		self.logger.info(u'Performing update of DomoPad''s IWS plugin...')
		
		# determine the IWS server directory
		indigoInstallPath = indigo.server.getInstallFolderPath()
		pluginBasePath = os.getcwd()
		
		mainPluginHome = os.path.join(pluginBasePath, "AndroidClientHelper") 
		iwsPluginHome = os.path.join(indigoInstallPath, "IndigoWebServer/plugins/AndroidClientHelper")
		
		self.logger.info(u'Source IWS directory: ' + mainPluginHome)
		self.logger.info(u'Target IWS directory: ' + iwsPluginHome)
		
		# ensure that we have the correct source directory...
		if os.path.exists(mainPluginHome) == False:
			self.logger.error(u'ERROR: Source directory not found!  AndroidClientHelper IWS plugin install could not complete.')
			return
			
		# execute the directory copy now...
		try:
			copy_tree(mainPluginHome, iwsPluginHome, preserve_mode=1)
			self.logger.info(u'AndroidClientHelper successfully installed/updated. Restarting Indigo IWS server to complete install.')
			self.restartIWS()
		except:
			self.logger.error(u'Error copying AndroidClientHelper, AndroidClientHelper IWS plugin install could not complete.')
		
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
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will send the Update Device Status request notification in order to ask
	# the device to update its status immediately (instead of waiting for its normal 15
	# minute update interval)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def requestDeviceStatusNotification(self, deviceId):
		rpDevice = self.managedDevices[deviceId]
		deviceRegistrationId = rpDevice.indigoDevice.pluginProps.get(u'deviceRegistrationId', u'')
		
		if deviceRegistrationId == u'':
			self.logger.error(u'Unable to send status update request notification to ' + RPFramework.RPFrameworkUtils.to_unicode(rpDevice.indigoDevice.deviceId) + u'; the device is not paired.')
		else:
			self.logger.threaddebug(u'Queuing device status update request notification command for ' + RPFramework.RPFrameworkUtils.to_unicode(deviceId))
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION, commandPayload=deviceRegistrationId))
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Return the list of devices configured for publishing to the Google Assistant in the
	# Google Smart Actions sync format
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getGoogleHomeSyncResponse(self):
		# loop through each defined device and capture the ones that have
		# been flagged for publishing
		publishedDevicesLst = []
		for device in indigo.devices:
			if device.sharedProps.get('googleClientPublishHome', False) == True:
				publishedDevicesLst.append(googleHomeDevices.buildGoogleHomeDeviceDefinition(device))
		
		# return the list of devices back to the calling routine; these are in the
		# proper format for a return to Google
		return publishedDevicesLst
	
		
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
					
					# get the plugin that was requested from the indigo server... if this is a domoPadMobileClient then we need
					# to access the plugin object directly to avoid an error dispatching the executeAction
					if pluginId == u'com.duncanware.domoPadMobileClient':
						indigoPlugin = indigo.activePlugin
						
						if actionId == 'sendUpdateStatusRequestNotification':
							indigoPlugin.requestDeviceStatusNotification(int(deviceId))
						else:
							indigo.server.log(u'Unknown action received for domoPadMobileClient: ' + actionId)
					else:
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
				
				elif commandName == u'googleHomeSyncAllDevices':
					indigoPlugin = indigo.activePlugin
					googleDevList = indigoPlugin.getGoogleHomeSyncResponse()
					commandResponse = json.dumps(googleDevList)
		
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
