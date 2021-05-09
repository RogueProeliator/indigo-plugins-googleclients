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
import requests

import RPFramework
import domoPadDevices
import googleHomeDevices


#/////////////////////////////////////////////////////////////////////////////////////////
# Constants and configuration variables
#/////////////////////////////////////////////////////////////////////////////////////////
DOMOPADCOMMAND_SENDNOTIFICATION                = u'SendNotification'
DOMOPADCOMMAND_SPEAKANNOUNCEMENTNOTIFICATION   = u'SendTextToSpeechNotification'
DOMOPADCOMMAND_CPDISPLAYNOTIFICATION           = u'SendCPDisplayRequest'
DOMOPADCOMMAND_DEVICEUPDATEREQUESTNOTIFICATION = u'RequestDeviceStatusUpdate'

GOOGLEHOME_SENDDEVICEUPDATE = u'SendHomeGraphUpdate'
GOOGLEHOME_REQUESTSYNC      = u'RequestHomeGraphSync'


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
				pass
			except:
				self.logger.exception(u'Failed to send device update to Google Home')

		elif rpCommand.commandName == GOOGLEHOME_REQUESTSYNC:
			pass
			

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
		if self.reportStateToAssistant == True:
			globalPropsDict = newDev.globalProps['com.indigodomo.indigoserver']
			if globalPropsDict.get(u'googleClientPublishHome', False) == True:
				try:
					# call the Google Home Graph's update via the Cloud Function
					pass
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
			googleDeviceType = googleHomeDevices.mapIndigoDeviceToGoogleType(dev)
			if googleDeviceType != '':
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
			device = indigo.devices.get(int(valuesDict["publishedDevice"]), None)

			valuesDict["enableDeviceDetailUI"]       = True
			valuesDict["publishToGoogle"]            = device.sharedProps.get(u'googleClientPublishHome', False)
			valuesDict["deviceDetailsPublishedName"] = device.sharedProps.get(u'googleClientAsstName', u'')
			valuesDict["deviceDetailsPublishedType"] = device.sharedProps.get(u'googleClientAsstType', u'')
			valuesDict["sendUpdatesToGoogle"]        = device.sharedProps.get(u'googleClientSendUpdates', u'')
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
			device.replaceSharedPropsOnServer(globalProps)

			valuesDict["publishedDevice"]            = None
			valuesDict["publishToGoogle"]            = False
			valuesDict['publishedDeviceSelected']    = False
			valuesDict["deviceDetailsPublishedName"] = ''
			valuesDict["deviceDetailsPublishedType"] = None

			valuesDict["enableDeviceDetailUI"]       = False

			# let Google know that a synchronization is required
			self.pluginCommandQueue.put(RPFramework.RPFrameworkCommand.RPFrameworkCommand(GOOGLEHOME_REQUESTSYNC))
		except:
			self.logger.exception(u'Failed to update published device properties')
		return valuesDict

	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Utility Routines
	#/////////////////////////////////////////////////////////////////////////////////////		
