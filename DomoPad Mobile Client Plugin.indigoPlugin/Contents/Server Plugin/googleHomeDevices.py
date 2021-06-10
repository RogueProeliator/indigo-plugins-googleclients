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

SUPPORTED_INDIGO_CLASSES = {
    indigo.DimmerDevice      : indigo.kDimmerDeviceSubType,
    indigo.SensorDevice      : indigo.kSensorDeviceSubType,
    indigo.RelayDevice       : indigo.kRelayDeviceSubType,
    indigo.SpeedControlDevice: None,
    indigo.ThermostatDevice  : None,
}

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Maps an Indigo device (object) to the proper/default Google Assistant device type
# that may be found in the types dictionary
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def getAvailableSubtypesForDevice(device):
    try:
        subtype_meta = SUPPORTED_INDIGO_CLASSES[device.__class__]
        subtypes = [getattr(subtype_meta, a) for a in dir(subtype_meta) if not a.startswith('__')]
        subtype_list = [(v, v) for v in subtypes]

        subtype_list.sort(key=lambda x: x[1])
        return subtype_list
    except TypeError:
        return []
    except:
        return [("invalid", "invalid device type")]

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Determines the sub type of a device based upon a specified sub type, a device
# property or hints based upon device properties
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def getDeviceSubType(device):
    if device.__class__ not in SUPPORTED_INDIGO_CLASSES or SUPPORTED_INDIGO_CLASSES[device.__class__] is None:
        return None

    # At some point, we might want to allow the device owner to give us a hint about it's subType, though once we
    # actually implement the subType property on a device that might be enough. So, TBD - we won't document this
    # yet.
    override_subtype = device.sharedProps.get(u"googleClientAsstType", None)
    if device.pluginProps.get("sub-type"): override_subtype = device.pluginProps.get("sub-type")
    sub_type = override_subtype if override_subtype else device.subType

    if sub_type == "Light":
        # The Insteon FanLinc light has type "Light". Others may as well, we're going to assume they are dimmers.
        sub_type = indigo.kDimmerDeviceSubType.Dimmer
    elif sub_type == "Strobe":
        # The Fortrezz siren/strobe device has "Strobe" for subtype, so we're going to map that to a standard relay device.
        sub_type = indigo.kRelayDeviceSubType.Switch
    elif sub_type == "Motion Sensor":
        sub_type = indigo.kSensorDeviceSubType.Motion
    elif sub_type == "Door Sensor":
        sub_type = indigo.kSensorDeviceSubType.DoorWindow
    elif sub_type == "Tilt Sensor":
        sub_type = indigo.kSensorDeviceSubType.DoorWindow
    if not sub_type:
        # So, no subtype was specified either through an override property or by the device's subType property. We
        # will use some extra logic to attempt to sus out the subtype.
        if type(device) == indigo.DimmerDevice:
            # So dimmer devices can be used for a variety of things: fans, shades/blinds, etc. They can also support
            # color settings or be a plug in (wall wart).
            if "plug" in device.model.lower():
                # This will normally mean that it's a plug-in device.
                sub_type = indigo.kDimmerDeviceSubType.PlugIn
            elif "blind" in device.name.lower() or "shade" in device.name.lower():
                # This one is harder to detect, but if they have the word blind or shade in the device name, we can
                # assume that it's a blind
                sub_type = indigo.kDimmerDeviceSubType.Blind
            elif "fan" in device.name.lower() or "fan" in device.model.lower():
                # Similar to blinds and shades, if fan is in the name it's likely a fan.
                sub_type = indigo.kDimmerDeviceSubType.Fan
            elif "bulb" in device.name.lower() or "bulb" in device.model.lower():
                if device.supportsColor:
                    # Color dimmer
                    sub_type = indigo.kDimmerDeviceSubType.ColorBulb
                else:
                    sub_type = indigo.kDimmerDeviceSubType.Bulb
            elif "valve" in device.name.lower() or "valve" in device.model.lower():
                # Similar to blinds and shades, if fan is in the name it's likely a fan.
                sub_type = indigo.kDimmerDeviceSubType.Valve
            else:
                if device.supportsColor:
                    # Color dimmer
                    sub_type = indigo.kDimmerDeviceSubType.ColorDimmer
                else:
                    # Everything else will just be a dimmer
                    sub_type = indigo.kDimmerDeviceSubType.Dimmer
        elif type(device) == indigo.RelayDevice:
            if "plug" in device.model.lower() or "plug" in device.name.lower() or "module" in device.model.lower():
                # This will normally mean that it's a plug-in device.
                sub_type = indigo.kRelayDeviceSubType.PlugIn
            elif "lock" in device.model.lower() or "lock" in device.name.lower() or device.ownerProps.get("isLockSubType", False):
                # Look specifically to see if this is Joe's MyQ device, which is actually a GarageController
                if device.pluginId == "com.flyingdiver.indigoplugin.myq" and device.deviceTypeId == "myqOpener":
                    sub_type = indigo.kRelayDeviceSubType.GarageController
                else:
                    sub_type = indigo.kRelayDeviceSubType.Lock
            elif "siren" in device.model.lower() or "siren" in device.name.lower():
                sub_type = indigo.kRelayDeviceSubType.Siren
            elif "strobe" in device.model.lower() or "strobe" in device.name.lower():
                sub_type = indigo.kRelayDeviceSubType.Siren
            elif "garage" in device.model.lower() or "garage" in device.name.lower():
                sub_type = indigo.kRelayDeviceSubType.GarageController
            elif "outlet" in device.model.lower() or "outlet" in device.name.lower():
                sub_type = indigo.kRelayDeviceSubType.GarageController
            else:
                sub_type = indigo.kRelayDeviceSubType.Switch
        elif type(device) == indigo.SensorDevice:
            if "door" in device.model.lower() or "window" in device.model.lower() or "open" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.DoorWindow
            if "door" in device.name.lower() or "window" in device.name.lower():
                sub_type = indigo.kSensorDeviceSubType.DoorWindow
            elif "motion" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.Motion
            elif "smoke" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.Smoke
            elif "co2" in device.model.lower() or "carbon" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.CO
            elif "tamper" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.Tamper
            elif "uv" in device.model.lower() or "ultraviolet" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.CO
            elif "illuminance" in device.model.lower() or "illuminance" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.Illuminance
            elif "vibration" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.Vibration
            elif "glass" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.GlassBreak
            elif "gas" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.GasLeak
            elif "pressure" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.Pressure
            elif "water" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.WaterLeak
            elif "vibration" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.Vibration
            elif "voltage" in device.model.lower():
                sub_type = indigo.kSensorDeviceSubType.Voltage
            else:
                sub_type = indigo.kSensorDeviceSubType.Binary
    return sub_type