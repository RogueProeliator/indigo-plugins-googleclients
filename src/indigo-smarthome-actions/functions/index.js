const functions        = require('firebase-functions');
const { defineString } = require('firebase-functions/params');
const {smarthome}      = require('actions-on-google');
const {google}         = require('googleapis');
const util             = require('util');
const admin            = require('firebase-admin');
const webRequest       = require('got');
const url              = require('url');

// initialize Firebase
admin.initializeApp();
const emulatorReflector = defineString("EMULATOR_REFLECTOR");
const emulatorToken     = defineString("EMULATOR_TOKEN");

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
// UTILITY ENDPOINT FUNCTIONS
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// allows verification of the Firebase function and can provide optional information
// about the current execution environment
exports.ping = functions.https.onRequest(async (req, res) => {
    // grab the query text to return to the user as a result
    const original = req.query.text;
    
    // echo the message back to the caller
    var resultMessage = original ? `Message \'${original}\' received` : 'pong';
    var reflectorUrl  = await retrieveReflectorUrlForUser(req.headers);

    res.json({
        result   : resultMessage,
        emulator : isInEmulator(),
        reflector: reflectorUrl,
        token    : authenticationToken(req.headers)
    });
  });

// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// SMART HOME ACTIONS FUNCTIONS
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
smartHomeApp.onSync(async (body, headers) => {
    // retrieve the reflector URL that is associated with this Bearer token/account
    // (we will first check caching value, then retrieve if necessary)
    const reflectorUrl = await retrieveReflectorUrlForUser(headers);
    if (!reflectorUrl) {
        return {
            requestId: body.requestId,
            payload: {
                errorCode: 'authFailure',
                debugString: 'Failed to retrieve reflector url from IndigoDomo'
            }
        };
    }

    // call into the Indigo server to retrieve the list of Google Home published
    // devices (using the reflector URL)
    const publishedDevices = await executeIndigoRequest(reflectorUrl, authenticationToken(headers), 'google_home_event_sync_request', '')

    return {
        requestId: body.requestId,
        payload: {
            agentUserId: reflectorUrl,
            devices: publishedDevices
        }
    };
});

// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// UTILITY (NON-PUBLISHED) FUNCTIONS
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// returns whether or not the current execution environment is running in
// a local emulator 
const isInEmulator = () => { return process.env.FUNCTIONS_EMULATOR === true || process.env.FUNCTIONS_EMULATOR === "true" };

// standardizes a URL given a valid URI that is in an unknown format (beginning or not with http),
// ending with a slash, etc. the standard format will NOT contain a trailing slash
const standardizeUrl = (url) => {
    const defaultProtocol = isInEmulator() ? "http" : "https";
    let standardUrl = url.startsWith("http") ? url : `${defaultProtocol}://${url}`;

    if (standardUrl.endsWith("/"))
        standardUrl = standardUrl.slice(0, -1);
    
    return standardUrl;
}

// returns the value for the authentication token given for this request
const authenticationToken = (headers) => {
    return isInEmulator() ? emulatorToken.value() : headers.authorization;
};

// retrieves the reflector URL to utilize in fulfilling all Indigo related queries; it does so
// by talking with the IndigoDomo server "as the user" via the OAuth token in the header
const retrieveReflectorUrlForUser = async (headers) => {
    // if we are running in an emulated environment, this should load the debug parameters
    // specified in the settings file
    if (isInEmulator()) {
        return emulatorReflector.value();
    }

    var bearerToken = authenticationToken(headers);
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
    var fullUri = `${standardizeUrl(reflectorUrl)}/message/com.duncanware.domoPadMobileClient/${commandName}`;
    if (payload) fullUri += `?${payload}`;
    var uri = url.parse(fullUri);

    var requestOptions = {
        hostname: uri.hostname,
        port: uri.protocol == "https" ? 443 : 8176,
        path: uri.path,
        method: 'GET',
        headers: {
            'Authorization': authToken,
            'Accept': '*/*'
        },
        responseType: 'json'
    };

    const indigoResponse = await webRequest(fullUri, requestOptions).json();
    return indigoResponse;
}

// export the smart home action / handler
exports.indigoassistant = functions.https.onRequest(smartHomeApp);