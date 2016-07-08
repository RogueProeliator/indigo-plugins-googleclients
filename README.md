#Introduction
Domotics Pad is able to talk to Indigo using several different techniques, depending upon the operation. However, sometimes Domotics Pad needs to do something that is beyond the scope of the "normal" Indigo communication. In these instances, Domotics Pad relies on an Indigo Plugin to extend Indigo's functionality. Domotics Pad will run without completing these steps, but with reduced functionality.


#Optional Software: Enable SQL Logger Plugin
Indigo Domotics includes an excellent plugin with Indigo that allows you to log historical changes to devices, variables, events, etc. Domotics Pad is able to utilize the data collected by this plugin to show you the historical changes of devices & variables.

The SQL Logger plugin is not enabled by default, but setting it up is very easy. For most users, simply enabling the plugin from the menu and settings its configuration is all that is required. If you would like additional information about the options, please see the [SQL Logger Plugin Documentation](http://www.indigodomo.com/wiki/doku.php?id=plugins:sql_logger) or post your question on the [SQL Logger Forum](http://forums.indigodomo.com/viewforum.php?f=98).

#Installation and Configuration
###Obtaining the Plugin
The latest released version is always available on the Releases tab and is the recommended version to use for your system. Alternatively, you may wish to download the source of this repository which includes all files necessary to install and utilize the plugin.

###Configuring the Plugin
Upon first installation you will be asked to configure the plugin; please see the instructions on the configuration screen for more information. Most users will be fine with the defaults unless an email is desired when a new version is released.<br />
![Plugin Configuration Screen](<Documentation/Help/PluginConfigurationScreen.png>)

#Plugin Devices
###Android Remote Client
You are not required to create Indigo devices for each physical Android device that you wish to use Domotics Pad; however, creating devices will allow you some advanced functionality such as sending the device push notifications and alerts. When you create a new device of type Android Remote Client, you will see the following configuration screen:<br />
![Android Remote Client Configuration Screen](<Documentation/Help/AndroidClientDeviceConfigScreen.png>)

You need only click the Save button on this screen! Once you have paired a device (see below), the pairing ID will appear here; if you wish to deauthorize a device from receiving notifications or other (future) features, you need only return and click the Clear Pairing (this allows you to easily clear, rather than delete, the Indigo device should you get a new phone/tablet/etc.)

###Pairing via Domotics Pad
Once you have the Indigo device created, you can now pair the physical Android device. To do so, launch DomoPad on your device and navigate to the Indigo device via the Devices screen. You should see the new device with a status of "Not Paired":<br />
![Domotics Pad Devices Screen](<Documentation/Help/DomoticsPad_DeviceListing_Unpaired.png>)

Single touch on the device to bring up its default action; click the Pair button to complete the process:<br />
![Domotics Pad Pairing Screen](<Documentation/Help/DomoticsPad_DeviceListing_PairAction.png>)

#Available Device states
The plugin tracks several states of the client device; most, however, require that the device enable the Indigo Status Updates within the Domotics Pad application.  Please see the settings screen of the application on your mobile device for more information.

- **isPaired** - Tracks whether or not the Indigo device has been paired to a mobile device
- **modelName** - The model name of the paired device
- **batteryLevel** - Battery level (0 - 100) of the mobile device
- **batteryStatus** - The current battery status of the device (Charged / NotCharging)
- **longitude** - The longitude coordinate from the devices GPS; only available if you have opted to send location info within the Domotics Pad mobile device's settings
- **latitude** - The latitude coordinate from the devices GPS; only available if you have opted to send location info within the Domotics Pad mobile device's settings
- **locationFixTime** - The time that the last GPS coordinate was obtained; only available if you have opted to send location info within the Domotics Pad mobile device's settings

#Available Actions
- **Send Push Notification Message** - Allows sending a push notification to a paired client device; the configuration screen has detailed information on the options and features available:<br />
![Push Notification Action Configuration Screen](<Documentation/Help/PushNotificationConfigScreen.png>)