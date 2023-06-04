Software Packages
=================

This page details package-specific information and quirks.

Supported Packages
------------------

============ ===================== ==================================
Name         License               Homepage
============ ===================== ==================================
Gaussian 16  Commercial            https://gaussian.com/
ORCA         Free for academia     https://orcaforum.kofo.mpg.de
xtb          Open-source (LGPL-3)  https://github.com/grimme-lab/xtb

                                   https://github.com/grimme-lab/crest

                                   https://github.com/grimme-lab/stda

                                   https://github.com/grimme-lab/xtb4stda

============ ===================== ==================================


Installation Quirks
--------------------

xtb Configuration
^^^^^^^^^^^^^^^^^

Calculations involving ``xtb``-related packages are grouped under the software ``xtb``. However, not all calculation types require only the ``xtb`` executable.

- Conformational searches (constrained or not) require ``crest`` (`homepage <https://github.com/grimme-lab/crest>`__)
- Transition state optimisations and minimum energy paths require ``ORCA`` as well as the ``otool_xtb`` wrapper (see `here <https://xtb-docs.readthedocs.io/en/latest/setup.html?highlight=orca#using-xtb-with-orca>`__)
- UV-Vis predictions require ``xtb4stda`` and ``stda`` (`homepage <https://github.com/grimme-lab/stda>`__) as well as solvent parameters (if solvation is used, see `here <https://github.com/grimme-lab/xtb4stda>`__)

Specifications
--------------

Specifications are modifiers or additional keywords that will change the input file. Common specifications are listed below for Gaussian and ORCA. Any valid additional keyword for these software can be used, even if not present below. In the case of xtb, only the recognized specifications listed below can be used for security reasons.

Gaussian
^^^^^^^^

When performing geometrical optimisations (constrained or not), multiple options can be specified to affect the optimisation procedure. Most commonly, the convergence criterion can be change with ``opt(loose)`` or ``opt(tight)``. If a system has the tendency to "wiggle" a lot without converging to a minimum, the option ``opt(maxstep=X)`` code be used, where ``X`` is an integer, typically from 5 to 30. This prevents the system from making optimisation steps that are too big, which might endlessly overshoot past the minimum.

Frequency calculations calculations involving Hartree-Fock and that do not make use of Raman intensities can be sped up by using ``freq(noraman)``.

Multiple options can be combined. For example:
* ``opt(loose, maxstep=10)``
* ``opt(loose, maxstep=10) EmpiricalDispersion=GD3``

Additional options related to another calculation type than the one performed are ignored. For example, specifying ``opt(maxstep=10)`` when performing a frequency calculation (``freq``) will not do anything.

ORCA
^^^^

Hirshfeld charges can be calculated by using the specification ``phirshfeld``. Note that this is not an ORCA keyword; CalcUS instead adds the appropriate block to the input.

The geometrical optimisation convergence criterion can be modified with ``LOOSEOPT``, ``TIGHTOPT`` or ``VERYTIGHTOPT``.

xtb
^^^

As many options are given on the command line, no unknown specification is allowed. All the possible specifications are listed here.	

The accuracy and the number of iterations can be specified with ``--acc X`` and ``--iterations X``, where ``X`` is the desired value.

The Hamiltonian can be chosen with ``--gfn 2`` (default), ``--gfn 1``, ``--gfn 0`` or ``--gfnff``. These options are valid for all calculations, except TS optimisations (which use ORCA use calculation driver).

The convergence criteria of geometrical optimisations can be chosen with ``--opt level``, where level is ``crude``, ``sloppy``, ``loose``, ``lax``, ``normal``, ``tight`` (default), ``vtight`` or ``extreme``.

Conformational searches (constrained or not) have several particular options. Faster/cruder sampling procedures can be requested with ``--quick``, ``--squick`` and ``--mquick``. The RMSD threshold for considering conformers as different can be set with ``--rthr X``, where ``X`` is the threshold in Ångström (default of 2.0 in CalcUS). Furthermore, the energy window to consider can be set with ``--ewin X``, where ``X`` is the treshold in kcal/mol (default of 6 in CalcUS).

Constrained geometrical optimisations and constrained conformational searches employ a harmonic potential to constrain coordinates (distances, angles, dihedral angles). The force constant of this potential can be chosen with ``--forceconstant X``, where ``X`` is the force constant in Hartree/Bohr². By default, CalcUS uses a force constant of 1.0, which corresponds to a very stiff potential well. In most cases, this high value forces the use of small timesteps in meta-dynamic and molecular dynamic simulations (for constrained conformational searches). If the constrained coordinates do not need to remain exactly constant, the simulations can be accelerated by a smaller force constant.

