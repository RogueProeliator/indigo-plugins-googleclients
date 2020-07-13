#! /usr/bin/env python
# -*- coding: utf-8 -*-
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////
# Domotics Pad Google Client Plugin by RogueProeliator <rp@rogueproeliator.com>
# 	See plugin.py for more plugin details and information
#/////////////////////////////////////////////////////////////////////////////////////////
#/////////////////////////////////////////////////////////////////////////////////////////

#/////////////////////////////////////////////////////////////////////////////////////////
# Python imports
#/////////////////////////////////////////////////////////////////////////////////////////
import os
import Queue
import re
import string
import sys
import threading
import json

import indigo
import RPFramework

#/////////////////////////////////////////////////////////////////////////////////////////
# GoogleDeviceTypesDefinition
#	Dictionary which defines the available Google Home device types and stores the 
#   recommended traits to support for the device type in order to allow the most complete
#   control/user experience "out of the box"
#/////////////////////////////////////////////////////////////////////////////////////////
googleDeviceTypesDefn = {
    'action.devices.types.DOOR': 
        {'Device': 'Door', 'DeviceType': 'action.devices.types.DOOR',
            'Description': 'Door can be opened and closed, potentially in more than one direction.',
            'Traits': ['action.devices.traits.OpenClose']},
    'action.devices.types.FAN': 
        {'Device': 'Fan', 'DeviceType': 'action.devices.types.FAN', 
            'Description': 'Fans can typically be turned on and off and have speed settings. Some fans may also have additional supported modes, such as fan direction/orientation (for example, a wall unit may have settings to adjust whether it blows up or down).', 
            'Traits': ['action.devices.traits.FanSpeed', 'action.devices.traits.Modes', 'action.devices.traits.OnOff', 'action.devices.traits.Toggles']},
    'action.devices.types.LIGHT': 
        {'Device': 'Light', 'DeviceType': 'action.devices.types.LIGHT',
            'Description': 'This type indicates that the device gets the light bulb icon and some light synonyms/aliases.',
            'Traits': ['action.devices.traits.Brightness', 'action.devices.traits.OnOff']},
    'action.devices.types.LOCK': 
        {'Device': 'Lock', 'DeviceType': 'action.devices.types.LOCK',
            'Description': 'Locks can lock, unlock, and report a locked state. Unlocking is a security sensitive action which can require two-factor authentication.',
            'Traits': ['action.devices.traits.LockUnlock']},
    'action.devices.types.OUTLET': 
        {'Device': 'Outlet', 'DeviceType': 'action.devices.types.OUTLET',
            'Description': 'This type indicates that the device gets the plug icon and some outlet synonyms/aliases.',
            'Traits': ['action.devices.traits.OnOff']},
    'action.devices.types.SENSOR':
        {'Device': 'Sensor', 'DeviceType': 'action.devices.types.SENSOR',
            'Description': 'A single sensor can serve multiple functions, such as monitoring both temperature and humidity. Sensors may report either or both quantitative—for example, carbon monoxide and smoke level measured at parts per million—and qualitative measurements (such as whether air quality is healthy or unhealthy).',
            'Traits': ['action.devices.traits.HumiditySetting', 'action.devices.traits.Modes', 'action.devices.traits.OnOff', 'action.devices.traits.SensorState']},
    'action.devices.types.SWITCH':
        {'Device': 'Switch', 'DeviceType': 'action.devices.types.SWITCH',
            'Description': 'This type indicates that the device gets the switch icon and some switch synonyms/aliases.',
            'Traits': ['action.devices.traits.OnOff']},
    'action.devices.types.THERMOSTAT':
        {'Device': 'Thermostat', 'DeviceType': 'action.devices.types.THERMOSTAT',
            'Description': 'Thermostats are temperature-managing devices, with set points and modes. This separates them from heaters and AC units which may only have modes and settings (for example, high/low) vs a temperature target.',
            'Traits': ['action.devices.traits.TemperatureSetting']},
    'action.devices.types.WINDOW':
        {'Device': 'Window', 'DeviceType': 'action.devices.types.WINDOW',
            'Description': 'Windows can be opened and closed, optionally with sections that open in different directions, and may also be locked and unlocked.',
            'Traits': ['action.devices.traits.LockUnlock', 'action.devices.traits.OpenClose']}
}

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Maps an Indigo device (object) to the proper/default Google Assistant device type
# that may be found in the types dictionary
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def mapIndigoDeviceToGoogleType(device):
    if isinstance(device, indigo.DimmerDevice):
        return 'action.devices.types.LIGHT'
    elif isinstance(device, indigo.RelayDevice):
        return 'action.devices.types.SWITCH'
    elif isinstance(device, indigo.ThermostatDevice):
        return 'action.devices.types.THERMOSTAT'
    elif isinstance(device, indigo.SensorDevice):
        return 'action.devices.types.SENSOR'
    else:
        return ''

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Builds a Google Device sync definition for the given device utilizing the Global Props
# defined by the user as well as the Indigo type
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def buildGoogleHomeDeviceDefinition(device):
    # do not check the published flag so that this routine may be used without explicit
    # options... full implementations should only pass in published devices
    globalProps = device.sharedProps

    # retrieve the device type for the Google Assistant device
    googleDevType = globalProps.get('googleClientAsstType', '')
    if googleDevType == '':
        googleDevType = mapIndigoDeviceToGoogleType(device)

    # retrieve the name of the device as defined by the user
    googleDevName = globalProps.get('googleClientAsstName', '')
    if googleDevName == '':
        googleDevName = device.name

    deviceDefnDict = {
        'id': RPFramework.RPFrameworkUtils.to_unicode(device.id),
        'type': googleDeviceTypesDefn[googleDevType]['DeviceType'],
        'traits': list(googleDeviceTypesDefn[googleDevType]['Traits']),
        'name': {
            'defaultNames': [googleDevName],
            'name': googleDevName
        },
        'willReportState': False,
        'deviceInfo': {
            'manufacturer': 'Indigo',
            'model': device.model
        }
    }
    return deviceDefnDict

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Builds the response for Google Assistant in the format required for updating the
# Google Home Graph with the current status/state of the device provided
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def buildGoogleHomeDeviceStatusUpdate(device):
    # configuration information is found in the global properties collection
    globalProps = device.sharedProps

    # retrieve the device type for the Google Assistant device
    googleDevType = globalProps.get('googleClientAsstType', '')
    if googleDevType == '':
        googleDevType = mapIndigoDeviceToGoogleType(device)

    # the status returned depends on the traits that are defined for this
    # device (dependent upon the device type)
    deviceStatusTraits = {}
    for trait in googleDeviceTypesDefn[googleDevType]['Traits']:
        if trait == 'action.devices.traits.Brightness':
            deviceStatusTraits['brightness'] = device.states.get('brightnessLevel', 0)
        elif trait == 'action.devices.traits.ColorSetting':
            # not yet implemented... could be added to Light type as an RGB state, such
            # as for Hue lights
            pass
        elif trait == 'action.devices.traits.OnOff':
            deviceStatusTraits['on'] = device.states.get('onOffState', False)

    # the online status will simply be if the device is enabled; should we look at a status
    # value?
    deviceStatusTraits['online'] = device.configured and device.enabled and device.states.get('errorState', '') == ''
    
    # return the trait/state dictionary back... note that the device ID will need
    # to be set as the key to this by the calling procedure
    return deviceStatusTraits
        
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Processes the EXECUTE intent against the given device IDs; note that multiple
# commands may be present. The return is the results of the action in the format
# expected by the Google Assistant for this particular execute command
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def processExecuteRequest(commandsList):
    # the response object contains a list of devices that fall into each status; this will
    # be a dictionary of status with a value being the list of devices
    deviceStatusResults = {}

    # there may be multiple commands to execute in the array
    for commandDefn in commandsList:
        # build the list of devices against which we must execute the
        # command(s) provided
        devicesList = []
        for deviceId in commandDefn['devices']:
            indigoDevice = indigo.devices[int(deviceId['id'])]
            devicesList.append(indigoDevice)
            if not indigoDevice.id in deviceStatusResults:
                deviceStatusResults[indigoDevice.id] = ''

        # loop through each device, executing the requested commands only if they are
        # valid for the device type found
        for device in devicesList:
            # determine if the device is online and configured; otherwise it cannot accept the command
            isDeviceOnline = device.configured and device.enabled and device.states.get('errorState', '') == ''

            # execute the requested command, if available
            if isDeviceOnline == False:
                deviceStatusResults[device.id] = 'OFFLINE'
            else:
                for execCommand in commandDefn['execution']:
                    commandId = execCommand['command']
                    if commandId == 'action.devices.commands.OnOff':
                        if execCommand['params']['on'] == True:
                            indigo.device.turnOn(device.id)
                        else:
                            indigo.device.turnOff(device.id)
                
                # mark the execution as pending since the commands are generally asynchronous in
                # nature... the statuses will be updated when the device changes
                if deviceStatusResults[device.id] == '':
                    deviceStatusResults[device.id] = 'PENDING'
    
    # formulate the return... this is an arry with a new result dictionary for each
    # status within the devices results
    commandReturn = []
    successDevices = {'ids': [], 'status': 'SUCCESS' }
    pendingDevices = {'ids': [], 'status': 'PENDING' }
    errorDevices = {'ids': [], 'status': 'ERROR' }
    offlineDevices = {'ids': [], 'status': 'OFFLINE' }

    # add each device result to the appropriate list
    for deviceId, result in deviceStatusResults.items():
        if result == 'SUCCESS':
            successDevices['ids'].append(str(deviceId))
        elif result == 'PENDING':
            pendingDevices['ids'].append(str(deviceId))
        elif result == 'ERROR':
            errorDevices['ids'].append(str(deviceId))
        elif result == 'offlineDevices':
            offlineDevices['ids'].append(str(deviceId))

    # build the composite results array
    if len(successDevices['ids']) > 0:
        commandReturn.append(successDevices)
    if len(pendingDevices['ids']) > 0:
        commandReturn.append(pendingDevices)
    if len(errorDevices['ids']) > 0:
        commandReturn.append(errorDevices)
    if len(offlineDevices['ids']) > 0:
        commandReturn.append(offlineDevices)
    
    return commandReturn