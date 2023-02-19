const functions = require('firebase-functions');
const chai      = require('chai');
const assert    = chai.assert;
const sinon     = require('sinon');
const admin     = require('firebase-admin');
const test      = require('firebase-functions-test')();
const { mockRequest, mockResponse } = require('mock-req-res');

chai.use(require('sinon-chai'));

describe('Indigo Assistant Smart Home Functions', async () => {
    let adminInitStub, testEnviron, dpSmartHome;

    before(() => {
        adminInitStub = sinon.stub(admin, 'initializeApp');
        
        testEnviron = process.env;
        process.env = { 
            "FUNCTIONS_EMULATOR": true ,
            "EMULATOR_REFLECTOR": "http://10.1.1.170:8176",
            "EMULATOR_TOKEN"    : "Bearer 76a8ff7a-dbd6-4851-9222-5f5bafacb64d"
        };
        
        dpSmartHome = require('../index');
    });

    after(() => {
        adminInitStub.restore();
        test.cleanup();
        process.env = testEnviron;
    });

    describe('Test Environment Validation', async () => {
        it('should return debug connection information', async () => {
            const expected = {
                "result"   : "pong",
                "emulator" : true,
                "reflector": "http://10.1.1.170:8176",
                "token"    : "Bearer 76a8ff7a-dbd6-4851-9222-5f5bafacb64d"
            };
            const response = {
                json: (value) => {
                    assert.equal(JSON.stringify(expected), JSON.stringify(value));
                }
            };
            await dpSmartHome.ping({ query: {}, headers: {}}, response);
        })
    });

    describe('Google Synchronization Request', async () => {
        it('should return a synchronization payload from Indigo', async () => {
            const input = {
                "requestId": "ff36a3cc-ec34-11e6-b1a0-64510650abcf",
                "inputs": [{
                "intent": "action.devices.SYNC"
                }]
            };
            const expected = {
                "requestId": "ff36a3cc-ec34-11e6-b1a0-64510650abcf",
                "payload": {
                "agentUserId": "1836.15267389",
                "devices": [
                    {
                    "id": "123",
                    "type": "action.devices.types.OUTLET",
                    "traits": [
                        "action.devices.traits.OnOff"
                    ],
                    "name": {
                        "defaultNames": [
                        "My Outlet 1234"
                        ],
                        "name": "Night light",
                        "nicknames": [
                        "wall plug"
                        ]
                    },
                    "willReportState": false,
                    "roomHint": "kitchen",
                    "deviceInfo": {
                        "manufacturer": "lights-out-inc",
                        "model": "hs1234",
                        "hwVersion": "3.2",
                        "swVersion": "11.4"
                    },
                    "otherDeviceIds": [
                        {
                        "deviceId": "local-device-id"
                        }
                    ],
                    "customData": {
                        "fooValue": 74,
                        "barValue": true,
                        "bazValue": "foo"
                    }
                    },
                    {
                    "id": "456",
                    "type": "action.devices.types.LIGHT",
                    "traits": [
                        "action.devices.traits.OnOff",
                        "action.devices.traits.Brightness",
                        "action.devices.traits.ColorSetting"
                    ],
                    "name": {
                        "defaultNames": [
                        "lights out inc. bulb A19 color hyperglow"
                        ],
                        "name": "lamp1",
                        "nicknames": [
                        "reading lamp"
                        ]
                    },
                    "willReportState": false,
                    "roomHint": "office",
                    "attributes": {
                        "colorModel": "rgb",
                        "colorTemperatureRange": {
                        "temperatureMinK": 2000,
                        "temperatureMaxK": 9000
                        },
                        "commandOnlyColorSetting": false
                    },
                    "deviceInfo": {
                        "manufacturer": "lights out inc.",
                        "model": "hg11",
                        "hwVersion": "1.2",
                        "swVersion": "5.4"
                    },
                    "customData": {
                        "fooValue": 12,
                        "barValue": false,
                        "bazValue": "bar"
                    }
                    }
                ]
                }
            }
            
            const request  = mockRequest({ body: input});
            const response = mockResponse();
            
            await dpSmartHome.indigoassistant(request, response);
            chai.expect(response.json).to.have.been.calledWith(JSON.stringify(expected))
        })
    });

});
