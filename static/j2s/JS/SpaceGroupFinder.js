Clazz.declarePackage ("JS");
Clazz.load (["JU.P3"], "JS.SpaceGroupFinder", ["JU.BS", "$.Lst", "$.PT", "JS.SpaceGroup", "$.SymmetryOperation", "JU.BSUtil", "$.SimpleUnitCell", "JV.FileManager"], function () {
c$ = Clazz.decorateAsClass (function () {
this.atoms = null;
this.nAtoms = 0;
this.pt = null;
if (!Clazz.isClassDefined ("JS.SpaceGroupFinder.SGAtom")) {
JS.SpaceGroupFinder.$SpaceGroupFinder$SGAtom$ ();
}
Clazz.instantialize (this, arguments);
}, JS, "SpaceGroupFinder");
Clazz.prepareFields (c$, function () {
this.pt =  new JU.P3 ();
});
Clazz.makeConstructor (c$, 
function () {
});
Clazz.defineMethod (c$, "findSpaceGroup", 
function (vwr, atoms0, xyzList, unitCellParams, uc, asString, isAssign) {
var oabc = null;
var cartesians = vwr.ms.at;
var isg = 0;
var bsGroups =  new JU.BS ();
var bsOps =  new JU.BS ();
var bsAtoms = null;
var bsPoints0 =  new JU.BS ();
if (xyzList == null || isAssign) {
bsAtoms = JU.BSUtil.copy (atoms0);
this.nAtoms = bsAtoms.cardinality ();
}var targets = JU.BS.newN (this.nAtoms);
var n = 0;
var nChecked = 0;
var scaling = JU.P3.new3 (1, 1, 1);
var sg = null;
try {
if (JS.SpaceGroupFinder.bsOpGroups == null) JS.SpaceGroupFinder.loadData (vwr, this);
if (xyzList != null) {
var ret = this.getGroupsWithOps (xyzList, unitCellParams, isAssign);
if (!isAssign) return ret;
sg = ret;
uc.setUnitCell (unitCellParams, false);
}oabc = uc.getUnitCellVectors ();
uc = uc.getUnitCellMultiplied ();
this.filterGroups (bsGroups, uc.getUnitCellParams ());
this.atoms =  new Array (bsAtoms.cardinality ());
System.out.println ("bsAtoms = " + bsAtoms);
for (var p = 0, i = bsAtoms.nextSetBit (0); i >= 0; i = bsAtoms.nextSetBit (i + 1), p++) {
var a = cartesians[i];
var type = a.getAtomicAndIsotopeNumber ();
(this.atoms[p] = Clazz.innerTypeInstance (JS.SpaceGroupFinder.SGAtom, this, null, type, i, a.getAtomName (), a.getOccupancy100 ())).setT (this.toFractional (a, uc));
}
var bsPoints = JU.BSUtil.newBitSet2 (0, this.nAtoms);
var uc0 = uc;
this.nAtoms = bsPoints.cardinality ();
uc0 = uc;
var isSupercell = false;
if (this.nAtoms > 0) {
for (var i = bsPoints.nextSetBit (0); i >= 0; i = bsPoints.nextSetBit (i + 1)) {
JU.SimpleUnitCell.unitizeDim (3, this.atoms[i]);
}
this.removeDuplicates (bsPoints);
uc = this.checkSupercell (vwr, uc, bsPoints, 1, scaling);
uc = this.checkSupercell (vwr, uc, bsPoints, 2, scaling);
uc = this.checkSupercell (vwr, uc, bsPoints, 3, scaling);
isSupercell = (uc !== uc0);
if (isSupercell) {
if (scaling.x != 1) System.out.println ("supercell found; a scaled by 1/" + scaling.x);
if (scaling.y != 1) System.out.println ("supercell found; b scaled by 1/" + scaling.y);
if (scaling.z != 1) System.out.println ("supercell found; c scaled by 1/" + scaling.z);
}}n = bsPoints.cardinality ();
bsAtoms =  new JU.BS ();
var newAtoms =  new Array (n);
for (var p = 0, i = bsPoints.nextSetBit (0); i >= 0; i = bsPoints.nextSetBit (i + 1)) {
var a = this.atoms[i];
newAtoms[p++] = a;
if (isSupercell) {
a.setT (this.toFractional (cartesians[a.index], uc));
JU.SimpleUnitCell.unitizeDim (3, a);
}bsAtoms.set (this.atoms[i].index);
}
this.atoms = newAtoms;
this.nAtoms = n;
System.out.println ("bsAtoms(within cell) = " + bsAtoms);
bsPoints.clearAll ();
bsPoints.setBits (0, this.nAtoms);
bsPoints0 = JU.BS.copy (bsPoints);
var temp1 = JU.BS.newN (JS.SpaceGroupFinder.OP_COUNT);
var targeted = JU.BS.newN (this.nAtoms);
bsOps.setBits (1, sg == null ? JS.SpaceGroupFinder.OP_COUNT : sg.getOperationCount ());
if (this.nAtoms == 0) {
bsGroups.clearBits (1, JS.SpaceGroupFinder.GROUP_COUNT);
bsOps.clearAll ();
}var uncheckedOps = JU.BS.newN (JS.SpaceGroupFinder.OP_COUNT);
var opsChecked = JU.BS.newN (JS.SpaceGroupFinder.OP_COUNT);
opsChecked.set (0);
var hasC1 = false;
for (var iop = bsOps.nextSetBit (1); iop > 0 && !bsGroups.isEmpty (); iop = bsOps.nextSetBit (iop + 1)) {
var op = (sg == null ? JS.SpaceGroupFinder.getOp (iop) : sg.getOperation (iop));
if (sg == null) {
System.out.println ("\nChecking operation " + iop + " " + JS.SpaceGroupFinder.opXYZ[iop]);
System.out.println ("bsGroups = " + bsGroups);
System.out.println ("bsOps = " + bsOps);
nChecked++;
}var isOK = true;
bsPoints.clearAll ();
bsPoints.or (bsPoints0);
targeted.clearAll ();
for (var i = bsPoints.nextSetBit (0); i >= 0; i = bsPoints.nextSetBit (i + 1)) {
bsPoints.clear (i);
var j = this.findEquiv (iop, op, i, bsPoints, this.pt, true);
if (j < 0 && sg == null) {
System.out.println ("failed op " + iop + " for atom " + i + " " + this.atoms[i].name + " " + this.atoms[i] + " looking for " + this.pt + "\n" + op);
isOK = false;
break;
}if (j >= 0 && i != j) {
targeted.set (j);
}}
if (sg == null) {
var myGroups = JS.SpaceGroupFinder.bsOpGroups[iop];
bsOps.clear (iop);
opsChecked.set (iop);
if (isOK) {
System.out.println ("OK!");
if (iop == 1) hasC1 = true;
targets.or (targeted);
bsGroups.and (myGroups);
temp1.setBits (1, JS.SpaceGroupFinder.OP_COUNT);
for (var i = bsGroups.nextSetBit (0); i >= 0; i = bsGroups.nextSetBit (i + 1)) {
temp1.and (JS.SpaceGroupFinder.bsGroupOps[i]);
}
uncheckedOps.or (temp1);
bsOps.andNot (temp1);
} else {
bsGroups.andNot (myGroups);
temp1.clearAll ();
for (var i = bsGroups.nextSetBit (0); i >= 0; i = bsGroups.nextSetBit (i + 1)) {
temp1.or (JS.SpaceGroupFinder.bsGroupOps[i]);
}
bsOps.and (temp1);
}} else {
targets.or (targeted);
}}
if (sg == null) {
n = bsGroups.cardinality ();
if (n == 0) {
bsGroups.set (hasC1 ? 1 : 0);
n = 1;
if (hasC1 && !asString) {
uncheckedOps.clearAll ();
uncheckedOps.set (1);
opsChecked.clearAll ();
targets.clearAll ();
bsPoints.or (bsPoints0);
}}isg = bsGroups.nextSetBit (0);
if (n == 1) {
if (isg > 0) {
opsChecked.and (JS.SpaceGroupFinder.bsGroupOps[isg]);
uncheckedOps.and (JS.SpaceGroupFinder.bsGroupOps[isg]);
uncheckedOps.andNot (opsChecked);
uncheckedOps.or (JS.SpaceGroupFinder.bsGroupOps[isg]);
uncheckedOps.clear (0);
bsPoints.or (bsPoints0);
bsPoints.andNot (targets);
if (!this.checkBasis (uncheckedOps, bsPoints, targets)) {
isg = 0;
}}if (isg == 0) targets.clearAll ();
}}} catch (e) {
if (Clazz.exceptionOf (e, Exception)) {
e.printStackTrace ();
bsGroups.clearAll ();
} else {
throw e;
}
}
if (sg == null) {
System.out.println ("checked " + nChecked + " operations; now " + n + " " + bsGroups + " " + bsOps);
for (var i = bsGroups.nextSetBit (0); i >= 0; i = bsGroups.nextSetBit (i + 1)) {
System.out.println (JS.SpaceGroup.nameToGroup.get (JS.SpaceGroupFinder.groupNames[i]));
}
if (n != 1) return null;
sg = JS.SpaceGroup.nameToGroup.get (JS.SpaceGroupFinder.groupNames[isg]);
}var name = sg.asString ();
var basis = JU.BSUtil.copy (bsAtoms);
for (var i = targets.nextSetBit (0); i >= 0; i = targets.nextSetBit (i + 1)) basis.clear (this.atoms[i].index);

var nb = basis.cardinality ();
var msg = name + "\nbasis is " + nb + " atom" + (nb == 1 ? "" : "s") + ": " + basis;
System.out.println (msg);
if (asString) return msg;
var map = sg.dumpInfoObj ();
System.out.println ("unitcell is " + uc.getUnitCellInfo (true));
var bs1 = JU.BS.copy (bsPoints0);
bs1.andNot (targets);
if (!isAssign) this.dumpBasis (JS.SpaceGroupFinder.bsGroupOps[isg], bs1, bsPoints0);
map.put ("name", name);
map.put ("basis", basis);
map.put ("supercell", scaling);
oabc[1].scale (scaling.x);
oabc[2].scale (scaling.y);
oabc[3].scale (scaling.z);
map.put ("unitcell", oabc);
if (isAssign) map.put ("sg", sg);
return map;
}, "JV.Viewer,JU.BS,~S,~A,J.api.SymmetryInterface,~B,~B");
Clazz.defineMethod (c$, "removeDuplicates", 
 function (bs) {
for (var i = bs.nextSetBit (0); i >= 0; i = bs.nextSetBit (i + 1)) {
var a = this.atoms[i];
for (var j = bs.nextSetBit (0); j < i; j = bs.nextSetBit (j + 1)) {
var b = this.atoms[j];
if (a.typeAndOcc == b.typeAndOcc && a.distanceSquared (b) < 1.96E-6) {
bs.clear (i);
break;
}}
}
}, "JU.BS");
Clazz.defineMethod (c$, "dumpBasis", 
 function (ops, bs1, bsPoints) {
}, "JU.BS,JU.BS,JU.BS");
Clazz.defineMethod (c$, "checkBasis", 
 function (uncheckedOps, bsPoints, targets) {
var n = uncheckedOps.cardinality ();
if (n == 0) return true;
var bs =  new JU.BS ();
bs.or (bsPoints);
System.out.println ("finishing check for basis for " + n + " operations");
for (var iop = uncheckedOps.nextSetBit (0); iop >= 0; iop = uncheckedOps.nextSetBit (iop + 1)) {
bs.or (bsPoints);
var op = JS.SpaceGroupFinder.getOp (iop);
for (var i = bs.nextSetBit (0); i >= 0; i = bs.nextSetBit (i + 1)) {
var j = this.findEquiv (-1, op, i, bs, this.pt, false);
if (j < 0) return false;
if (i != j) {
j = Math.max (i, j);
targets.set (j);
bs.clear (j);
}}
}
return true;
}, "JU.BS,JU.BS,JU.BS");
Clazz.defineMethod (c$, "filterGroups", 
 function (bsGroups, params) {
var isOrtho = false;
var isTet = false;
var isTri = false;
var isRhombo = false;
var isCubic = false;
var absame = this.approx0 (params[0] - params[1]);
var bcsame = this.approx0 (params[1] - params[2]);
if (params[3] == 90) {
if (params[4] == 90) {
if (absame && params[0] != params[1]) System.out.println ("OHOH");
isTri = (absame && this.approx000 (params[5] - 120));
if (params[5] == 90) {
isCubic = (absame && params[1] == params[2]);
isTet = (!isCubic && absame);
isOrtho = (!isCubic && !isTet);
}}} else if (absame && bcsame && params[3] == params[4] && params[4] == params[5]) {
isRhombo = true;
}bsGroups.setBits (0, 2);
var i0 = 2;
var i = 2;
while (true) {
i = JS.SpaceGroupFinder.scanTo (i, "16");
if (!isOrtho && !isTet && !isTri && !isRhombo && !isCubic) break;
i = JS.SpaceGroupFinder.scanTo (i, "75");
if (!isTet && !isTri && !isRhombo && !isCubic) break;
i = JS.SpaceGroupFinder.scanTo (i, "143");
if (!isTri && !isRhombo && !isCubic) break;
i0 = i;
for (; ; i++) {
var g = JS.SpaceGroupFinder.groupNames[i];
if (g.indexOf (":r") >= 0) {
if (!isRhombo) continue;
bsGroups.set (i);
}if (g.startsWith ("195")) {
if (isRhombo) return;
break;
}}
if (!isCubic) break;
bsGroups.setBits (2, i0);
i0 = i;
i = JS.SpaceGroupFinder.GROUP_COUNT;
break;
}
bsGroups.setBits (i0, i);
}, "JU.BS,~A");
c$.scanTo = Clazz.defineMethod (c$, "scanTo", 
 function (i, num) {
for (; ; i++) {
if (JS.SpaceGroupFinder.groupNames[i].startsWith (num)) break;
}
return i;
}, "~N,~S");
Clazz.defineMethod (c$, "getGroupsWithOps", 
 function (xyzList, unitCellParams, isAssign) {
var groups =  new JU.BS ();
if (unitCellParams == null) {
groups.setBits (0, JS.SpaceGroupFinder.GROUP_COUNT);
} else {
this.filterGroups (groups, unitCellParams);
}var sg = null;
if (xyzList.indexOf ("x") < 0) {
sg = JS.SpaceGroup.determineSpaceGroupNA (xyzList, unitCellParams);
if (sg == null) return null;
sg.checkHallOperators ();
for (var i = 0; i < JS.SpaceGroupFinder.GROUP_COUNT; i++) if (JS.SpaceGroupFinder.groupNames[i].equals (sg.intlTableNumberFull)) return (groups.get (i) ? sg : null);

return null;
}var isEqual = xyzList.indexOf ("&") < 0 || isAssign;
var ops = JU.PT.split (JU.PT.trim (xyzList.trim ().$replace ('&', ';'), ";="), ";");
for (var j = ops.length; --j >= 0; ) {
var xyz = ops[j];
if (xyz == null || xyz.indexOf ("z") < xyz.lastIndexOf (",")) return "?" + ops[j] + "?";
xyz = JS.SymmetryOperation.getJmolCanonicalXYZ (xyz);
for (var i = JS.SpaceGroupFinder.opXYZ.length; --i >= 0; ) {
if (JS.SpaceGroupFinder.opXYZ[i].equals (xyz)) {
groups.and (JS.SpaceGroupFinder.bsOpGroups[i]);
break;
}if (i == 0) groups.clearAll ();
}
}
if (groups.isEmpty ()) {
return (isAssign ? JS.SpaceGroup.createSpaceGroupN (xyzList) : null);
}if (isEqual) {
for (var n = ops.length, i = groups.nextSetBit (0); i >= 0; i = groups.nextSetBit (i + 1)) {
if (JS.SpaceGroupFinder.bsGroupOps[i].cardinality () == n) {
if (isAssign) {
return JS.SpaceGroup.createSpaceGroupN (JS.SpaceGroupFinder.groupNames[i]);
}return JS.SpaceGroup.getInfo (null, JS.SpaceGroupFinder.groupNames[i], unitCellParams, true, false);
}}
return null;
}var ret =  new Array (groups.cardinality ());
for (var p = 0, i = groups.nextSetBit (0); i >= 0; i = groups.nextSetBit (i + 1)) {
ret[p++] = JS.SpaceGroupFinder.groupNames[i];
}
return ret;
}, "~S,~A,~B");
Clazz.defineMethod (c$, "toFractional", 
function (a, uc) {
this.pt.setT (a);
uc.toFractional (this.pt, false);
return this.pt;
}, "JM.Atom,J.api.SymmetryInterface");
c$.getOp = Clazz.defineMethod (c$, "getOp", 
 function (iop) {
var op = JS.SpaceGroupFinder.ops[iop];
if (op == null) {
JS.SpaceGroupFinder.ops[iop] = op =  new JS.SymmetryOperation (null, iop, false);
op.setMatrixFromXYZ (JS.SpaceGroupFinder.opXYZ[iop], 0, false);
op.doFinalize ();
}return op;
}, "~N");
Clazz.defineMethod (c$, "checkSupercell", 
function (vwr, uc, bsPoints, abc, scaling) {
if (bsPoints.isEmpty ()) return uc;
var minF = 2147483647;
var maxF = -2147483648;
var counts =  Clazz.newIntArray (101, 0);
for (var i = bsPoints.nextSetBit (0); i >= 0; i = bsPoints.nextSetBit (i + 1)) {
var a = this.atoms[i];
var type = a.typeAndOcc;
var b;
var f;
for (var j = bsPoints.nextSetBit (0); j >= 0; j = bsPoints.nextSetBit (j + 1)) {
if (j == i || (b = this.atoms[j]).typeAndOcc != type) continue;
this.pt.sub2 (b, a);
switch (abc) {
case 1:
if (this.approx0 (f = this.pt.x) || !this.approx0 (this.pt.y) || !this.approx0 (this.pt.z)) continue;
break;
case 2:
if (this.approx0 (f = this.pt.y) || !this.approx0 (this.pt.x) || !this.approx0 (this.pt.z)) continue;
break;
default:
case 3:
if (this.approx0 (f = this.pt.z) || !this.approx0 (this.pt.x) || !this.approx0 (this.pt.y)) continue;
break;
}
var n = this.approxInt (1 / f);
if (n == 0 || Clazz.doubleToInt (this.nAtoms / n) != 1 * this.nAtoms / n || n > 100) continue;
if (n > maxF) maxF = n;
if (n < minF) minF = n;
counts[n]++;
}
}
var n = maxF;
while (n >= minF) {
if (counts[n] > 0 && counts[n] == Clazz.doubleToInt ((n - 1) * this.nAtoms / n)) {
break;
}--n;
}
if (n < minF) return uc;
var oabc = uc.getUnitCellVectors ();
oabc[abc].scale (1 / n);
switch (abc) {
case 1:
scaling.x = n;
break;
case 2:
scaling.y = n;
break;
case 3:
scaling.z = n;
break;
}
uc = vwr.getSymTemp ().getUnitCell (oabc, false, "scaled");
var f = 0;
for (var i = bsPoints.nextSetBit (0); i >= 0; i = bsPoints.nextSetBit (i + 1)) {
switch (abc) {
case 1:
f = this.approxInt (n * this.atoms[i].x);
break;
case 2:
f = this.approxInt (n * this.atoms[i].y);
break;
case 3:
f = this.approxInt (n * this.atoms[i].z);
break;
}
if (f != 0) {
this.atoms[i] = null;
bsPoints.clear (i);
}}
this.nAtoms = bsPoints.cardinality ();
return uc;
}, "JV.Viewer,J.api.SymmetryInterface,JU.BS,~N,JU.P3");
Clazz.defineMethod (c$, "approx0", 
 function (f) {
return (Math.abs (f) < 0.001);
}, "~N");
Clazz.defineMethod (c$, "approx000", 
 function (f) {
return (Math.abs (f) < 1.0E-4);
}, "~N");
Clazz.defineMethod (c$, "approx0014", 
 function (f) {
return (Math.abs (f) < JS.SpaceGroupFinder.SLOP0014);
}, "~N");
Clazz.defineMethod (c$, "approxInt", 
 function (finv) {
var i = Clazz.floatToInt (finv + 0.001);
return (Math.abs (finv - i) < 0.001 ? i : 0);
}, "~N");
Clazz.defineMethod (c$, "findEquiv", 
 function (iop, op, i, bsPoints, pt, andClear) {
var a = this.atoms[i];
pt.setT (a);
op.rotTrans (pt);
JU.SimpleUnitCell.unitizeDim (3, pt);
if (pt.distanceSquared (a) == 0) {
return i;
}var testiop = -99;
var type = a.typeAndOcc;
var name = a.name;
for (var j = this.nAtoms; --j >= 0; ) {
var b = this.atoms[j];
if (b.typeAndOcc != type) continue;
var d = b.distance (pt);
if (d * d < 1.96E-6 || (1 - d) * (1 - d) < 1.96E-6 && this.latticeShift (pt, b)) {
if (andClear) {
j = Math.max (i, j);
if (i != j) bsPoints.clear (j);
}return j;
}}
return -1;
}, "~N,JS.SymmetryOperation,~N,JU.BS,JU.P3,~B");
Clazz.defineMethod (c$, "latticeShift", 
 function (a, b) {
var is1 = (this.approx0014 (Math.abs (a.x - b.x) - 1) || this.approx0014 (Math.abs (a.y - b.y) - 1) || this.approx0014 (Math.abs (a.z - b.z) - 1));
if (is1) {
}return is1;
}, "JU.P3,JU.P3");
c$.main = Clazz.defineMethod (c$, "main", 
function (args) {
if (JS.SpaceGroupFinder.loadData (null,  new JS.SpaceGroupFinder ())) System.out.println ("OK");
}, "~A");
c$.loadData = Clazz.defineMethod (c$, "loadData", 
 function (vwr, me) {
try {
JS.SpaceGroupFinder.groupNames = JS.SpaceGroupFinder.getList (vwr, me, null, "sggroups_ordered.txt");
JS.SpaceGroupFinder.GROUP_COUNT = JS.SpaceGroupFinder.groupNames.length;
JS.SpaceGroupFinder.opXYZ = JS.SpaceGroupFinder.getList (vwr, me, null, "sgops_ordered.txt");
JS.SpaceGroupFinder.OP_COUNT = JS.SpaceGroupFinder.opXYZ.length;
var map = JS.SpaceGroupFinder.getList (vwr, me,  new Array (JS.SpaceGroupFinder.OP_COUNT), "sgmap.txt");
JS.SpaceGroupFinder.bsGroupOps =  new Array (JS.SpaceGroupFinder.GROUP_COUNT);
JS.SpaceGroupFinder.bsOpGroups =  new Array (JS.SpaceGroupFinder.OP_COUNT);
for (var j = 0; j < JS.SpaceGroupFinder.GROUP_COUNT; j++) JS.SpaceGroupFinder.bsGroupOps[j] = JU.BS.newN (JS.SpaceGroupFinder.OP_COUNT);

for (var i = 0; i < JS.SpaceGroupFinder.OP_COUNT; i++) {
var m = map[i];
JS.SpaceGroupFinder.bsOpGroups[i] = JU.BS.newN (JS.SpaceGroupFinder.GROUP_COUNT);
for (var j = 0; j < JS.SpaceGroupFinder.GROUP_COUNT; j++) {
if (m.charAt (j) == '1') {
JS.SpaceGroupFinder.bsGroupOps[j].set (i);
JS.SpaceGroupFinder.bsOpGroups[i].set (j);
}}
}
JS.SpaceGroupFinder.ops =  new Array (JS.SpaceGroupFinder.OP_COUNT);
return true;
} catch (e) {
if (Clazz.exceptionOf (e, Exception)) {
e.printStackTrace ();
return false;
} else {
throw e;
}
} finally {
if (JS.SpaceGroupFinder.rdr != null) try {
JS.SpaceGroupFinder.rdr.close ();
} catch (e) {
if (Clazz.exceptionOf (e, java.io.IOException)) {
} else {
throw e;
}
}
}
}, "JV.Viewer,~O");
c$.getList = Clazz.defineMethod (c$, "getList", 
 function (vwr, me, list, fileName) {
JS.SpaceGroupFinder.rdr = JV.FileManager.getBufferedReaderForResource (vwr, me, "JS/", "sg/" + fileName);
if (list == null) {
var l =  new JU.Lst ();
var line;
while ((line = JS.SpaceGroupFinder.rdr.readLine ()) != null) {
if (line.length > 0) {
l.addLast (line);
}}
l.toArray (list =  new Array (l.size ()));
} else {
for (var i = 0; i < list.length; i++) list[i] = JS.SpaceGroupFinder.rdr.readLine ();

}JS.SpaceGroupFinder.rdr.close ();
return list;
}, "JV.Viewer,~O,~A,~S");
c$.$SpaceGroupFinder$SGAtom$ = function () {
Clazz.pu$h(self.c$);
c$ = Clazz.decorateAsClass (function () {
Clazz.prepareCallback (this, arguments);
this.typeAndOcc = 0;
this.index = 0;
this.name = null;
Clazz.instantialize (this, arguments);
}, JS.SpaceGroupFinder, "SGAtom", JU.P3);
Clazz.makeConstructor (c$, 
function (a, b, c, d) {
Clazz.superConstructor (this, JS.SpaceGroupFinder.SGAtom, []);
this.typeAndOcc = a + 1000 * d;
this.index = b;
this.name = c;
}, "~N,~N,~S,~N");
c$ = Clazz.p0p ();
};
Clazz.defineStatics (c$,
"MAX_COUNT", 100);
c$.SLOP0014 = c$.prototype.SLOP0014 = Math.sqrt (1.96E-6);
Clazz.defineStatics (c$,
"SLOP001", 0.001,
"SLOP0001", 0.0001,
"GROUP_COUNT", 0,
"OP_COUNT", 0,
"bsOpGroups", null,
"bsGroupOps", null,
"groupNames", null,
"opXYZ", null,
"ops", null,
"rdr", null);
});
