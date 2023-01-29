const functions = require('firebase-functions');
const {smarthome} = require('actions-on-google');
const {google} = require('googleapis');
const util = require('util');
const admin = require('firebase-admin');

// initialize Firebase
admin.initializeApp();
const firebaseRef = admin.database().ref('/');

// initialize the Google Homegraph
const auth = new google.auth.GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/homegraph'],
});
const homegraph = google.homegraph({
  version: 'v1',
  auth: auth,
});

// create the main smart home application
const smartHomeApp = smarthome();


// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// SMART HOME ACTIONS FUNCTIONS
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
smartHomeApp.onSync(async (body, headers) => {
    console.log('Sync request received');

    // retrieve the reflector URL that is associated with this Bearer token/account
    // (we will first check caching value, then retrieve if necessary)
    const reflectorUrl = await retrieveReflectorUrlForUser(headers);

    // call into the Indigo server to retrieve the list of Google Home published
    // devices (using the reflector URL)
    console.log('Retrieving devices...')
    const publishedDevices = await executeIndigoRequest(reflectorUrl, headers.authorization, 'google_home_event_sync_request', '')
    console.log('Received: ' + JSON.stringify(publishedDevices));
    
    console.log('Returning devices...');
    return {
        requestId: body.requestId,
        payload: {
            agentUserId: '1234',
            devices: publishedDevices
        }
    };
});

// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// UTILITY (NON-PUBLISHED) FUNCTIONS
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// retrieves the reflector URL to utilize in fulfilling all Indigo related queries; it does so
// by talking with the IndigoDomo server "as the user" via the OAuth token in the header
const retrieveReflectorUrlForUser = async (headers) => {
    var bearerToken = headers.authorization;
    console.log('Requesting reflector URL with token: ' + bearerToken);

    // retrieve the token from the IndigoDomo servers
    var requestOptions = {
        hostname: 'www.indigodomo.com',
        port: 443,
        path: '/api/v3/integrations/reflector-url',
        method: 'GET',
        headers: {
            'Authorization': bearerToken,
            'Accept': "*/*"
        },
        responseType: 'json'
    };
    
    const reflectorUrls = await webRequest('https://www.indigodomo.com/api/v3/integrations/reflector-url', requestOptions).json();
    console.log('Reflector Url: ' + reflectorUrls.reflector_url)

    return reflectorUrls.reflector_url;
};

// executes a command/request against the Google Client helper plugin, returning the result as a JSON
// parsed object
const executeIndigoRequest = async(reflectorUrl, authToken, commandName, payload) => {
    var fullPath = '/message/com.duncanware.domoPadMobileClient/' + commandName
    if (payload != '')
        fullPath += '?' + payload

    var requestOptions = {
        hostname: reflectorUrl,
        port: 443,
        path: fullPath,
        method: 'GET',
        headers: {
            'Authorization': authToken,
            'Accept': '*/*'
        },
        responseType: 'json'
    };

    const indigoResponse = await webRequest('https://' + reflectorUrl + fullPath, requestOptions).json();
    return indigoResponse;
}

// export the smart home action / handler
exports.smarthome = functions.https.onRequest(smartHomeApp);