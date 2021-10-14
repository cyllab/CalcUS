/*
 * International Chemical Identifier (InChI)
 * Version 1
 * Software version 1.06
 * December 15, 2020
 *
 * The InChI library and programs are free software developed under the
 * auspices of the International Union of Pure and Applied Chemistry (IUPAC).
 * Originally developed at NIST.
 * Modifications and additions by IUPAC and the InChI Trust.
 * Some portions of code were developed/changed by external contributors
 * (either contractor or volunteer) which are listed in the file
 * 'External-contributors' included in this distribution.
 *
 * IUPAC/InChI-Trust Licence No.1.0 for the
 * International Chemical Identifier (InChI)
 * Copyright (C) IUPAC and InChI Trust
 *
 * This library is free software; you can redistribute it and/or modify it
 * under the terms of the IUPAC/InChI Trust InChI Licence No.1.0,
 * or any later version.
 *
 * Please note that this library is distributed WITHOUT ANY WARRANTIES
 * whatsoever, whether expressed or implied.
 * See the IUPAC/InChI-Trust InChI Licence No.1.0 for more details.
 *
 * You should have received a copy of the IUPAC/InChI Trust InChI
 * Licence No. 1.0 with this library; if not, please e-mail:
 *
 * info@inchi-trust.org
 *
 */


This package contains InChI Software version 1.06.

This is a combination of bugfix release and feature release.

What is new:

- security-related bugfixes;
- a number of other bugfixes and minor improvements;
- experimental support for pseudo element (Zz, or "star") atoms;
- modified experimental support of InChI/InChIKey for regular single-strand polymers (explicit pseudo atoms are used);
- minor update to InChI API Library;
- optional support of Intel(R) Threading Building Blocks scalable memory allocators;
- added several convenience features and software options.

InChI Software binaries are placed in the file/directory INCHI-1-BIN. 
Example data files are placed in the file/directory INCHI-1-TEST.  
Documentation is placed in the file/directory INCHI-1-DOC. 
InChI Software source codes are placed in the file/directory INCHI-1-SRC; 
this file/directory also contains examples of InChI API usage.
