Clazz.declarePackage ("JS");
Clazz.load (["JU.SimpleUnitCell", "JU.P3", "JV.JC"], "JS.UnitCell", ["java.lang.Double", "$.Float", "java.util.Hashtable", "JU.Lst", "$.M3", "$.M4", "$.P4", "$.PT", "$.Quat", "$.T4", "$.V3", "J.api.Interface", "JS.Symmetry", "JU.BoxInfo", "$.Escape"], function () {
c$ = Clazz.decorateAsClass (function () {
this.vertices = null;
this.fractionalOffset = null;
this.allFractionalRelative = false;
this.cartesianOffset = null;
this.unitCellMultiplier = null;
this.unitCellMultiplied = null;
this.moreInfo = null;
this.name = "";
Clazz.instantialize (this, arguments);
}, JS, "UnitCell", JU.SimpleUnitCell, Cloneable);
Clazz.prepareFields (c$, function () {
this.cartesianOffset =  new JU.P3 ();
});
c$.fromOABC = Clazz.defineMethod (c$, "fromOABC", 
function (oabc, setRelative) {
var c =  new JS.UnitCell ();
if (oabc.length == 3) oabc =  Clazz.newArray (-1, [ new JU.P3 (), oabc[0], oabc[1], oabc[2]]);
var parameters =  Clazz.newFloatArray (-1, [-1, 0, 0, 0, 0, 0, oabc[1].x, oabc[1].y, oabc[1].z, oabc[2].x, oabc[2].y, oabc[2].z, oabc[3].x, oabc[3].y, oabc[3].z]);
c.init (parameters);
c.allFractionalRelative = setRelative;
c.initUnitcellVertices ();
c.setCartesianOffset (oabc[0]);
return c;
}, "~A,~B");
c$.fromParams = Clazz.defineMethod (c$, "fromParams", 
function (params, setRelative) {
var c =  new JS.UnitCell ();
c.init (params);
c.initUnitcellVertices ();
c.allFractionalRelative = setRelative;
return c;
}, "~A,~B");
Clazz.defineMethod (c$, "initOrientation", 
function (mat) {
if (mat == null) return;
var m =  new JU.M4 ();
m.setToM3 (mat);
this.matrixFractionalToCartesian.mul2 (m, this.matrixFractionalToCartesian);
this.matrixCartesianToFractional.setM4 (this.matrixFractionalToCartesian).invert ();
this.initUnitcellVertices ();
}, "JU.M3");
Clazz.defineMethod (c$, "toUnitCell", 
function (pt, offset) {
if (this.matrixCartesianToFractional == null) return;
if (offset == null) {
this.matrixCartesianToFractional.rotTrans (pt);
this.unitize (pt);
this.matrixFractionalToCartesian.rotTrans (pt);
} else {
this.matrixCtoFNoOffset.rotTrans (pt);
this.unitize (pt);
pt.add (offset);
this.matrixFtoCNoOffset.rotTrans (pt);
}}, "JU.T3,JU.T3");
Clazz.defineMethod (c$, "toUnitCellRnd", 
function (pt, offset) {
if (this.matrixCartesianToFractional == null) return;
if (offset == null) {
this.matrixCartesianToFractional.rotTrans (pt);
this.unitizeRnd (pt);
this.matrixFractionalToCartesian.rotTrans (pt);
} else {
this.matrixCtoFNoOffset.rotTrans (pt);
this.unitizeRnd (pt);
pt.add (offset);
this.matrixFtoCNoOffset.rotTrans (pt);
}}, "JU.T3,JU.T3");
Clazz.defineMethod (c$, "unitize", 
function (pt) {
JU.SimpleUnitCell.unitizeDim (this.dimension, pt);
}, "JU.T3");
Clazz.defineMethod (c$, "unitizeRnd", 
function (pt) {
JU.SimpleUnitCell.unitizeDimRnd (this.dimension, pt);
}, "JU.T3");
Clazz.defineMethod (c$, "reset", 
function () {
this.unitCellMultiplier = null;
this.unitCellMultiplied = null;
this.setOffset (JU.P3.new3 (0, 0, 0));
});
Clazz.defineMethod (c$, "setOffset", 
function (pt) {
if (pt == null) return;
this.unitCellMultiplied = null;
var pt4 = (Clazz.instanceOf (pt, JU.T4) ? pt : null);
var w = (pt4 == null ? 1.4E-45 : pt4.w);
var isCell555P4 = (w > 999999);
if (pt4 != null ? w <= 0 || isCell555P4 : pt.x >= 100 || pt.y >= 100) {
this.unitCellMultiplier = (pt.z == 0 && pt.x == pt.y && !isCell555P4 ? null : isCell555P4 ? JU.P4.newPt (pt4) : JU.P3.newP (pt));
this.unitCellMultiplied = null;
if (pt4 == null || pt4.w == 0 || isCell555P4) return;
}if (this.hasOffset () || pt.lengthSquared () > 0) {
this.fractionalOffset =  new JU.P3 ();
this.fractionalOffset.setT (pt);
}this.matrixCartesianToFractional.m03 = -pt.x;
this.matrixCartesianToFractional.m13 = -pt.y;
this.matrixCartesianToFractional.m23 = -pt.z;
this.cartesianOffset.setT (pt);
this.matrixFractionalToCartesian.m03 = 0;
this.matrixFractionalToCartesian.m13 = 0;
this.matrixFractionalToCartesian.m23 = 0;
this.matrixFractionalToCartesian.rotTrans (this.cartesianOffset);
this.matrixFractionalToCartesian.m03 = this.cartesianOffset.x;
this.matrixFractionalToCartesian.m13 = this.cartesianOffset.y;
this.matrixFractionalToCartesian.m23 = this.cartesianOffset.z;
if (this.allFractionalRelative) {
this.matrixCtoFNoOffset.setM4 (this.matrixCartesianToFractional);
this.matrixFtoCNoOffset.setM4 (this.matrixFractionalToCartesian);
}}, "JU.T3");
Clazz.defineMethod (c$, "setCartesianOffset", 
 function (origin) {
this.cartesianOffset.setT (origin);
this.matrixFractionalToCartesian.m03 = this.cartesianOffset.x;
this.matrixFractionalToCartesian.m13 = this.cartesianOffset.y;
this.matrixFractionalToCartesian.m23 = this.cartesianOffset.z;
var wasOffset = this.hasOffset ();
this.fractionalOffset =  new JU.P3 ();
this.fractionalOffset.setT (this.cartesianOffset);
this.matrixCartesianToFractional.m03 = 0;
this.matrixCartesianToFractional.m13 = 0;
this.matrixCartesianToFractional.m23 = 0;
this.matrixCartesianToFractional.rotTrans (this.fractionalOffset);
this.matrixCartesianToFractional.m03 = -this.fractionalOffset.x;
this.matrixCartesianToFractional.m13 = -this.fractionalOffset.y;
this.matrixCartesianToFractional.m23 = -this.fractionalOffset.z;
if (this.allFractionalRelative) {
this.matrixCtoFNoOffset.setM4 (this.matrixCartesianToFractional);
this.matrixFtoCNoOffset.setM4 (this.matrixFractionalToCartesian);
}if (!wasOffset && this.fractionalOffset.lengthSquared () == 0) this.fractionalOffset = null;
}, "JU.T3");
Clazz.defineMethod (c$, "getInfo", 
function () {
var m = this.getUnitCellMultiplied ();
if (m !== this) return m.getInfo ();
var info =  new java.util.Hashtable ();
info.put ("params", this.unitCellParams);
info.put ("oabc", this.getUnitCellVectors ());
info.put ("volume", Double.$valueOf (this.volume));
info.put ("matFtoC", this.matrixFractionalToCartesian);
info.put ("matCtoF", this.matrixCartesianToFractional);
return info;
});
Clazz.defineMethod (c$, "dumpInfo", 
function (isDebug, multiplied) {
var m = (multiplied ? this.getUnitCellMultiplied () : this);
if (m !== this) return m.dumpInfo (isDebug, false);
return "a=" + this.a + ", b=" + this.b + ", c=" + this.c + ", alpha=" + this.alpha + ", beta=" + this.beta + ", gamma=" + this.gamma + "\noabc=" + JU.Escape.eAP (this.getUnitCellVectors ()) + "\nvolume=" + this.volume + (isDebug ? "\nfractional to cartesian: " + this.matrixFractionalToCartesian + "\ncartesian to fractional: " + this.matrixCartesianToFractional : "");
}, "~B,~B");
Clazz.defineMethod (c$, "getUnitCellMultiplied", 
function () {
if (this.unitCellMultiplier == null || this.unitCellMultiplier.z > 0 && this.unitCellMultiplier.z == Clazz.floatToInt (this.unitCellMultiplier.z)) return this;
if (this.unitCellMultiplied == null) {
var pts = JU.BoxInfo.toOABC (this.getScaledCell (true), null);
this.unitCellMultiplied = JS.UnitCell.fromOABC (pts, false);
}return this.unitCellMultiplied;
});
Clazz.defineMethod (c$, "getVertices", 
function () {
return this.vertices;
});
Clazz.defineMethod (c$, "getCartesianOffset", 
function () {
return this.cartesianOffset;
});
Clazz.defineMethod (c$, "getFractionalOffset", 
function () {
return this.fractionalOffset;
});
Clazz.defineMethod (c$, "getTensor", 
function (vwr, parBorU) {
var t = (J.api.Interface.getUtil ("Tensor", vwr, "file"));
if (parBorU[0] == 0 && parBorU[1] == 0 && parBorU[2] == 0) {
var f = parBorU[7];
var eigenValues =  Clazz.newFloatArray (-1, [f, f, f]);
return t.setFromEigenVectors (JS.UnitCell.unitVectors, eigenValues, "iso", "Uiso=" + f, null);
}t.parBorU = parBorU;
var Bcart =  Clazz.newDoubleArray (6, 0);
var ortepType = Clazz.floatToInt (parBorU[6]);
if (ortepType == 12) {
Bcart[0] = parBorU[0] * 19.739208802178716;
Bcart[1] = parBorU[1] * 19.739208802178716;
Bcart[2] = parBorU[2] * 19.739208802178716;
Bcart[3] = parBorU[3] * 19.739208802178716 * 2;
Bcart[4] = parBorU[4] * 19.739208802178716 * 2;
Bcart[5] = parBorU[5] * 19.739208802178716 * 2;
parBorU[7] = (parBorU[0] + parBorU[1] + parBorU[3]) / 3;
} else {
var isFractional = (ortepType == 4 || ortepType == 5 || ortepType == 8 || ortepType == 9);
var cc = 2 - (ortepType % 2);
var dd = (ortepType == 8 || ortepType == 9 || ortepType == 10 ? 19.739208802178716 : ortepType == 4 || ortepType == 5 ? 0.25 : ortepType == 2 || ortepType == 3 ? Math.log (2) : 1);
var B11 = parBorU[0] * dd * (isFractional ? this.a_ * this.a_ : 1);
var B22 = parBorU[1] * dd * (isFractional ? this.b_ * this.b_ : 1);
var B33 = parBorU[2] * dd * (isFractional ? this.c_ * this.c_ : 1);
var B12 = parBorU[3] * dd * (isFractional ? this.a_ * this.b_ : 1) * cc;
var B13 = parBorU[4] * dd * (isFractional ? this.a_ * this.c_ : 1) * cc;
var B23 = parBorU[5] * dd * (isFractional ? this.b_ * this.c_ : 1) * cc;
parBorU[7] = Math.pow (B11 / 19.739208802178716 / this.a_ / this.a_ * B22 / 19.739208802178716 / this.b_ / this.b_ * B33 / 19.739208802178716 / this.c_ / this.c_, 0.3333);
Bcart[0] = this.a * this.a * B11 + this.b * this.b * this.cosGamma * this.cosGamma * B22 + this.c * this.c * this.cosBeta * this.cosBeta * B33 + this.a * this.b * this.cosGamma * B12 + this.b * this.c * this.cosGamma * this.cosBeta * B23 + this.a * this.c * this.cosBeta * B13;
Bcart[1] = this.b * this.b * this.sinGamma * this.sinGamma * B22 + this.c * this.c * this.cA_ * this.cA_ * B33 + this.b * this.c * this.cA_ * this.sinGamma * B23;
Bcart[2] = this.c * this.c * this.cB_ * this.cB_ * B33;
Bcart[3] = 2 * this.b * this.b * this.cosGamma * this.sinGamma * B22 + 2 * this.c * this.c * this.cA_ * this.cosBeta * B33 + this.a * this.b * this.sinGamma * B12 + this.b * this.c * (this.cA_ * this.cosGamma + this.sinGamma * this.cosBeta) * B23 + this.a * this.c * this.cA_ * B13;
Bcart[4] = 2 * this.c * this.c * this.cB_ * this.cosBeta * B33 + this.b * this.c * this.cosGamma * B23 + this.a * this.c * this.cB_ * B13;
Bcart[5] = 2 * this.c * this.c * this.cA_ * this.cB_ * B33 + this.b * this.c * this.cB_ * this.sinGamma * B23;
}return t.setFromThermalEquation (Bcart, JU.Escape.eAF (parBorU));
}, "JV.Viewer,~A");
Clazz.defineMethod (c$, "getCanonicalCopy", 
function (scale, withOffset) {
var pts = this.getScaledCell (withOffset);
return JU.BoxInfo.getCanonicalCopy (pts, scale);
}, "~N,~B");
Clazz.defineMethod (c$, "getScaledCell", 
function (withOffset) {
var pts =  new Array (8);
var cell0 = null;
var cell1 = null;
if (withOffset && this.unitCellMultiplier != null && this.unitCellMultiplier.z == 0) {
cell0 =  new JU.P3 ();
cell1 =  new JU.P3 ();
JU.SimpleUnitCell.ijkToPoint3f (Clazz.floatToInt (this.unitCellMultiplier.x), cell0, 0, 0);
JU.SimpleUnitCell.ijkToPoint3f (Clazz.floatToInt (this.unitCellMultiplier.y), cell1, 0, 0);
cell1.sub (cell0);
}var scale = (this.unitCellMultiplier == null || this.unitCellMultiplier.z == 0 ? 1 : Math.abs (this.unitCellMultiplier.z));
for (var i = 0; i < 8; i++) {
var pt = pts[i] = JU.P3.newP (JU.BoxInfo.unitCubePoints[i]);
if (cell0 != null) {
pts[i].add3 (cell0.x + cell1.x * pt.x, cell0.y + cell1.y * pt.y, cell0.z + cell1.z * pt.z);
}pts[i].scale (scale);
this.matrixFractionalToCartesian.rotTrans (pt);
if (!withOffset) pt.sub (this.cartesianOffset);
}
return pts;
}, "~B");
Clazz.defineMethod (c$, "initUnitcellVertices", 
 function () {
if (this.matrixFractionalToCartesian == null) return;
this.matrixCtoFNoOffset = JU.M4.newM4 (this.matrixCartesianToFractional);
this.matrixFtoCNoOffset = JU.M4.newM4 (this.matrixFractionalToCartesian);
this.vertices =  new Array (8);
for (var i = 8; --i >= 0; ) this.vertices[i] = this.matrixFractionalToCartesian.rotTrans2 (JU.BoxInfo.unitCubePoints[i],  new JU.P3 ());

});
Clazz.defineMethod (c$, "checkDistance", 
function (f1, f2, distance, dx, iRange, jRange, kRange, ptOffset) {
var p1 = JU.P3.newP (f1);
this.toCartesian (p1, true);
for (var i = -iRange; i <= iRange; i++) for (var j = -jRange; j <= jRange; j++) for (var k = -kRange; k <= kRange; k++) {
ptOffset.set (f2.x + i, f2.y + j, f2.z + k);
this.toCartesian (ptOffset, true);
var d = p1.distance (ptOffset);
if (dx > 0 ? Math.abs (d - distance) <= dx : d <= distance && d > 0.1) {
ptOffset.set (i, j, k);
return true;
}}


return false;
}, "JU.P3,JU.P3,~N,~N,~N,~N,~N,JU.P3");
Clazz.defineMethod (c$, "getUnitCellMultiplier", 
function () {
return this.unitCellMultiplier;
});
Clazz.defineMethod (c$, "getUnitCellVectors", 
function () {
var m = this.matrixFractionalToCartesian;
return  Clazz.newArray (-1, [JU.P3.newP (this.cartesianOffset), JU.P3.new3 (this.fix (m.m00), this.fix (m.m10), this.fix (m.m20)), JU.P3.new3 (this.fix (m.m01), this.fix (m.m11), this.fix (m.m21)), JU.P3.new3 (this.fix (m.m02), this.fix (m.m12), this.fix (m.m22))]);
});
Clazz.defineMethod (c$, "fix", 
 function (x) {
return (Math.abs (x) < 0.001 ? 0 : x);
}, "~N");
Clazz.defineMethod (c$, "isSameAs", 
function (uc) {
if (uc.unitCellParams.length != this.unitCellParams.length) return false;
for (var i = this.unitCellParams.length; --i >= 0; ) if (this.unitCellParams[i] != uc.unitCellParams[i] && !(Float.isNaN (this.unitCellParams[i]) && Float.isNaN (uc.unitCellParams[i]))) return false;

return (this.fractionalOffset == null ? !uc.hasOffset () : uc.fractionalOffset == null ? !this.hasOffset () : this.fractionalOffset.distanceSquared (uc.fractionalOffset) == 0);
}, "JS.UnitCell");
Clazz.defineMethod (c$, "hasOffset", 
function () {
return (this.fractionalOffset != null && this.fractionalOffset.lengthSquared () != 0);
});
Clazz.defineMethod (c$, "getQuaternionRotation", 
function (abc) {
var a = JU.V3.newVsub (this.vertices[4], this.vertices[0]);
var b = JU.V3.newVsub (this.vertices[2], this.vertices[0]);
var c = JU.V3.newVsub (this.vertices[1], this.vertices[0]);
var x =  new JU.V3 ();
var v =  new JU.V3 ();
var mul = (abc.charAt (0) == '-' ? -1 : 1);
if (mul < 0) abc = abc.substring (1);
var abc0 = abc;
abc = JU.PT.rep (JU.PT.rep (JU.PT.rep (JU.PT.rep (JU.PT.rep (JU.PT.rep (abc, "ab", "A"), "bc", "B"), "ca", "C"), "ba", "D"), "cb", "E"), "ac", "F");
var isFace = !abc0.equals (abc);
var quadrant = (isFace ? 1 : 0);
if (abc.length == 2) {
quadrant = abc.charCodeAt (1) - 48;
abc = abc.substring (0, 1);
}var isEven = (quadrant % 2 == 0);
var axis = "abcABCDEF".indexOf (abc);
var v1;
var v2;
var v3;
switch (axis) {
case 7:
mul = -mul;
case 4:
a.cross (c, b);
quadrant = ((5 - quadrant) % 4) + 1;
case 0:
default:
v1 = a;
v2 = c;
v3 = b;
break;
case 8:
mul = -mul;
case 5:
mul = -mul;
b.cross (c, a);
quadrant = ((2 + quadrant) % 4) + 1;
case 1:
v1 = b;
v2 = a;
v3 = c;
mul = -mul;
break;
case 3:
mul = -mul;
case 6:
c.cross (a, b);
if (isEven) quadrant = 6 - quadrant;
case 2:
v1 = c;
v2 = a;
v3 = b;
if (!isFace && quadrant > 0) {
quadrant = 5 - quadrant;
}break;
}
if (quadrant > 0) {
if (mul > 0 != isEven) {
v2 = v3;
v1.scale (-1);
}}switch (quadrant) {
case 0:
default:
case 1:
break;
case 2:
v1.scale (-1);
v2.scale (-1);
break;
case 3:
v2.scale (-1);
break;
case 4:
v1.scale (-1);
break;
}
x.cross (v1, v2);
v.cross (x, v1);
return JU.Quat.getQuaternionFrame (null, v, x).inv ();
}, "~S");
Clazz.defineMethod (c$, "getV0abc", 
function (def, retMatrix) {
if (Clazz.instanceOf (def, Array)) return def;
var m;
var isRev = false;
var pts =  new Array (4);
var pt = pts[0] = JU.V3.new3 (0, 0, 0);
pts[1] = JU.V3.new3 (1, 0, 0);
pts[2] = JU.V3.new3 (0, 1, 0);
pts[3] = JU.V3.new3 (0, 0, 1);
var m3 =  new JU.M3 ();
if (Clazz.instanceOf (def, String)) {
var sdef = def;
var strans = "0,0,0";
if (sdef.indexOf ("a=") == 0) return JU.SimpleUnitCell.setOabc (sdef, null, pts);
var ptc = sdef.indexOf (";");
if (ptc >= 0) {
strans = sdef.substring (ptc + 1);
sdef = sdef.substring (0, ptc);
}sdef += ";0,0,0";
isRev = sdef.startsWith ("!");
if (isRev) sdef = sdef.substring (1);
var symTemp =  new JS.Symmetry ();
symTemp.setSpaceGroup (false);
var i = symTemp.addSpaceGroupOperation ("=" + sdef, 0);
if (i < 0) return null;
m = symTemp.getSpaceGroupOperation (i);
(m).doFinalize ();
var atrans = JU.PT.split (strans, ",");
var ftrans =  Clazz.newFloatArray (3, 0);
if (atrans.length == 3) for (var j = 0; j < 3; j++) {
var s = atrans[j];
var sfpt = s.indexOf ("/");
if (sfpt >= 0) {
ftrans[j] = JU.PT.parseFloat (s.substring (0, sfpt)) / JU.PT.parseFloat (s.substring (sfpt + 1));
} else {
ftrans[j] = JU.PT.parseFloat (s);
}}
var ptrans = JU.P3.new3 (ftrans[0], ftrans[1], ftrans[2]);
m.setTranslation (ptrans);
if (retMatrix != null) {
retMatrix.setM4 (m);
}} else if (Clazz.instanceOf (def, JU.M3)) {
m = JU.M4.newMV (def,  new JU.P3 ());
} else if (Clazz.instanceOf (def, JU.M4)) {
m = def;
} else {
m = (def)[0];
m.getRotationScale (m3);
this.toCartesian (pt, false);
m.rotTrans (pt);
for (var i = 1; i < 4; i++) {
this.toCartesian (pts[i], true);
m3.rotate (pts[i]);
}
return pts;
}m.getRotationScale (m3);
m.getTranslation (pt);
if (isRev) {
m3.invert ();
m3.transpose ();
m3.rotate (pt);
pt.scale (-1);
} else {
m3.transpose ();
}this.toCartesian (pt, false);
for (var i = 1; i < 4; i++) {
m3.rotate (pts[i]);
this.toCartesian (pts[i], true);
}
return pts;
}, "~O,JU.M4");
Clazz.defineMethod (c$, "toFromPrimitive", 
function (toPrimitive, type, uc, primitiveToCrystal) {
var offset = uc.length - 3;
var mf = null;
if (type == 'r' || primitiveToCrystal == null) {
switch (type) {
default:
return false;
case 'r':
JU.SimpleUnitCell.getReciprocal (uc, uc, 1);
return true;
case 'P':
toPrimitive = true;
mf = JU.M3.newA9 ( Clazz.newFloatArray (-1, [1, 0, 0, 0, 1, 0, 0, 0, 1]));
break;
case 'A':
mf = JU.M3.newA9 ( Clazz.newFloatArray (-1, [1, 0, 0, 0, 0.5, 0.5, 0, -0.5, 0.5]));
break;
case 'B':
mf = JU.M3.newA9 ( Clazz.newFloatArray (-1, [0.5, 0, 0.5, 0, 1, 0, -0.5, 0, 0.5]));
break;
case 'C':
mf = JU.M3.newA9 ( Clazz.newFloatArray (-1, [0.5, 0.5, 0, -0.5, 0.5, 0, 0, 0, 1]));
break;
case 'R':
mf = JU.M3.newA9 ( Clazz.newFloatArray (-1, [0.6666667, -0.33333334, -0.33333334, 0.33333334, 0.33333334, -0.6666667, 0.33333334, 0.33333334, 0.33333334]));
break;
case 'I':
mf = JU.M3.newA9 ( Clazz.newFloatArray (-1, [-0.5, .5, .5, .5, -0.5, .5, .5, .5, -0.5]));
break;
case 'F':
mf = JU.M3.newA9 ( Clazz.newFloatArray (-1, [0, 0.5, 0.5, 0.5, 0, 0.5, 0.5, 0.5, 0]));
break;
}
if (!toPrimitive) mf.invert ();
} else {
mf = JU.M3.newM3 (primitiveToCrystal);
if (toPrimitive) mf.invert ();
}for (var i = uc.length; --i >= offset; ) {
var p = uc[i];
this.toFractional (p, false);
mf.rotate (p);
this.toCartesian (p, false);
}
return true;
}, "~B,~S,~A,JU.M3");
Clazz.defineMethod (c$, "getConventionalUnitCell", 
function (latticeType, primitiveToCrystal) {
var oabc = this.getUnitCellVectors ();
if (!latticeType.equals ("P") || primitiveToCrystal != null) this.toFromPrimitive (false, latticeType.charAt (0), oabc, primitiveToCrystal);
return oabc;
}, "~S,JU.M3");
c$.cloneUnitCell = Clazz.defineMethod (c$, "cloneUnitCell", 
function (uc) {
var ucnew = null;
try {
ucnew = uc.clone ();
} catch (e) {
if (Clazz.exceptionOf (e, CloneNotSupportedException)) {
} else {
throw e;
}
}
return ucnew;
}, "JS.UnitCell");
Clazz.defineMethod (c$, "getEquivPoints", 
function (pt, flags, ops, list, i0, n0) {
var fromfractional = (flags.indexOf ("fromfractional") >= 0);
var tofractional = (flags.indexOf ("tofractional") >= 0);
var packed = (flags.indexOf ("packed") >= 0);
if (list == null) list =  new JU.Lst ();
var pf = JU.P3.newP (pt);
if (!fromfractional) this.toFractional (pf, true);
var n = list.size ();
for (var i = 0, nops = ops.length; i < nops; i++) {
var p = JU.P3.newP (pf);
ops[i].rotTrans (p);
p.x = (p.x - Math.floor (p.x));
p.y = (p.y - Math.floor (p.y));
p.z = (p.z - Math.floor (p.z));
list.addLast (p);
n++;
}
if (packed) {
for (var i = n0; i < n; i++) {
pf.setT (list.get (i));
this.unitizeRnd (pf);
if (pf.x == 0) {
list.addLast (JU.P3.new3 (0, pf.y, pf.z));
list.addLast (JU.P3.new3 (1, pf.y, pf.z));
if (pf.y == 0) {
list.addLast (JU.P3.new3 (1, 1, pf.z));
list.addLast (JU.P3.new3 (0, 0, pf.z));
if (pf.z == 0) {
list.addLast (JU.P3.new3 (1, 1, 1));
list.addLast (JU.P3.new3 (0, 0, 0));
}}}if (pf.y == 0) {
list.addLast (JU.P3.new3 (pf.x, 0, pf.z));
list.addLast (JU.P3.new3 (pf.x, 1, pf.z));
if (pf.z == 0) {
list.addLast (JU.P3.new3 (pf.x, 0, 0));
list.addLast (JU.P3.new3 (pf.x, 1, 1));
}}if (pf.z == 0) {
list.addLast (JU.P3.new3 (pf.x, pf.y, 0));
list.addLast (JU.P3.new3 (pf.x, pf.y, 1));
if (pf.x == 0) {
list.addLast (JU.P3.new3 (0, pf.y, 0));
list.addLast (JU.P3.new3 (1, pf.y, 1));
}}}
}JS.UnitCell.checkDuplicate (list, i0, n0, -1);
if (!tofractional) {
for (var i = list.size (); --i >= n0; ) this.toCartesian (list.get (i), true);

}return list;
}, "JU.P3,~S,~A,JU.Lst,~N,~N");
c$.checkDuplicate = Clazz.defineMethod (c$, "checkDuplicate", 
 function (list, i0, n0, n) {
if (n < 0) n = list.size ();
for (var i = i0; i < n; i++) {
var p = list.get (i);
for (var j = Math.max (i + 1, n0); j < n; j++) {
if (list.get (j).distanceSquared (p) < 1.96E-6) {
list.removeItemAt (j);
n--;
j--;
}}
}
}, "JU.Lst,~N,~N,~N");
Clazz.defineMethod (c$, "normalize", 
function (vtrans) {
vtrans.x = JU.SimpleUnitCell.normalizeXRnd (vtrans.x);
vtrans.y = JU.SimpleUnitCell.normalizeXRnd (vtrans.y);
vtrans.z = JU.SimpleUnitCell.normalizeXRnd (vtrans.z);
}, "JU.V3");
Clazz.defineMethod (c$, "getState", 
function () {
var s = "";
if (this.fractionalOffset != null && this.fractionalOffset.lengthSquared () != 0) s += "  unitcell offset " + JU.Escape.eP (this.fractionalOffset) + ";\n";
if (this.unitCellMultiplier != null) s += "  unitcell range " + JU.SimpleUnitCell.escapeMultiplier (this.unitCellMultiplier) + ";\n";
return s;
});
Clazz.defineStatics (c$,
"twoP2", 19.739208802178716);
c$.unitVectors = c$.prototype.unitVectors =  Clazz.newArray (-1, [JV.JC.axisX, JV.JC.axisY, JV.JC.axisZ]);
});
