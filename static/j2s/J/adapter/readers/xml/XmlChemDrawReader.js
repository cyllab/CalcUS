Clazz.declarePackage ("J.adapter.readers.xml");
Clazz.load (["J.adapter.readers.xml.XmlReader", "JU.Lst"], "J.adapter.readers.xml.XmlChemDrawReader", ["java.lang.Boolean", "JU.BS", "$.PT", "J.adapter.smarter.Atom", "J.api.JmolAdapter"], function () {
c$ = Clazz.decorateAsClass (function () {
this.$optimize2D = false;
this.minX = 3.4028235E38;
this.minY = 3.4028235E38;
this.minZ = 3.4028235E38;
this.maxZ = -3.4028235E38;
this.maxY = -3.4028235E38;
this.maxX = -3.4028235E38;
this.is3D = false;
this.bonds = null;
this.warningAtom = null;
Clazz.instantialize (this, arguments);
}, J.adapter.readers.xml, "XmlChemDrawReader", J.adapter.readers.xml.XmlReader);
Clazz.prepareFields (c$, function () {
this.bonds =  new JU.Lst ();
});
Clazz.makeConstructor (c$, 
function () {
Clazz.superConstructor (this, J.adapter.readers.xml.XmlChemDrawReader, []);
});
Clazz.overrideMethod (c$, "processXml", 
function (parent, saxReader) {
this.$optimize2D = this.checkFilterKey ("2D");
this.processXml2 (parent, saxReader);
this.filter = parent.filter;
}, "J.adapter.readers.xml.XmlReader,~O");
Clazz.overrideMethod (c$, "processStartElement", 
function (localName, nodeName) {
if ("fragment".equals (localName)) {
return;
}if ("n".equals (localName)) {
if (this.asc.bsAtoms == null) this.asc.bsAtoms =  new JU.BS ();
var nodeType = this.atts.get ("nodetype");
if ("Fragment".equals (nodeType)) return;
var isNickname = "Nickname".equals (nodeType);
var isConnectionPt = "ExternalConnectionPoint".equals (nodeType);
var warning = this.atts.get ("warning");
this.atom =  new J.adapter.smarter.Atom ();
this.atom.atomName = this.atts.get ("id");
var element = this.atts.get ("element");
this.atom.elementNumber = (warning != null ? 0 : element == null ? 6 : Integer.parseInt (element));
element = J.api.JmolAdapter.getElementSymbol (this.atom.elementNumber);
var isotope = this.atts.get ("isotope");
if (isotope != null) element = isotope + element;
this.setElementAndIsotope (this.atom, element);
var s = this.atts.get ("charge");
if (s != null) {
this.atom.formalCharge = Integer.parseInt (s);
}if (this.atts.containsKey ("xyz")) {
this.is3D = true;
this.setAtom ("xyz");
} else if (this.atts.containsKey ("p")) {
this.setAtom ("p");
}this.asc.addAtomWithMappedName (this.atom);
if (warning != null) {
this.atom.atomName = JU.PT.rep (warning, "&apos;", "'");
this.warningAtom = this.atom;
} else {
this.warningAtom = null;
}if (!isConnectionPt && !isNickname) {
this.asc.bsAtoms.set (this.atom.index);
}return;
}if ("s".equals (localName)) {
if (this.warningAtom != null) {
this.setKeepChars (true);
}}if ("b".equals (localName)) {
var atom1 = this.atts.get ("b");
var atom2 = this.atts.get ("e");
var invertEnds = false;
var order = (this.atts.containsKey ("order") ? this.parseIntStr (this.atts.get ("order")) : 1);
var buf = this.atts.get ("display");
if (buf != null) {
if (buf.equals ("WedgeEnd")) {
invertEnds = true;
order = 1025;
} else if (buf.equals ("WedgeBegin")) {
order = 1025;
} else if (buf.equals ("Hash") || buf.equals ("WedgedHashBegin")) {
order = 1041;
} else if (buf.equals ("WedgedHashEnd")) {
invertEnds = true;
order = 1041;
}}this.bonds.addLast ( Clazz.newArray (-1, [(invertEnds ? atom2 : atom1), (invertEnds ? atom1 : atom2), Integer.$valueOf (order)]));
return;
}}, "~S,~S");
Clazz.defineMethod (c$, "setAtom", 
 function (key) {
var xyz = this.atts.get (key);
var tokens = JU.PT.getTokens (xyz);
var x = this.parseFloatStr (tokens[0]);
var y = -this.parseFloatStr (tokens[1]);
var z = (key === "xyz" ? this.parseFloatStr (tokens[2]) : 0);
if (x < this.minX) this.minX = x;
if (x > this.maxX) this.maxX = x;
if (y < this.minY) this.minY = y;
if (y > this.maxY) this.maxY = y;
if (z < this.minZ) this.minZ = z;
if (z > this.maxZ) this.maxZ = z;
this.atom.set (x, y, z);
}, "~S");
Clazz.overrideMethod (c$, "processEndElement", 
function (localName) {
if ("s".equals (localName)) {
if (this.warningAtom != null) {
var group = this.chars.toString ();
this.warningAtom.atomName += ": " + group;
this.parent.appendLoadNote ("Warning: " + this.warningAtom.atomName);
this.warningAtom = null;
}}this.setKeepChars (false);
}, "~S");
Clazz.overrideMethod (c$, "finalizeSubclassReader", 
function () {
this.fixConnections ();
this.center ();
System.out.println ("bsAtoms = " + this.asc.bsAtoms);
this.asc.setInfo ("minimize3D", Boolean.$valueOf (this.is3D));
this.set2D ();
this.asc.setInfo ("is2D", Boolean.$valueOf (!this.is3D));
if (!this.is3D) this.asc.setModelInfoForSet ("dimension", "2D", this.asc.iSet);
this.parent.appendLoadNote ("ChemDraw CDXML: " + (this.is3D ? "3D" : "2D"));
});
Clazz.defineMethod (c$, "fixConnections", 
 function () {
for (var i = 0, n = this.bonds.size (); i < n; i++) {
var o = this.bonds.get (i);
var b = this.asc.addNewBondFromNames (o[0], o[1], (o[2]).intValue ());
if (b == null) continue;
var a1 = this.asc.atoms[b.atomIndex1];
var a2 = this.asc.atoms[b.atomIndex2];
var pt = (!this.asc.bsAtoms.get (b.atomIndex1) ? a1 : !this.asc.bsAtoms.get (b.atomIndex2) ? a2 : null);
if (pt == null) continue;
for (var j = this.asc.bsAtoms.nextSetBit (0); j >= 0; j = this.asc.bsAtoms.nextSetBit (j + 1)) {
var a = this.asc.atoms[j];
if (Math.abs (a.x - pt.x) < 0.1 && Math.abs (a.y - pt.y) < 0.1) {
if (pt === a1) {
b.atomIndex1 = (a1 = a).index;
} else {
b.atomIndex2 = (a2 = a).index;
}break;
}}
b.distance = a1.distance (a2);
}
});
Clazz.defineMethod (c$, "center", 
 function () {
if (this.minX > this.maxX) return;
var sum = 0;
var n = 0;
if (this.is3D) {
for (var i = this.asc.bondCount; --i >= 0; ) {
if (this.asc.atoms[this.asc.bonds[i].atomIndex1].elementNumber > 1 && this.asc.atoms[this.asc.bonds[i].atomIndex2].elementNumber > 1) {
sum += this.asc.bonds[i].distance;
n++;
}}
}var f = 1;
if (sum > 0) {
f = 1.45 * n / sum;
}var cx = (this.maxX + this.minX) / 2;
var cy = (this.maxY + this.minY) / 2;
var cz = (this.maxZ + this.minZ) / 2;
for (var i = this.asc.ac; --i >= 0; ) {
var a = this.asc.atoms[i];
a.x = (a.x - cx) * f;
a.y = (a.y - cy) * f;
a.z = (a.z - cz) * f;
}
});
});
