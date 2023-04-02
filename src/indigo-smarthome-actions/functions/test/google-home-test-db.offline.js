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
            "EMULATOR_REFLECTOR": "10.1.1.170",
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
                "reflector": "10.1.1.170",
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
                    "agentUserId": "10.1.1.170",
                    "devices": [
                        {
                        "id": "309103834",
                        "type": "action.devices.types.LIGHT",
                        "traits": [
                            "action.devices.traits.Brightness",
                            "action.devices.traits.OnOff"
                        ],
                        "name": { "defaultNames": ["garage light"], "name": "garage light" },
                        "willReportState": true,
                        "deviceInfo": {
                            "manufacturer": "Indigo",
                            "model": "SwitchLinc 2-Way Dimmer"
                        },
                        "customData": { "indigoDeviceType": "", "pinRequired": false }
                        },
                        {
                        "id": "518185989",
                        "type": "action.devices.types.SWITCH",
                        "traits": ["action.devices.traits.OnOff"],
                        "name": {
                            "defaultNames": ["Office Ceiling Fan"],
                            "name": "Office Ceiling Fan"
                        },
                        "willReportState": true,
                        "deviceInfo": { "manufacturer": "Indigo", "model": "FanLinc" },
                        "customData": { "indigoDeviceType": "", "pinRequired": false }
                        },
                        {
                        "id": "1091151457",
                        "type": "action.devices.types.LIGHT",
                        "traits": [
                            "action.devices.traits.Brightness",
                            "action.devices.traits.OnOff"
                        ],
                        "name": {
                            "defaultNames": ["Office Floor Lamp"],
                            "name": "Office Floor Lamp"
                        },
                        "willReportState": true,
                        "deviceInfo": { "manufacturer": "Indigo", "model": "LampLinc V2" },
                        "customData": { "indigoDeviceType": "", "pinRequired": false }
                        }]
                }
            }
            
            const request  = mockRequest({ body: input});
            const response = mockResponse();
            
            await dpSmartHome.indigoassistant(request, response);
            chai.expect(response.json).to.have.been.calledWith(JSON.stringify(expected))
        })
    });

});
