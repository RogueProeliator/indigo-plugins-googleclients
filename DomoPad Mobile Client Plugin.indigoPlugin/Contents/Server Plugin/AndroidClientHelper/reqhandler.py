#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Android Client Helper by RogueProeliator <rp@rogueproeliator.com>
# 	Indigo Web Server (IWDS) plugin that allows the Android client to communicate to the
#	IWS for information not provided in the standard communications protocol
#
#	Version 0.8.15:
#		Initial release of the DomoPad plugin
#
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////


#/////////////////////////////////////////////////////////////////////////////////////////
# Python imports
#/////////////////////////////////////////////////////////////////////////////////////////
import os
import xml.etree.ElementTree
import httplib
import jsonUtil
import urllib

from indigopy import indigoconn as ic
from indigopy import indigodb as idb
from indigopy.basereqhandler import BaseRequestHandler, kTrueStr, kFalseStr, kEmptyStr, kTextPageStr, kHtmlPageStr, kXmlPageStr
from dataAccess import indigosql

#/////////////////////////////////////////////////////////////////////////////////////////
# Constants and configuration variables
#/////////////////////////////////////////////////////////////////////////////////////////
MAJOR_VERSION = "1"
MINOR_VERSION = "5"


#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Plugin Hooks
#	Optional hooks to provide a plugin name and description... these will appear in Event  
#	Log and the IWS plugin list
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Function called to retrieve the name of the plugin to display on lists/pages
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def PluginName():
	return u"Android Client Helper Plugin"

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Function called to retrieve the description of the plugin to display on lists/pages
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def PluginDescription():
	return u"Provides additional information and helper routines for the Indigo Android Client"

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Function called to determine if this page appears in lists
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def ShowOnControlPageList():
	return True

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Function called when IWS connects to Indigo
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def IndigoConnected():
	pass

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Function called to indicate that IWS has disconnected from Indigo
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def IndigoDisconnected():
	pass


#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# IndigoClientHelperHandler
#	Primary IWS plugin that handles requests sent in from the web server
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
class IndigoClientHelperHandler(BaseRequestHandler):

	#/////////////////////////////////////////////////////////////////////////////////////
	# Class construction and destruction methods
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Constructor must call the base class' constructor to properly integrate with IWS
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def __init__(self, logFunc, debugLogFunc):
		BaseRequestHandler.__init__(self, logFunc, debugLogFunc)
		
	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Stub routines necessary for use of the SQL classes from Perceptive Automation
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Future use
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def logMessage(self, msg, isError = False):
		pass
		
		
	#/////////////////////////////////////////////////////////////////////////////////////
	# Index page information
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will return information about the plugin without doing any actual
	# data retrieval
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def index(self):
		indexPageHtml = "<html><head><title>DomoPad Android Client IWS Helper</title></head>"
		indexPageHtml += "<body>"
		indexPageHtml += "<pre>"
		indexPageHtml += "   DomoPad Android Client IWS Helper\n"
		indexPageHtml += "MMMMMMMMMM8$$$$$$$$$$$$$$$$$ZZ$DMMMMMMMM\n"
		indexPageHtml += "MMMMMMMMMM=+++=~=?I7I????IIIIII$MMMMMMMM\n"
		indexPageHtml += "MMMMMMMMM$+++=Z:+?I$OI?IIIIIII7ODMMMMMMM\n"
		indexPageHtml += "MMMMMMMM$???+$:.~I7$OZI777777777OMMMMMMM\n"
		indexPageHtml += "MMMMMMM7?I??7,...=$ZOOZ77777777?$DMMMMMM\n"
		indexPageHtml += "MMMMMM7IIII?.,~~,.+OOOOZ$$$$77?+IOMMMMMM\n"
		indexPageHtml += "MMMMM7II77$+.,~=,..~=~I$$$$$$Z=++7DMMMMM\n"
		indexPageHtml += "MMMMNI7777I:..::,...,+ZZZZZ$ZZ?+=+8MMMMM\n"
		indexPageHtml += "MMMNI7777Z::..::,...:$ZZZZZZO7====NMMMMM\n"
		indexPageHtml += "MMMMMMZ=??:,........IOOOOZOOO+=~~=NMMMMM\n"
		indexPageHtml += "MMMMMM8..:~,,.......887~=I7$$?++==MMMMMM\n"
		indexPageHtml += "MMMMMMD..,=:.,I+=:..:=+87ZZZOOOOOZ7ZMMMM\n"
		indexPageHtml += "MMMMMMN..,:,.,$??=..++7Z=7I+I$77$Z$?DMMM\n"
		indexPageHtml += "MMMMMMN,.,::.,$II=..~+O+?I$I7Z$77IIOMMMM\n"
		indexPageHtml += "MMMMMMM~.....,7II+..=ZI+??7I?77III+$IZMM\n"
		indexPageHtml += "MMMMM$I?+:....7$7?..$$++++???IIII?+7OMMM\n"
		indexPageHtml += "MMOII?=~~=III??I7I.,O++++++?+?I?+=$MMMMM\n"
		indexPageHtml += "MMO$$$77III??II77$7I?======+++?+=+OMMMMM\n"
		indexPageHtml += "MMMMMMN8ZZ$$7II77I?$===~~~~==++?=$MMMMMM\n"
		indexPageHtml += "MMMMMMMMMMMN8OZZ$7~+I?+=~:~~==?+IDMMMMMM\n"
		indexPageHtml += "MMMMMMMMMMMMMMMMN7=IOZ$$I??III7+OMMMMMMM\n"
		indexPageHtml += "MMMMMMMMMMMMMMMMMMD$~IN?=$8O7=.$NMMMMMMM\n"
		indexPageHtml += "MMMMMMMMMMMMMMMMMMMM?I+=~ZI~$IIOMMMMMMMM\n"
		indexPageHtml += "MMMMMMMMMMMMMMMMMMMMMMMM87IIO8MMMMMMMMMM\n"
		indexPageHtml += "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\n"
		
		indexPageHtml += "Installed........... Yes\n"
		indexPageHtml += "Indigo Directory.... " + __file__ + "\n"
		
		# test the SQL Logger plugin...
		indexPageHtml += "SQL Logger.......... "
		sqlLoggerPrefPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Preferences/Plugins/com.perceptiveautomation.indigoplugin.sql-logger.indiPref"))
		if os.path.exists(sqlLoggerPrefPath) == False:
			sqlLoggerPrefPath = ""
			
		if sqlLoggerPrefPath == "":
			indexPageHtml += "Not found at default path.\n"
		else:
			indexPageHtml += "Found!\n"
			indexPageHtml += "SQL Logger Config... "
			dbConnParams = self.readSQLLoggerPreferences(sqlLoggerPrefPath)
			indexPageHtml += str(dbConnParams)
			indexPageHtml += "\n"
			indexPageHtml += "SQL Logger Test..... "
			dbConn = self.getDatabaseConnection()
			if dbConn is None:
				indexPageHtml += "Fail! Check the SQL Logger Plugin configuration\n"
			else:
				indexPageHtml += "Success!\n"
				dbConn.CloseSqlConnection()
				
		indexPageHtml += "</pre>"
		indexPageHtml += "</body></html>"
		return indexPageHtml
	index.exposed = True
		
		
	#/////////////////////////////////////////////////////////////////////////////////////
	# HousePad IWS/Plugin Management
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the version of this (IWS) plugin
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getVersionInfo(self):
		return "v" + MAJOR_VERSION + "." + MINOR_VERSION
	getVersionInfo.exposed = True
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will allow execution of arbitrary plugin actions from the HousePad
	# client
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def executePluginAction(self, **kwargs):
		# rebuild the full URL that will be used to pass the execution on to the full
		# Indigo Plugin
		pluginQuery = "/AndroidClientHelper/executePluginAction?"
		isFirstArgument = True
		for k,v in kwargs.iteritems():
			if isFirstArgument == False:
				pluginQuery = pluginQuery + "&"
			else:
				isFirstArgument = False
			pluginQuery = pluginQuery + urllib.quote(k, '') + "=" + urllib.quote(v, '')
			
		# execute the GET against the plugin's web server now
		conn = httplib.HTTPConnection("localhost", "9176")
		conn.connect()
		request = conn.putrequest("GET", pluginQuery)
		conn.endheaders()

		responseToAction = conn.getresponse()
		responseToActionText = responseToAction.read()
		
		return responseToActionText
	executePluginAction.exposed = True
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will allow an Android device to un-pair itself to an Indigo device
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def unregisterAndroidDevice(self, deviceId="0", pairingId="0", allowOverwrite="0"):
		if deviceId == "0" or pairingId == "0":
			return "ERROR: Exception Processing Request"
		else:
			# execute the GET against the plugin's web server now
			conn = httplib.HTTPConnection("localhost", "9176")
			conn.connect()
			request = conn.putrequest("GET", "/AndroidClientHelper/unregisterAndroidDevice?deviceId=" + str(deviceId) + "&pairingId=" + str(pairingId) + "&allowOverwrite=" + str(allowOverwrite))
			conn.endheaders()

			responseToAction = conn.getresponse()
			responseToActionText = responseToAction.read()
		
			return responseToActionText
	unregisterAndroidDevice.exposed = True
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will allow an Android device to pair itself to an Indigo device
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def registerAndroidDevice(self, deviceId="0", pairingId="0", allowOverwrite="0"):
		if deviceId == "0" or pairingId == "0":
			return "ERROR: Exception Processing Request"
		else:
			# execute the GET against the plugin's web server now
			conn = httplib.HTTPConnection("localhost", "9176")
			conn.connect()
			request = conn.putrequest("GET", "/AndroidClientHelper/registerAndroidDevice?deviceId=" + urllib.quote_plus(deviceId) + "&pairingId=" + urllib.quote_plus(pairingId) + "&allowOverwrite=" + urllib.quote_plus(allowOverwrite))
			conn.endheaders()

			responseToAction = conn.getresponse()
			responseToActionText = responseToAction.read()
		
			return responseToActionText
	registerAndroidDevice.exposed = True
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine allows a mobile device to update its current status/state within the
	# Indigo device system
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def updateAndroidDeviceStates(self, pairingId="", deviceModel="", batteryStatus="", batteryLevel=-1, longitude="", latitude="", locationFixTime=""):
		if not pairingId == u'':
			# execute a GET against the plugin's web server to complete the action
			conn = httplib.HTTPConnection("localhost", "9176")
			conn.connect()
			request = conn.putrequest("GET", "/AndroidClientHelper/updateMobileDeviceStates?pairingId=" + urllib.quote_plus(pairingId) + "&deviceModel=" + urllib.quote_plus(deviceModel) + "&batteryStatus=" + urllib.quote_plus(batteryStatus) + "&batteryLevel=" + urllib.quote_plus(batteryLevel) + "&longitude=" + urllib.quote_plus(longitude) + "&latitude=" + urllib.quote_plus(latitude) + "&locationFix=" + urllib.quote_plus(locationFixTime))
			conn.endheaders()

			responseToAction = conn.getresponse()
			responseToActionText = responseToAction.read()
		
			return responseToActionText
	updateAndroidDeviceStates.exposed = True
	
	
	#/////////////////////////////////////////////////////////////////////////////////////
	# Indigo Object History Retrieval
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will obtain the list of variable changes for a given variable and
	# number of historical items
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getVariableHistory(self, variableId, maxRecords=10, startEntryId=0):
		sqlConn = None
		try:
			# attempt to connect to the database
			sqlConn = self.getDatabaseConnection()
			if sqlConn is None:
				return "ERROR 99: SQL Logger not configured"
			
			# create the table that will hold the variable's history and ensure that it
			# exists (e.g. the user may not be logging variable histories)
			variableHistoryTableName = "variable_history_" + str(long(variableId))
			if sqlConn.TableExists(variableHistoryTableName) == False:
				return "Table does not exist..." + variableHistoryTableName
			else:
				sqlQueryText = "SELECT id, " + sqlConn.getLocalTimestampColumn("ts") + ", value FROM " + variableHistoryTableName
				if startEntryId > 0:
					sqlQueryText = sqlQueryText + " WHERE id < " + str(startEntryId)
				sqlQueryText = sqlQueryText + " ORDER BY ts desc" + " LIMIT " + str(maxRecords)
				
				sqlConn.ExecuteSQL(sqlQueryText)
				jsonWriter = jsonUtil.JsonWriter()
				return jsonWriter.write(self.sqlCursorToJSON(sqlConn))
		except Exception, e:
			return str(e)
			
		finally:
			if sqlConn is not None:
				sqlConn.CloseSqlConnection()		
	getVariableHistory.exposed = True
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will obtain the list of device state changes for a given device and
	# number of historical items
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getDeviceHistory(self, deviceId, maxRecords=10, startId=0):
		sqlConn = None
		try:
			# attempt to connect to the database
			sqlConn = self.getDatabaseConnection()
			if sqlConn is None:
				return "ERROR 99: SQL Logger not configured"
			
			# create the table name that will hold the variable's history and ensure that it
			# exists (e.g. the user may not be logging variable histories)
			deviceHistoryTableName = "device_history_" + str(long(deviceId))
			if sqlConn.TableExists(deviceHistoryTableName) == False:
				return "Table does not exist..." + deviceHistoryTableName
			else:
				columnDict = sqlConn.GetTableColumnNamesAndTypes(deviceHistoryTableName)
				columnSelectList = ""
				historyReturnColList = ""
				historyReturnTypeList = ""
				for key in columnDict:
					# value/column separator
					if len(columnSelectList) > 0:
						columnSelectList += ","
						historyReturnColList += ","
						historyReturnTypeList += ","
						
					# key is the actual value or column
					columnName = key
					if columnDict.get(key).find("timestamp") >= 0:
						columnName = sqlConn.getLocalTimestampColumn(key)
						
					if key.find('"') == -1:
						columnSelectList += columnName
						historyReturnColList += '"' + key + '"'
						historyReturnTypeList += '"' + columnDict.get(key) + '"'
					else:
						columnSelectList += columnName
						historyReturnColList += key
						historyReturnTypeList += columnDict.get(key)
				historyReturn = "[[" + historyReturnColList + "],[" + historyReturnTypeList + "],"
				
				sqlCommandText = "SELECT " + columnSelectList + " FROM " + deviceHistoryTableName
				if startId > 0:
					sqlCommandText = sqlCommandText + " WHERE id < " + str(startId)
				sqlCommandText = sqlCommandText + " ORDER BY ts desc" + " LIMIT " + str(maxRecords)
				sqlConn.ExecuteSQL(sqlCommandText)
				
				jsonWriter = jsonUtil.JsonWriter()
				historyReturn = historyReturn + jsonWriter.write(self.sqlCursorToJSON(sqlConn)) + "]"
				
				return historyReturn
		except Exception, e:
			return str(e)
			
		finally:
			if sqlConn is not None:
				sqlConn.CloseSqlConnection()		
	getDeviceHistory.exposed = True


	#/////////////////////////////////////////////////////////////////////////////////////
	# Google Home/Assistant Routines
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Called by Firebase functions in order to request the device definitions for all
	# devices
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def googleHomeSyncAllDevices(self):
		# execute the GET against the plugin's web server now
		conn = httplib.HTTPConnection("localhost", "9176")
		conn.connect()
		request = conn.putrequest("GET", "/AndroidClientHelper/googleHomeSyncAllDevices")
		conn.endheaders()

		responseToAction = conn.getresponse()
		responseToActionText = responseToAction.read()
	
		return responseToActionText
	googleHomeSyncAllDevices.exposed = True
	
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Exposed call that allows the Firebase functions fulfilling Google Home status
	# requests 
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def googleHomeRequestStatus(self, devices):
		# execute the GET against the plugin's web server now
		conn = httplib.HTTPConnection("localhost", "9176")
		conn.connect()
		request = conn.putrequest("GET", "/AndroidClientHelper/googleHomeRequestStatus?devices=" + devices)
		conn.endheaders()

		responseToAction = conn.getresponse()
		responseToActionText = responseToAction.read()
	
		return responseToActionText
	googleHomeRequestStatus.exposed = True

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# Public execution request that originates from the Google Assistant (Firebase Cloud
	# Functions). Requires the list of devices and list of commands to execute, both in
	# JSON format
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def googleHomeExecuteRequest(self, command):
		# execute the GET against the plugin's web server now
		conn = httplib.HTTPConnection("localhost", "9176")
		conn.connect()
		request = conn.putrequest("GET", "/AndroidClientHelper/googleHomeExecuteRequest?command=" + unicode(command))
		conn.endheaders()

		responseToAction = conn.getresponse()
		responseToActionText = responseToAction.read()
	
		return responseToActionText
	googleHomeExecuteRequest.exposed = True


	#/////////////////////////////////////////////////////////////////////////////////////
	# Utility Routines
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will obtain a connection to the PostGRE or SQLLite database
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getDatabaseConnection(self):
		# read in the parameters from the SQL Logger preferences file... since this info
		# is not available directly it must come from the file system
		sqlLoggerPrefPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Preferences/Plugins/com.perceptiveautomation.indigoplugin.sql-logger.indiPref"))
		if os.path.exists(sqlLoggerPrefPath) == False:
			return None
			
		dbConfig = self.readSQLLoggerPreferences(sqlLoggerPrefPath)
		if dbConfig["dbType"] == indigosql.kDbType_sqlite:
			return indigosql.IndigoSqlite(dbConfig["dbName"], None, self.logMessage, None)
		elif dbConfig["dbType"] == indigosql.kDbType_postgres:
			return indigosql.IndigoPostgresql(dbConfig["serverHost"], dbConfig["sqlUsername"], dbConfig["sqlPassword"], dbConfig["dbName"], None, self.logMessage, None)
		else:
			return None
			
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will read the preferences file from the SQL Logger plugin
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def readSQLLoggerPreferences(self, prefFilePath):
		configParams = dict()
		
		try:
			preferencesDom = xml.etree.ElementTree.parse(prefFilePath)
			prefRootNode = preferencesDom.getroot()
		
			databaseTypeStr = prefRootNode.find("databaseType").text
			if databaseTypeStr == "postgresql":
				configParams["dbType"] = indigosql.kDbType_postgres
				configParams["dbName"] = prefRootNode.find("postgresqlDatabase").text
				configParams["serverHost"] = prefRootNode.find("postgresqlHost").text
				configParams["sqlUsername"] = prefRootNode.find("postgresqlUser").text
				configParams["sqlPassword"] = prefRootNode.find("postgresqlPassword").text
			else:
				sqlLiteFilePath = prefRootNode.find("sqliteFilePath").text
				if sqlLiteFilePath == u'':
					sqlLiteFilePath = prefRootNode.find("sqliteFilePath").text
				configParams["dbType"] = indigosql.kDbType_sqlite
				configParams["dbName"] = sqlLiteFilePath
		except:
			pass
			
		return configParams
		
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine will convert a database cursor to a JSON array
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def sqlCursorToJSON(self, dbConn, singleRow=False):
		r = [dict((dbConn.sqlCursor.description[i][0], value) for i, value in enumerate(row)) for row in dbConn.FetchAll()]
		return (r[0] if r else None) if singleRow else r
	
		