Clazz.declarePackage ("JS");
Clazz.load (["J.api.SymmetryInterface"], "JS.Symmetry", ["JU.BS", "$.Lst", "$.P3", "$.PT", "J.api.Interface", "J.bspt.Bspt", "JS.PointGroup", "$.SpaceGroup", "$.SymmetryInfo", "$.SymmetryOperation", "$.UnitCell", "JU.Escape", "$.Logger", "$.SimpleUnitCell"], function () {
c$ = Clazz.decorateAsClass (function () {
this.spaceGroup = null;
this.pointGroup = null;
this.symmetryInfo = null;
this.unitCell = null;
this.cip = null;
this.$isBio = false;
this.desc = null;
Clazz.instantialize (this, arguments);
}, JS, "Symmetry", null, J.api.SymmetryInterface);
Clazz.overrideMethod (c$, "isBio", 
function () {
return this.$isBio;
});
Clazz.makeConstructor (c$, 
function () {
});
Clazz.overrideMethod (c$, "setPointGroup", 
function (siLast, center, atomset, bsAtoms, haveVibration, distanceTolerance, linearTolerance, maxAtoms, localEnvOnly) {
this.pointGroup = JS.PointGroup.getPointGroup (siLast == null ? null : (siLast).pointGroup, center, atomset, bsAtoms, haveVibration, distanceTolerance, linearTolerance, maxAtoms, localEnvOnly);
return this;
}, "J.api.SymmetryInterface,JU.T3,~A,JU.BS,~B,~N,~N,~N,~B");
Clazz.overrideMethod (c$, "getPointGroupName", 
function () {
return this.pointGroup.getName ();
});
Clazz.overrideMethod (c$, "getPointGroupInfo", 
function (modelIndex, drawID, asInfo, type, index, scale) {
if (drawID == null && !asInfo && this.pointGroup.textInfo != null) return this.pointGroup.textInfo;
 else if (drawID == null && this.pointGroup.isDrawType (type, index, scale)) return this.pointGroup.drawInfo;
 else if (asInfo && this.pointGroup.info != null) return this.pointGroup.info;
return this.pointGroup.getInfo (modelIndex, drawID, asInfo, type, index, scale);
}, "~N,~S,~B,~S,~N,~N");
Clazz.overrideMethod (c$, "setSpaceGroup", 
function (doNormalize) {
if (this.spaceGroup == null) this.spaceGroup = JS.SpaceGroup.getNull (true, doNormalize, false);
}, "~B");
Clazz.overrideMethod (c$, "addSpaceGroupOperation", 
function (xyz, opId) {
return this.spaceGroup.addSymmetry (xyz, opId, false);
}, "~S,~N");
Clazz.overrideMethod (c$, "addBioMoleculeOperation", 
function (mat, isReverse) {
this.$isBio = this.spaceGroup.isBio = true;
return this.spaceGroup.addSymmetry ((isReverse ? "!" : "") + "[[bio" + mat, 0, false);
}, "JU.M4,~B");
Clazz.overrideMethod (c$, "setLattice", 
function (latt) {
this.spaceGroup.setLatticeParam (latt);
}, "~N");
Clazz.overrideMethod (c$, "getSpaceGroup", 
function () {
return this.spaceGroup;
});
Clazz.overrideMethod (c$, "createSpaceGroup", 
function (desiredSpaceGroupIndex, name, data, modDim) {
this.spaceGroup = JS.SpaceGroup.createSpaceGroup (desiredSpaceGroupIndex, name, data, modDim);
if (this.spaceGroup != null && JU.Logger.debugging) JU.Logger.debug ("using generated space group " + this.spaceGroup.dumpInfo ());
return this.spaceGroup != null;
}, "~N,~S,~O,~N");
Clazz.overrideMethod (c$, "getSpaceGroupInfoObj", 
function (name, params, isFull, addNonstandard) {
return JS.SpaceGroup.getInfo (this.spaceGroup, name, params, isFull, addNonstandard);
}, "~S,~A,~B,~B");
Clazz.overrideMethod (c$, "getLatticeDesignation", 
function () {
return this.spaceGroup.getLatticeDesignation ();
});
Clazz.overrideMethod (c$, "setFinalOperations", 
function (dim, name, atoms, iAtomFirst, noSymmetryCount, doNormalize, filterSymop) {
if (name != null && (name.startsWith ("bio") || name.indexOf (" *(") >= 0)) this.spaceGroup.name = name;
if (filterSymop != null) {
var lst =  new JU.Lst ();
lst.addLast (this.spaceGroup.operations[0]);
for (var i = 1; i < this.spaceGroup.operationCount; i++) if (filterSymop.contains (" " + (i + 1) + " ")) lst.addLast (this.spaceGroup.operations[i]);

this.spaceGroup = JS.SpaceGroup.createSpaceGroup (-1, name + " *(" + filterSymop.trim () + ")", lst, -1);
}this.spaceGroup.setFinalOperationsForAtoms (dim, atoms, iAtomFirst, noSymmetryCount, doNormalize);
}, "~N,~S,~A,~N,~N,~B,~S");
Clazz.overrideMethod (c$, "getSpaceGroupOperation", 
function (i) {
return (this.spaceGroup == null || this.spaceGroup.operations == null || i >= this.spaceGroup.operations.length ? null : this.spaceGroup.finalOperations == null ? this.spaceGroup.operations[i] : this.spaceGroup.finalOperations[i]);
}, "~N");
Clazz.overrideMethod (c$, "getSpaceGroupXyz", 
function (i, doNormalize) {
return this.spaceGroup.getXyz (i, doNormalize);
}, "~N,~B");
Clazz.overrideMethod (c$, "newSpaceGroupPoint", 
function (pt, i, o, transX, transY, transZ, retPoint) {
if (o == null && this.spaceGroup.finalOperations == null) {
var op = this.spaceGroup.operations[i];
if (!op.isFinalized) op.doFinalize ();
o = op;
}JS.Symmetry.newPoint ((o == null ? this.spaceGroup.finalOperations[i] : o), pt, transX, transY, transZ, retPoint);
}, "JU.P3,~N,JU.M4,~N,~N,~N,JU.P3");
Clazz.overrideMethod (c$, "rotateAxes", 
function (iop, axes, ptTemp, mTemp) {
return (iop == 0 ? axes : this.spaceGroup.finalOperations[iop].rotateAxes (axes, this.unitCell, ptTemp, mTemp));
}, "~N,~A,JU.P3,JU.M3");
Clazz.overrideMethod (c$, "getSpaceGroupOperationCode", 
function (iOp) {
return this.spaceGroup.operations[iOp].subsystemCode;
}, "~N");
Clazz.overrideMethod (c$, "setTimeReversal", 
function (op, val) {
this.spaceGroup.operations[op].setTimeReversal (val);
}, "~N,~N");
Clazz.overrideMethod (c$, "getSpinOp", 
function (op) {
return this.spaceGroup.operations[op].getMagneticOp ();
}, "~N");
Clazz.overrideMethod (c$, "addLatticeVectors", 
function (lattvecs) {
return this.spaceGroup.addLatticeVectors (lattvecs);
}, "JU.Lst");
Clazz.overrideMethod (c$, "getLatticeOp", 
function () {
return this.spaceGroup.latticeOp;
});
Clazz.overrideMethod (c$, "getLatticeCentering", 
function () {
return JS.SymmetryOperation.getLatticeCentering (this.getSymmetryOperations ());
});
Clazz.overrideMethod (c$, "getOperationRsVs", 
function (iop) {
return (this.spaceGroup.finalOperations == null ? this.spaceGroup.operations : this.spaceGroup.finalOperations)[iop].rsvs;
}, "~N");
Clazz.overrideMethod (c$, "getSiteMultiplicity", 
function (pt) {
return this.spaceGroup.getSiteMultiplicity (pt, this.unitCell);
}, "JU.P3");
Clazz.overrideMethod (c$, "addSubSystemOp", 
function (code, rs, vs, sigma) {
this.spaceGroup.isSSG = true;
var s = JS.SymmetryOperation.getXYZFromRsVs (rs, vs, false);
var i = this.spaceGroup.addSymmetry (s, -1, true);
this.spaceGroup.operations[i].setSigma (code, sigma);
return s;
}, "~S,JU.Matrix,JU.Matrix,JU.Matrix");
Clazz.overrideMethod (c$, "getMatrixFromString", 
function (xyz, rotTransMatrix, allowScaling, modDim) {
return JS.SymmetryOperation.getMatrixFromString (null, xyz, rotTransMatrix, allowScaling);
}, "~S,~A,~B,~N");
Clazz.overrideMethod (c$, "getSpaceGroupName", 
function () {
return (this.symmetryInfo != null ? this.symmetryInfo.sgName : this.spaceGroup != null ? this.spaceGroup.getName () : this.unitCell != null && this.unitCell.name.length > 0 ? "cell=" + this.unitCell.name : "");
});
Clazz.overrideMethod (c$, "getSpaceGroupNameType", 
function (type) {
return (this.spaceGroup == null ? null : this.spaceGroup.getNameType (type, this));
}, "~S");
Clazz.overrideMethod (c$, "setSpaceGroupName", 
function (name) {
if (this.spaceGroup != null) this.spaceGroup.setName (name);
}, "~S");
Clazz.overrideMethod (c$, "getSpaceGroupOperationCount", 
function () {
return (this.symmetryInfo != null && this.symmetryInfo.symmetryOperations != null ? this.symmetryInfo.symmetryOperations.length : this.spaceGroup != null && this.spaceGroup.finalOperations != null ? this.spaceGroup.finalOperations.length : 0);
});
Clazz.overrideMethod (c$, "getLatticeType", 
function () {
return (this.symmetryInfo != null ? this.symmetryInfo.latticeType : this.spaceGroup == null ? 'P' : this.spaceGroup.latticeType);
});
Clazz.overrideMethod (c$, "getIntTableNumber", 
function () {
return (this.symmetryInfo != null ? this.symmetryInfo.intlTableNo : this.spaceGroup == null ? null : this.spaceGroup.intlTableNumber);
});
Clazz.overrideMethod (c$, "getCoordinatesAreFractional", 
function () {
return this.symmetryInfo == null || this.symmetryInfo.coordinatesAreFractional;
});
Clazz.overrideMethod (c$, "getCellRange", 
function () {
return this.symmetryInfo == null ? null : this.symmetryInfo.cellRange;
});
Clazz.overrideMethod (c$, "getSymmetryInfoStr", 
function () {
if (this.symmetryInfo != null) return this.symmetryInfo.infoStr;
if (this.spaceGroup == null) return "";
this.symmetryInfo =  new JS.SymmetryInfo ();
this.symmetryInfo.setSymmetryInfo (null, this.getUnitCellParams (), this.spaceGroup);
return this.symmetryInfo.infoStr;
});
Clazz.overrideMethod (c$, "getSymmetryOperations", 
function () {
if (this.symmetryInfo != null) return this.symmetryInfo.symmetryOperations;
if (this.spaceGroup == null) this.spaceGroup = JS.SpaceGroup.getNull (true, false, true);
this.spaceGroup.setFinalOperations ();
return this.spaceGroup.finalOperations;
});
Clazz.overrideMethod (c$, "isSimple", 
function () {
return (this.spaceGroup == null && (this.symmetryInfo == null || this.symmetryInfo.symmetryOperations == null));
});
Clazz.overrideMethod (c$, "setSymmetryInfo", 
function (modelIndex, modelAuxiliaryInfo, unitCellParams) {
this.symmetryInfo =  new JS.SymmetryInfo ();
var params = this.symmetryInfo.setSymmetryInfo (modelAuxiliaryInfo, unitCellParams, null);
if (params != null) {
this.setUnitCell (params, modelAuxiliaryInfo.containsKey ("jmolData"));
this.unitCell.moreInfo = modelAuxiliaryInfo.get ("moreUnitCellInfo");
modelAuxiliaryInfo.put ("infoUnitCell", this.getUnitCellAsArray (false));
this.setOffsetPt (modelAuxiliaryInfo.get ("unitCellOffset"));
var matUnitCellOrientation = modelAuxiliaryInfo.get ("matUnitCellOrientation");
if (matUnitCellOrientation != null) this.initializeOrientation (matUnitCellOrientation);
if (JU.Logger.debugging) JU.Logger.debug ("symmetryInfos[" + modelIndex + "]:\n" + this.unitCell.dumpInfo (true, true));
}return this;
}, "~N,java.util.Map,~A");
Clazz.overrideMethod (c$, "haveUnitCell", 
function () {
return (this.unitCell != null);
});
Clazz.defineMethod (c$, "setUnitCell", 
function (unitCellParams, setRelative) {
this.unitCell = JS.UnitCell.fromParams (unitCellParams, setRelative);
return this;
}, "~A,~B");
Clazz.overrideMethod (c$, "unitCellEquals", 
function (uc2) {
return ((uc2)).unitCell.isSameAs (this.unitCell);
}, "J.api.SymmetryInterface");
Clazz.overrideMethod (c$, "getUnitCellState", 
function () {
if (this.unitCell == null) return "";
return this.unitCell.getState ();
});
Clazz.overrideMethod (c$, "getMoreInfo", 
function () {
return this.unitCell.moreInfo;
});
Clazz.defineMethod (c$, "getUnitsymmetryInfo", 
function () {
return this.unitCell.dumpInfo (false, true);
});
Clazz.overrideMethod (c$, "initializeOrientation", 
function (mat) {
this.unitCell.initOrientation (mat);
}, "JU.M3");
Clazz.overrideMethod (c$, "unitize", 
function (ptFrac) {
this.unitCell.unitize (ptFrac);
}, "JU.T3");
Clazz.overrideMethod (c$, "toUnitCell", 
function (pt, offset) {
this.unitCell.toUnitCell (pt, offset);
}, "JU.T3,JU.T3");
Clazz.overrideMethod (c$, "toUnitCellRnd", 
function (pt, offset) {
this.unitCell.toUnitCellRnd (pt, offset);
}, "JU.T3,JU.T3");
Clazz.overrideMethod (c$, "toSupercell", 
function (fpt) {
return this.unitCell.toSupercell (fpt);
}, "JU.P3");
Clazz.overrideMethod (c$, "toFractional", 
function (pt, ignoreOffset) {
if (!this.$isBio) this.unitCell.toFractional (pt, ignoreOffset);
}, "JU.T3,~B");
Clazz.overrideMethod (c$, "toFractionalM", 
function (m) {
if (!this.$isBio) this.unitCell.toFractionalM (m);
}, "JU.M4");
Clazz.overrideMethod (c$, "toCartesian", 
function (fpt, ignoreOffset) {
if (!this.$isBio) this.unitCell.toCartesian (fpt, ignoreOffset);
}, "JU.T3,~B");
Clazz.overrideMethod (c$, "getUnitCellParams", 
function () {
return this.unitCell.getUnitCellParams ();
});
Clazz.overrideMethod (c$, "getUnitCellAsArray", 
function (vectorsOnly) {
return this.unitCell.getUnitCellAsArray (vectorsOnly);
}, "~B");
Clazz.overrideMethod (c$, "getTensor", 
function (vwr, parBorU) {
if (parBorU == null) return null;
if (this.unitCell == null) this.unitCell = JS.UnitCell.fromParams ( Clazz.newFloatArray (-1, [1, 1, 1, 90, 90, 90]), true);
return this.unitCell.getTensor (vwr, parBorU);
}, "JV.Viewer,~A");
Clazz.overrideMethod (c$, "getUnitCellVerticesNoOffset", 
function () {
return this.unitCell.getVertices ();
});
Clazz.overrideMethod (c$, "getCartesianOffset", 
function () {
return this.unitCell.getCartesianOffset ();
});
Clazz.overrideMethod (c$, "getFractionalOffset", 
function () {
return this.unitCell.getFractionalOffset ();
});
Clazz.overrideMethod (c$, "setOffsetPt", 
function (pt) {
this.unitCell.setOffset (pt);
}, "JU.T3");
Clazz.overrideMethod (c$, "setOffset", 
function (nnn) {
var pt =  new JU.P3 ();
JU.SimpleUnitCell.ijkToPoint3f (nnn, pt, 0, 0);
this.unitCell.setOffset (pt);
}, "~N");
Clazz.overrideMethod (c$, "getUnitCellMultiplier", 
function () {
return this.unitCell.getUnitCellMultiplier ();
});
Clazz.overrideMethod (c$, "getUnitCellMultiplied", 
function () {
var uc = this.unitCell.getUnitCellMultiplied ();
if (uc === this.unitCell) return this;
var s =  new JS.Symmetry ();
s.unitCell = uc;
return s;
});
Clazz.overrideMethod (c$, "getCanonicalCopy", 
function (scale, withOffset) {
return this.unitCell.getCanonicalCopy (scale, withOffset);
}, "~N,~B");
Clazz.overrideMethod (c$, "getUnitCellInfoType", 
function (infoType) {
return this.unitCell.getInfo (infoType);
}, "~N");
Clazz.overrideMethod (c$, "getUnitCellInfo", 
function (scaled) {
return this.unitCell.dumpInfo (false, scaled);
}, "~B");
Clazz.overrideMethod (c$, "isSlab", 
function () {
return this.unitCell.isSlab ();
});
Clazz.overrideMethod (c$, "isPolymer", 
function () {
return this.unitCell.isPolymer ();
});
Clazz.overrideMethod (c$, "checkDistance", 
function (f1, f2, distance, dx, iRange, jRange, kRange, ptOffset) {
return this.unitCell.checkDistance (f1, f2, distance, dx, iRange, jRange, kRange, ptOffset);
}, "JU.P3,JU.P3,~N,~N,~N,~N,~N,JU.P3");
Clazz.defineMethod (c$, "getUnitCellVectors", 
function () {
return this.unitCell.getUnitCellVectors ();
});
Clazz.overrideMethod (c$, "getUnitCell", 
function (oabc, setRelative, name) {
if (oabc == null) return null;
this.unitCell = JS.UnitCell.fromOABC (oabc, setRelative);
if (name != null) this.unitCell.name = name;
return this;
}, "~A,~B,~S");
Clazz.overrideMethod (c$, "isSupercell", 
function () {
return this.unitCell.isSupercell ();
});
Clazz.overrideMethod (c$, "notInCentroid", 
function (modelSet, bsAtoms, minmax) {
try {
var bsDelete =  new JU.BS ();
var iAtom0 = bsAtoms.nextSetBit (0);
var molecules = modelSet.getMolecules ();
var moleculeCount = molecules.length;
var atoms = modelSet.at;
var isOneMolecule = (molecules[moleculeCount - 1].firstAtomIndex == modelSet.am[atoms[iAtom0].mi].firstAtomIndex);
var center =  new JU.P3 ();
var centroidPacked = (minmax[6] == 1);
nextMol : for (var i = moleculeCount; --i >= 0 && bsAtoms.get (molecules[i].firstAtomIndex); ) {
var bs = molecules[i].atomList;
center.set (0, 0, 0);
var n = 0;
for (var j = bs.nextSetBit (0); j >= 0; j = bs.nextSetBit (j + 1)) {
if (isOneMolecule || centroidPacked) {
center.setT (atoms[j]);
if (this.isNotCentroid (center, 1, minmax, centroidPacked)) {
if (isOneMolecule) bsDelete.set (j);
} else if (!isOneMolecule) {
continue nextMol;
}} else {
center.add (atoms[j]);
n++;
}}
if (centroidPacked || n > 0 && this.isNotCentroid (center, n, minmax, false)) bsDelete.or (bs);
}
return bsDelete;
} catch (e) {
if (Clazz.exceptionOf (e, Exception)) {
return null;
} else {
throw e;
}
}
}, "JM.ModelSet,JU.BS,~A");
Clazz.defineMethod (c$, "isNotCentroid", 
 function (center, n, minmax, centroidPacked) {
center.scale (1 / n);
this.toFractional (center, false);
if (centroidPacked) return (center.x + 0.000005 <= minmax[0] || center.x - 0.000005 > minmax[3] || center.y + 0.000005 <= minmax[1] || center.y - 0.000005 > minmax[4] || center.z + 0.000005 <= minmax[2] || center.z - 0.000005 > minmax[5]);
return (center.x + 0.000005 <= minmax[0] || center.x + 0.00005 > minmax[3] || center.y + 0.000005 <= minmax[1] || center.y + 0.00005 > minmax[4] || center.z + 0.000005 <= minmax[2] || center.z + 0.00005 > minmax[5]);
}, "JU.P3,~N,~A,~B");
Clazz.defineMethod (c$, "getDesc", 
 function (modelSet) {
if (modelSet == null) {
return (JS.Symmetry.nullDesc == null ? (JS.Symmetry.nullDesc = (J.api.Interface.getInterface ("JS.SymmetryDesc", null, "modelkit"))) : JS.Symmetry.nullDesc);
}return (this.desc == null ? (this.desc = (J.api.Interface.getInterface ("JS.SymmetryDesc", modelSet.vwr, "eval"))) : this.desc).set (modelSet);
}, "JM.ModelSet");
Clazz.overrideMethod (c$, "getSymmetryInfoAtom", 
function (modelSet, iatom, xyz, op, translation, pt, pt2, id, type, scaleFactor, nth, options, opList) {
return this.getDesc (modelSet).getSymopInfo (iatom, xyz, op, translation, pt, pt2, id, type, scaleFactor, nth, options, opList);
}, "JM.ModelSet,~N,~S,~N,JU.P3,JU.P3,JU.P3,~S,~N,~N,~N,~N,~A");
Clazz.overrideMethod (c$, "getSpaceGroupInfo", 
function (modelSet, sgName, modelIndex, isFull, cellParams) {
var isForModel = (sgName == null);
if (sgName == null) {
var info = modelSet.getModelAuxiliaryInfo (modelSet.vwr.am.cmi);
if (info != null) sgName = info.get ("spaceGroup");
}var cellInfo = null;
if (cellParams != null) {
cellInfo =  new JS.Symmetry ().setUnitCell (cellParams, false);
}return this.getDesc (modelSet).getSpaceGroupInfo (this, modelIndex, sgName, 0, null, null, null, 0, -1, isFull, isForModel, 0, cellInfo, null);
}, "JM.ModelSet,~S,~N,~B,~A");
Clazz.overrideMethod (c$, "fcoord", 
function (p) {
return JS.SymmetryOperation.fcoord (p);
}, "JU.T3");
Clazz.overrideMethod (c$, "getV0abc", 
function (def, retMatrix) {
return (this.unitCell == null ? null : this.unitCell.getV0abc (def, retMatrix));
}, "~O,JU.M4");
Clazz.overrideMethod (c$, "getQuaternionRotation", 
function (abc) {
return (this.unitCell == null ? null : this.unitCell.getQuaternionRotation (abc));
}, "~S");
Clazz.overrideMethod (c$, "getFractionalOrigin", 
function () {
return this.unitCell.getFractionalOrigin ();
});
Clazz.overrideMethod (c$, "getState", 
function (ms, modelIndex, commands) {
var pt = this.getFractionalOffset ();
var loadUC = false;
if (pt != null && (pt.x != 0 || pt.y != 0 || pt.z != 0)) {
commands.append ("; set unitcell ").append (JU.Escape.eP (pt));
loadUC = true;
}pt = this.getUnitCellMultiplier ();
if (pt != null) {
commands.append ("; set unitcell ").append (JU.SimpleUnitCell.escapeMultiplier (pt));
loadUC = true;
}var isAssigned = (ms.getInfo (modelIndex, "spaceGroupAssigned") != null);
var sg = ms.getInfo (modelIndex, "spaceGroup");
if (isAssigned && sg != null) {
commands.append ("\n UNITCELL " + JU.Escape.e (ms.getUnitCell (modelIndex).getUnitCellVectors ()));
commands.append ("\n MODELKIT SPACEGROUP " + JU.PT.esc (sg));
loadUC = true;
}return loadUC;
}, "JM.ModelSet,~N,JU.SB");
Clazz.overrideMethod (c$, "getIterator", 
function (vwr, atom, bsAtoms, radius) {
return (J.api.Interface.getInterface ("JS.UnitCellIterator", vwr, "script")).set (this, atom, vwr.ms.at, bsAtoms, radius);
}, "JV.Viewer,JM.Atom,JU.BS,~N");
Clazz.overrideMethod (c$, "toFromPrimitive", 
function (toPrimitive, type, oabc, primitiveToCrystal) {
if (this.unitCell == null) this.unitCell = JS.UnitCell.fromOABC (oabc, false);
return this.unitCell.toFromPrimitive (toPrimitive, type, oabc, primitiveToCrystal);
}, "~B,~S,~A,JU.M3");
Clazz.overrideMethod (c$, "generateCrystalClass", 
function (pt0) {
var ops = this.getSymmetryOperations ();
var lst =  new JU.Lst ();
var isRandom = (pt0 == null);
var rand1 = 0;
var rand2 = 0;
var rand3 = 0;
if (isRandom) {
rand1 = 2.718281828459045;
rand2 = 3.141592653589793;
rand3 = Math.log10 (2000);
pt0 = JU.P3.new3 (rand1 + 1, rand2 + 2, rand3 + 3);
} else {
pt0 = JU.P3.newP (pt0);
}if (ops == null || this.unitCell == null) {
lst.addLast (pt0);
} else {
this.unitCell.toFractional (pt0, true);
var pt1 = null;
var pt2 = null;
var pt3 = null;
if (isRandom) {
pt1 = JU.P3.new3 (rand2 + 4, rand3 + 5, rand1 + 6);
this.unitCell.toFractional (pt1, true);
pt2 = JU.P3.new3 (rand3 + 7, rand1 + 8, rand2 + 9);
this.unitCell.toFractional (pt2, true);
}var bspt =  new J.bspt.Bspt (3, 0);
var iter = bspt.allocateCubeIterator ();
var pt =  new JU.P3 ();
out : for (var i = ops.length; --i >= 0; ) {
ops[i].rotate2 (pt0, pt);
iter.initialize (pt, 0.001, false);
if (iter.hasMoreElements ()) continue out;
var ptNew = JU.P3.newP (pt);
lst.addLast (ptNew);
bspt.addTuple (ptNew);
if (isRandom) {
if (pt2 != null) {
pt3 =  new JU.P3 ();
ops[i].rotate2 (pt2, pt3);
lst.addLast (pt3);
}if (pt1 != null) {
pt3 =  new JU.P3 ();
ops[i].rotate2 (pt1, pt3);
lst.addLast (pt3);
}}}
for (var j = lst.size (); --j >= 0; ) this.unitCell.toCartesian (lst.get (j), true);

}return lst;
}, "JU.P3");
Clazz.overrideMethod (c$, "calculateCIPChiralityForAtoms", 
function (vwr, bsAtoms) {
vwr.setCursor (3);
var cip = this.getCIPChirality (vwr);
var dataClass = (vwr.getBoolean (603979960) ? "CIPData" : "CIPDataTracker");
var data = (J.api.Interface.getInterface ("JS." + dataClass, vwr, "script")).set (vwr, bsAtoms);
data.setRule6Full (vwr.getBoolean (603979823));
cip.getChiralityForAtoms (data);
vwr.setCursor (0);
}, "JV.Viewer,JU.BS");
Clazz.overrideMethod (c$, "calculateCIPChiralityForSmiles", 
function (vwr, smiles) {
vwr.setCursor (3);
var cip = this.getCIPChirality (vwr);
var data = (J.api.Interface.getInterface ("JS.CIPDataSmiles", vwr, "script")).setAtomsForSmiles (vwr, smiles);
cip.getChiralityForAtoms (data);
vwr.setCursor (0);
return data.getSmilesChiralityArray ();
}, "JV.Viewer,~S");
Clazz.defineMethod (c$, "getCIPChirality", 
 function (vwr) {
return (this.cip == null ? (this.cip = (J.api.Interface.getInterface ("JS.CIPChirality", vwr, "script"))) : this.cip);
}, "JV.Viewer");
Clazz.overrideMethod (c$, "getConventionalUnitCell", 
function (latticeType, primitiveToCrystal) {
return (this.unitCell == null || latticeType == null ? null : this.unitCell.getConventionalUnitCell (latticeType, primitiveToCrystal));
}, "~S,JU.M3");
Clazz.overrideMethod (c$, "getUnitCellInfoMap", 
function () {
return (this.unitCell == null ? null : this.unitCell.getInfo ());
});
Clazz.defineMethod (c$, "setUnitCell", 
function (uc) {
this.unitCell = JS.UnitCell.cloneUnitCell ((uc).unitCell);
}, "J.api.SymmetryInterface");
Clazz.overrideMethod (c$, "findSpaceGroup", 
function (vwr, atoms, xyzList, unitCell, asString, isAssign) {
return (J.api.Interface.getInterface ("JS.SpaceGroupFinder", vwr, "eval")).findSpaceGroup (vwr, atoms, xyzList, unitCell, this, asString, isAssign);
}, "JV.Viewer,JU.BS,~S,~A,~B,~B");
Clazz.overrideMethod (c$, "setSpaceGroupTo", 
function (sg) {
this.symmetryInfo = null;
if (Clazz.instanceOf (sg, JS.SpaceGroup)) {
this.spaceGroup = sg;
} else {
this.spaceGroup = JS.SpaceGroup.getSpaceGroupFromITAName (sg.toString ());
}}, "~O");
Clazz.overrideMethod (c$, "removeDuplicates", 
function (ms, bs, highPrec) {
var uc = this.unitCell;
var atoms = ms.at;
var occs = ms.occupancies;
var haveOccupancies = (occs != null);
var unitized =  new Array (bs.length ());
for (var i = bs.nextSetBit (0); i >= 0; i = bs.nextSetBit (i + 1)) {
var pt = unitized[i] = JU.P3.newP (atoms[i]);
uc.toFractional (pt, false);
if (highPrec) uc.unitizeRnd (pt);
 else uc.unitize (pt);
}
for (var i = bs.nextSetBit (0); i >= 0; i = bs.nextSetBit (i + 1)) {
var a = atoms[i];
var pt = unitized[i];
var type = a.getAtomicAndIsotopeNumber ();
var occ = (haveOccupancies ? occs[i] : 0);
for (var j = bs.nextSetBit (i + 1); j >= 0; j = bs.nextSetBit (j + 1)) {
var b = atoms[j];
if (type != b.getAtomicAndIsotopeNumber () || (haveOccupancies && occ != occs[j])) continue;
var pt2 = unitized[j];
if (pt.distanceSquared (pt2) < 1.96E-6) {
bs.clear (j);
}}
}
return bs;
}, "JM.ModelSet,JU.BS,~B");
Clazz.overrideMethod (c$, "getEquivPoints", 
function (pts, pt, flags) {
var ops = this.getSymmetryOperations ();
return (ops == null || this.unitCell == null ? null : this.unitCell.getEquivPoints (pt, flags, ops, pts == null ?  new JU.Lst () : pts, 0, 0));
}, "JU.Lst,JU.P3,~S");
Clazz.overrideMethod (c$, "getEquivPointList", 
function (pts, nIgnored, flags) {
var ops = this.getSymmetryOperations ();
var newPt = (flags.indexOf ("newpt") >= 0);
var zapped = (flags.indexOf ("zapped") >= 0);
var n = pts.size ();
var tofractional = (flags.indexOf ("tofractional") >= 0);
if (flags.indexOf ("fromfractional") < 0) {
for (var i = 0; i < pts.size (); i++) {
this.toFractional (pts.get (i), true);
}
}flags += ",fromfractional,tofractional";
var check0 = (nIgnored > 0 ? 0 : n);
var allPoints = (nIgnored == n);
var n0 = (nIgnored > 0 ? nIgnored : n);
if (allPoints) {
nIgnored--;
n0--;
}if (zapped) n0 = 0;
var p0 = (nIgnored > 0 ? pts.get (nIgnored) : null);
if (ops != null || this.unitCell != null) {
for (var i = nIgnored; i < n; i++) {
this.unitCell.getEquivPoints (pts.get (i), flags, ops, pts, check0, n0);
}
}if (!zapped && (pts.size () == nIgnored || pts.get (nIgnored) !== p0 || allPoints || newPt)) n--;
for (var i = n - nIgnored; --i >= 0; ) pts.removeItemAt (nIgnored);

if (!tofractional) {
for (var i = pts.size (); --i >= nIgnored; ) this.toCartesian (pts.get (i), true);

}}, "JU.Lst,~N,~S");
Clazz.overrideMethod (c$, "getInvariantSymops", 
function (pt, v0) {
var ops = this.getSymmetryOperations ();
if (ops == null) return  Clazz.newIntArray (0, 0);
var bs =  new JU.BS ();
var p =  new JU.P3 ();
var p0 =  new JU.P3 ();
var nops = ops.length;
for (var i = 1; i < nops; i++) {
p.setT (pt);
this.toFractional (p, true);
this.unitCell.unitize (p);
p0.setT (p);
ops[i].rotTrans (p);
this.unitCell.unitize (p);
if (p0.distanceSquared (p) < 1.96E-6) {
System.out.println ("Symm found " + i + " " + p0 + " " + p);
bs.set (i);
}}
var ret =  Clazz.newIntArray (bs.cardinality (), 0);
if (v0 != null && ret.length != v0.length) return null;
for (var k = 0, i = 1; i < nops; i++) {
var isOK = bs.get (i);
if (isOK) {
if (v0 != null && v0[k] != i + 1) return null;
ret[k++] = i + 1;
}}
return ret;
}, "JU.P3,~A");
Clazz.overrideMethod (c$, "getTransform", 
function (fracA, fracB, best) {
return this.getDesc (null).getTransform (this.unitCell, this.getSymmetryOperations (), fracA, fracB, best);
}, "JU.P3,JU.P3,~B");
c$.newPoint = Clazz.defineMethod (c$, "newPoint", 
function (m, atom1, x, y, z, atom2) {
m.rotTrans2 (atom1, atom2);
atom2.add3 (x, y, z);
}, "JU.M4,JU.P3,~N,~N,~N,JU.P3");
Clazz.overrideMethod (c$, "isWithinUnitCell", 
function (pt, a, b, c) {
return this.unitCell.isWithinUnitCell (a, b, c, pt);
}, "JU.P3,~N,~N,~N");
Clazz.overrideMethod (c$, "checkPeriodic", 
function (pt) {
return this.unitCell.checkPeriodic (pt);
}, "JU.P3");
Clazz.defineStatics (c$,
"nullDesc", null);
});
