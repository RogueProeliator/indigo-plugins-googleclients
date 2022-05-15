#! /usr/bin/env python
# -*- coding: utf-8 -*-
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////
# Domotics Pad Client Plugin by RogueProeliator <adam@duncanwaredevelopment.com>
# /////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////

# /////////////////////////////////////////////////////////////////////////////////////////
# Python imports
# /////////////////////////////////////////////////////////////////////////////////////////
import indigo
import RPFramework

# /////////////////////////////////////////////////////////////////////////////////////////
# GoogleDeviceTypesDefinition
# Dictionary which defines the available Google Home device types and stores the
# recommended traits to support for the device type in order to allow the most complete
# control/user experience "out of the box"
# /////////////////////////////////////////////////////////////////////////////////////////
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

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Maps an Indigo device (object) to the proper/default Google Assistant device type
# that may be found in the types dictionary
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
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


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Builds a Google Device sync definition for the given device utilizing the Global Props
# defined by the user as well as the Indigo type
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def buildGoogleHomeDeviceDefinition(device):
    # do not check the published flag so that this routine may be used without explicit
    # options... full implementations should only pass in published devices
    global_props = device.sharedProps

    # retrieve the device type for the Google Assistant device
    google_dev_type = global_props.get('googleClientAsstType', '')
    if google_dev_type == '':
        google_dev_type = mapIndigoDeviceToGoogleType(device)

    # retrieve the name of the device as defined by the user
    google_dev_name = global_props.get('googleClientAsstName', '')
    if google_dev_name == '':
        google_dev_name = device.name

    device_defn_dict = {
        'id': RPFramework.RPFrameworkUtils.to_unicode(device.id),
        'type': googleDeviceTypesDefn[google_dev_type]['DeviceType'],
        'traits': list(googleDeviceTypesDefn[google_dev_type]['Traits']),
        'name': {
            'defaultNames': [google_dev_name],
            'name': google_dev_name
        },
        'willReportState': False,
        'deviceInfo': {
            'manufacturer': 'Indigo',
            'model': device.model
        }
    }
    return device_defn_dict


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Builds the response for Google Assistant in the format required for updating the
# Google Home Graph with the current status/state of the device provided
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def buildGoogleHomeDeviceStatusUpdate(device):
    # configuration information is found in the global properties collection
    global_props = device.sharedProps

    # retrieve the device type for the Google Assistant device
    google_dev_type = global_props.get('googleClientAsstType', '')
    if google_dev_type == '':
        google_dev_type = mapIndigoDeviceToGoogleType(device)

    # the status returned depends on the traits that are defined for this
    # device (dependent upon the device type)
    device_status_traits = {}
    for trait in googleDeviceTypesDefn[google_dev_type]['Traits']:
        if trait == 'action.devices.traits.Brightness':
            device_status_traits['brightness'] = device.states.get('brightnessLevel', 0)
        elif trait == 'action.devices.traits.ColorSetting':
            # not yet implemented... could be added to Light type as an RGB state, such
            # as for Hue lights
            pass
        elif trait == 'action.devices.traits.OnOff':
            device_status_traits['on'] = device.states.get('onOffState', False)

    # the online status will simply be if the device is enabled; should we look at a status
    # value?
    device_status_traits['online'] = device.configured and device.enabled and device.states.get('errorState', '') == ''
    
    # return the trait/state dictionary back... note that the device ID will need
    # to be set as the key to this by the calling procedure
    return device_status_traits
        
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# Processes the EXECUTE intent against the given device IDs; note that multiple
# commands may be present. The return is the results of the action in the format
# expected by the Google Assistant for this particular execute command
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
def processExecuteRequest(commandsList):
    # the response object contains a list of devices that fall into each status; this will
    # be a dictionary of status with a value being the list of devices
    device_status_results = {}

    # there may be multiple commands to execute in the array
    for commandDefn in commandsList:
        # build the list of devices against which we must execute the
        # command(s) provided
        devices_list = []
        for deviceId in commandDefn['devices']:
            indigo_device = indigo.devices[int(deviceId['id'])]
            devices_list.append(indigo_device)
            if indigo_device.id not in device_status_results:
                device_status_results[indigo_device.id] = ''

        # loop through each device, executing the requested commands only if they are
        # valid for the device type found
        for device in devices_list:
            # determine if the device is online and configured; otherwise it cannot accept the command
            is_device_online = device.configured and device.enabled and device.states.get('errorState', '') == ''

            # execute the requested command, if available
            if not is_device_online:
                device_status_results[device.id] = 'OFFLINE'
            else:
                for execCommand in commandDefn['execution']:
                    command_id = execCommand['command']
                    if command_id == 'action.devices.commands.OnOff':
                        if execCommand['params']['on']:
                            indigo.device.turnOn(device.id)
                        else:
                            indigo.device.turnOff(device.id)
                
                # mark the execution as pending since the commands are generally asynchronous in
                # nature... the statuses will be updated when the device changes
                if device_status_results[device.id] == '':
                    device_status_results[device.id] = 'PENDING'
    
    # formulate the return... this is an array with a new result dictionary for each
    # status within the devices results
    command_return = []
    success_devices = {'ids': [], 'status': 'SUCCESS'}
    pending_devices = {'ids': [], 'status': 'PENDING'}
    error_devices   = {'ids': [], 'status': 'ERROR'}
    offline_devices = {'ids': [], 'status': 'OFFLINE'}

    # add each device result to the appropriate list
    for deviceId, result in device_status_results.items():
        if result == 'SUCCESS':
            success_devices['ids'].append(str(deviceId))
        elif result == 'PENDING':
            pending_devices['ids'].append(str(deviceId))
        elif result == 'ERROR':
            error_devices['ids'].append(str(deviceId))
        elif result == 'offlineDevices':
            offline_devices['ids'].append(str(deviceId))

    # build the composite results array
    if len(success_devices['ids']) > 0:
        command_return.append(success_devices)
    if len(pending_devices['ids']) > 0:
        command_return.append(pending_devices)
    if len(error_devices['ids']) > 0:
        command_return.append(error_devices)
    if len(offline_devices['ids']) > 0:
        command_return.append(offline_devices)
    
    return command_return
