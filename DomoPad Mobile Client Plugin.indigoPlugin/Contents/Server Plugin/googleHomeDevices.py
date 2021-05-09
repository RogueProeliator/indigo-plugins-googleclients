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