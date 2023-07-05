Clazz.declarePackage ("JSV.app");
Clazz.load (["JSV.api.ScriptInterface", "JSV.app.JSVApp", "J.api.JSVInterface"], "JSV.app.JSVAppPro", null, function () {
c$ = Clazz.declareType (JSV.app, "JSVAppPro", JSV.app.JSVApp, [J.api.JSVInterface, JSV.api.ScriptInterface]);
Clazz.overrideMethod (c$, "isSigned", 
function () {
return true;
});
Clazz.overrideMethod (c$, "isPro", 
function () {
return true;
});
Clazz.overrideMethod (c$, "exitJSpecView", 
function (withDialog, frame) {
this.appletFrame.doExitJmol ();
}, "~B,~O");
Clazz.overrideMethod (c$, "siProcessCommand", 
function (script) {
this.appletFrame.getApp ().runScriptNow (script);
}, "~S");
Clazz.overrideMethod (c$, "saveProperties", 
function (properties) {
}, "java.util.Properties");
Clazz.overrideMethod (c$, "setProperties", 
function (properties) {
}, "java.util.Properties");
});
