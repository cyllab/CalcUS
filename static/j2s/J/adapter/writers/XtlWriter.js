Clazz.declarePackage ("J.adapter.writers");
Clazz.load (null, "J.adapter.writers.XtlWriter", ["JU.PT"], function () {
c$ = Clazz.decorateAsClass (function () {
this.haveUnitCell = true;
Clazz.instantialize (this, arguments);
}, J.adapter.writers, "XtlWriter");
Clazz.defineMethod (c$, "clean", 
function (f) {
var t;
return (!this.haveUnitCell || (t = J.adapter.writers.XtlWriter.twelfthsOf (f)) < 0 ? JU.PT.formatF (f, 18, 12, false, false) : (f < 0 ? "   -" : "    ") + J.adapter.writers.XtlWriter.twelfths[t]);
}, "~N");
c$.twelfthsOf = Clazz.defineMethod (c$, "twelfthsOf", 
 function (f) {
if (f == 0) return 0;
f = Math.abs (f * 12);
var i = Math.round (f);
return (i <= 12 && Math.abs (f - i) < 0.0018 ? i : -1);
}, "~N");
c$.twelfths = c$.prototype.twelfths =  Clazz.newArray (-1, ["0.000000000000", "0.083333333333", "0.166666666667", "0.250000000000", "0.333333333333", "0.416666666667", "0.500000000000", "0.583333333333", "0.666666666667", "0.750000000000", "0.833333333333", "0.916666666667", "1.000000000000"]);
});
