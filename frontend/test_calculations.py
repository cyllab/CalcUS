"""
This file of part of CalcUS.

Copyright (C) 2020-2022 Raphaël Robidas

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


import os

from functools import partial

from .calculation_unittest import CalculationUnitTest
from .calcusliveserver import tests_dir
from .models import *
from .libxyz import *


class XtbCalculationTests(CalculationUnitTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.params = {
            "mol_name": "methane",
            "type": "Single-Point Energy",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "software": "xtb",
            "theory_level": "GFN2-xTB",
            "method": "GFN2-xTB",
        }

    def test_sp(self):
        self.assertTrue(self.run_test())

    def test_opt(self):
        self.assertTrue(self.run_test(type="Geometrical Optimisation"))

    def test_freq(self):
        self.assertTrue(
            self.run_test(
                type="Frequency Calculation", in_file="carbo_cation.mol", charge=1
            )
        )

    def test_freq_solv_GBSA(self):
        self.assertTrue(
            self.run_test(
                type="Frequency Calculation",
                in_file="carbo_cation.mol",
                charge=1,
                solvent="Chloroform",
                solvation_model="GBSA",
            )
        )

    def test_freq_solv_ALPB(self):
        self.assertTrue(
            self.run_test(
                type="Frequency Calculation",
                in_file="carbo_cation.mol",
                charge=1,
                solvent="Chloroform",
                solvation_model="ALPB",
            )
        )

    def test_conf_search(self):
        self.assertTrue(
            self.run_test(type="Conformational Search", in_file="ethanol.sdf")
        )

    def test_conf_search_gfnff(self):
        self.assertTrue(
            self.run_test(
                type="Conformational Search",
                in_file="ethanol.sdf",
                specifications="--gfnff",
            )
        )

    def test_conf_search_invalid_specification(self):
        self.assertFalse(
            self.run_test(
                type="Conformational Search",
                in_file="ethanol.sdf",
                specifications="--gfn2-ff",
            )
        )

    def test_conf_search_gfnff_sp(self):
        self.assertTrue(
            self.run_test(
                type="Conformational Search",
                in_file="ethanol.sdf",
                specifications="--gfn2//gfnff",
            )
        )

    # ORCA does not support calculating the Hessian before TS optimization with xtb
    # def test_ts(self):
    #    self.assertTrue(self.run_test(type="TS Optimisation", in_file="ts.xyz"))

    def test_scan_distance(self):
        self.assertTrue(
            self.run_test(
                type="Constrained Optimisation",
                constraints="Scan_1.5_2.0_10/1_2;",
                callback=partial(self.cb_has_n_conformers, 10),
            )
        )

    def test_scan_angle(self):
        self.assertTrue(
            self.run_test(
                type="Constrained Optimisation",
                constraints="Scan_120_130_10/1_2_3;",
                callback=partial(self.cb_has_n_conformers, 10),
            )
        )

    def test_scan_dihedral(self):
        self.assertTrue(
            self.run_test(
                type="Constrained Optimisation",
                constraints="Scan_0_10_10/1_2_3_4;",
                callback=partial(self.cb_has_n_conformers, 10),
            )
        )

    def test_freeze_distance(self):
        self.assertTrue(
            self.run_test(
                type="Constrained Optimisation",
                constraints="Freeze/1_4;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freeze_distance2(self):
        self.assertTrue(
            self.run_test(
                type="Constrained Optimisation",
                constraints="Freeze/1_4;Freeze/2_3;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freeze_angle(self):
        self.assertTrue(
            self.run_test(
                type="Constrained Optimisation",
                constraints="Freeze/1_2_3;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freeze_dihedral(self):
        self.assertTrue(
            self.run_test(
                type="Constrained Optimisation",
                constraints="Freeze/1_2_3_4;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_NEB(self):
        self.assertTrue(
            self.run_test(
                type="Minimum Energy Path",
                in_file="elimination_substrate.xyz",
                aux_file="elimination_product.xyz",
                driver="orca",
                charge=-1,
                specifications="--nimages 3",
                callback=partial(self.cb_has_n_conformers, 5),
            )
        )

    def test_constrained_conf_search(self):
        xyz = parse_xyz_from_file(os.path.join(tests_dir, "pentane.xyz"))
        ang0 = get_angle(xyz, 1, 5, 8)

        self.assertTrue(
            self.run_test(
                type="Constrained Conformational Search",
                in_file="pentane.xyz",
                constraints="Freeze/1_5_8;",
                callback=partial(self.cb_has_angle_value, (1, 5, 8), ang0),
            )
        )

    def test_xtb4stda(self):
        self.assertTrue(
            self.run_test(
                type="UV-Vis Calculation",
            )
        )

        prop = Property.objects.latest("id")
        self.assertTrue(prop.has_uvvis)

    def test_invalid_spec(self):
        self.assertFalse(self.run_test(specifications="--nimages 50"))

        calc = Calculation.objects.latest("pk")
        self.assertTrue(calc.error_message != "")


class OrcaCalculationTests(CalculationUnitTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.params = {
            "mol_name": "test",
            "type": "Single-Point Energy",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "software": "ORCA",
            "theory_level": "HF",
            "basis_set": "Def2-SVP",
        }

    def test_sp_SE(self):
        self.assertTrue(self.run_test(theory_level="Semi-empirical", method="AM1"))

    def test_sp_HF(self):
        self.assertTrue(self.run_test(in_file="H2.mol2"))

    def test_sp_HF_CPCM(self):
        self.assertTrue(
            self.run_test(in_file="H2.mol2", solvation_model="CPCM", solvent="Methanol")
        )

    def test_sp_DFT(self):
        self.assertTrue(self.run_test(theory_level="DFT", method="M062X"))

    def test_sp_RIMP2(self):
        self.assertTrue(
            self.run_test(
                in_file="H2.sdf",
                theory_level="RI-MP2",
                basis_set="cc-pVDZ",
                specifications="cc-pVDZ/C",
            )
        )

    def test_opt_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Geometrical Optimisation",
            )
        )

    def test_opt_HF(self):
        self.assertTrue(
            self.run_test(
                basis_set="Def2-SVP",
                type="Geometrical Optimisation",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_opt_DFT(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                theory_level="DFT",
                method="M062X",
                basis_set="Def2-SVP",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_opt_RIMP2(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                in_file="H2.sdf",
                theory_level="RI-MP2",
                basis_set="cc-pVDZ",
                specifications="cc-pVDZ/C",
            )
        )

    def test_freq_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="PM3",
                type="Frequency Calculation",
                in_file="carbo_cation.mol",
                charge=1,
            )
        )

    def test_freq_HF(self):
        self.assertTrue(
            self.run_test(
                type="Frequency Calculation", in_file="carbo_cation.mol", charge=1
            )
        )

    def test_freq_DFT(self):
        self.assertTrue(
            self.run_test(
                theory_level="DFT", method="M062X", type="Frequency Calculation"
            )
        )

    def test_freq_DFT_single_atom(self):
        self.assertTrue(
            self.run_test(
                type="Frequency Calculation",
                theory_level="DFT",
                method="M062X",
                in_file="Cl.xyz",
                charge=-1,
            )
        )

    def test_ts_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="TS Optimisation",
                in_file="mini_ts.xyz",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_ts_HF(self):
        self.assertTrue(
            self.run_test(
                type="TS Optimisation",
                in_file="mini_ts.xyz",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_ts_DFT(self):
        self.assertTrue(
            self.run_test(
                theory_level="DFT",
                method="M062X",
                type="TS Optimisation",
                in_file="mini_ts.xyz",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_ts_RIMP2(self):
        self.assertTrue(
            self.run_test(
                theory_level="RI-MP2",
                basis_set="cc-pVDZ",
                type="TS Optimisation",
                in_file="mini_ts.xyz",
                specifications="cc-pVDZ/C",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    """
    #TODO: reactivate once fixed
    def test_mo_HF(self):
        self.assertTrue(
            self.run_test(type="MO Calculation", in_file="carbo_cation.mol", charge=1)
        )

    def test_mo_DFT(self):
        self.assertTrue(
            self.run_test(
                theory_level="DFT",
                method="M062X",
                type="MO Calculation",
                in_file="carbo_cation.mol",
                charge=1,
            )
        )
    """

    def test_scan_distance_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Scan_3.5_1.5_5/1_2;",
                callback=partial(self.cb_has_n_conformers, 5),
            )
        )

    def test_scan_angle_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Scan_120_130_10/1_2_3;",
                callback=partial(self.cb_has_n_conformers, 10),
            )
        )

    def test_scan_dihedral_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Scan_0_10_10/1_2_3_4;",
                callback=partial(self.cb_has_n_conformers, 10),
            )
        )

    def test_freeze_distance_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Freeze/1_4;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freeze_distance_SE2(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Freeze/1_4;Freeze/2_3;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freeze_angle_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Freeze/1_2_3;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freeze_dihedral_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Freeze/1_2_3_4;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_nmr_DFT(self):
        self.assertTrue(
            self.run_test(
                theory_level="DFT",
                method="M062X",
                type="NMR Prediction",
                specifications="Def2/J",
            )
        )

    def test_opt_DFT_loose(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                theory_level="DFT",
                method="M062X",
                specifications="looseopt",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_opt_DFT_tightscf(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                theory_level="DFT",
                method="M062X",
                specifications="tightscf",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_opt_DFT_single_atom(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                theory_level="DFT",
                method="M062X",
                in_file="Cl.xyz",
                charge=-1,
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_DFT_default_pop(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                theory_level="DFT",
                method="M062X",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

        prop = Property.objects.latest("id")
        self.assertIn("Mulliken:", prop.charges)
        self.assertIn("Loewdin:", prop.charges)

    """
    # Not valid with ccinput v1.3.2
    def test_DFT_hirshfeld_pop(self):
        self.assertTrue(self.run_test(type="Geometrical Optimisation", theory_level="DFT",
                method="M062X", specifications="--phirshfeld",
                callback=partial(self.cb_has_n_conformers, 1)))

        prop = Property.objects.latest('id')
        self.assertIn("Hirshfeld:", prop.charges)
    """


class GaussianCalculationTests(CalculationUnitTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.params = {
            "mol_name": "test",
            "type": "Single-Point Energy",
            "project": "New Project",
            "new_project_name": "SeleniumProject",
            "in_file": "CH4.mol",
            "software": "Gaussian",
            "theory_level": "HF",
            "basis_set": "Def2-SVP",
        }

    def test_sp_SE(self):
        self.assertTrue(self.run_test(theory_level="Semi-empirical", method="AM1"))

    def test_sp_HF(self):
        self.assertTrue(self.run_test(in_file="H2.mol2"))

    def test_sp_HF_CPCM(self):
        self.assertTrue(
            self.run_test(in_file="H2.mol2", solvation_model="CPCM", solvent="Methanol")
        )

    def test_sp_DFT(self):
        self.assertTrue(self.run_test(theory_level="DFT", method="M062X"))

    def test_sp_DFT_SMD18(self):
        self.assertTrue(
            self.run_test(
                theory_level="DFT",
                method="M062X",
                solvation_model="SMD",
                solvent="Methanol",
            )
        )

    def test_sp_DFT_SMD18(self):
        self.assertTrue(
            self.run_test(
                theory_level="DFT",
                method="M062X",
                solvation_model="SMD",
                solvation_radii="SMD18",
                solvent="Methanol",
            )
        )

    def test_opt_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Geometrical Optimisation",
            )
        )

    def test_opt_HF(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_opt_DFT(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                theory_level="DFT",
                method="M062X",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_opt_DFT_single_atom(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                theory_level="DFT",
                method="M062X",
                in_file="Cl.xyz",
                charge=-1,
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freq_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="PM3",
                type="Frequency Calculation",
                in_file="carbo_cation.mol",
                charge=1,
            )
        )

    def test_freq_HF(self):
        self.assertTrue(
            self.run_test(
                type="Frequency Calculation", in_file="carbo_cation.mol", charge=1
            )
        )

    def test_freq_DFT(self):
        self.assertTrue(
            self.run_test(
                theory_level="DFT", method="M062X", type="Frequency Calculation"
            )
        )

    def test_freq_DFT_single_atom(self):
        self.assertTrue(
            self.run_test(
                type="Frequency Calculation",
                theory_level="DFT",
                method="M062X",
                in_file="Cl.xyz",
                charge=-1,
            )
        )

    def test_ts_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="TS Optimisation",
                in_file="mini_ts.xyz",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_ts_HF(self):
        self.assertTrue(
            self.run_test(
                type="TS Optimisation",
                in_file="mini_ts.xyz",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_ts_DFT(self):
        self.assertTrue(
            self.run_test(
                theory_level="DFT",
                method="M062X",
                type="TS Optimisation",
                in_file="mini_ts.xyz",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_scan_distance_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Scan_3.5_1.5_5/1_2;",
                callback=partial(self.cb_has_n_conformers, 6),
            )
        )

    def test_scan_angle_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Scan_120_130_10/1_2_3;",
                callback=partial(self.cb_has_n_conformers, 11),
            )
        )

    def test_scan_dihedral_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Scan_0_10_10/1_2_3_4;",
                callback=partial(self.cb_has_n_conformers, 11),
            )
        )

    def test_freeze_distance_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Freeze/1_4;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freeze_distance_SE2(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Freeze/1_4;Freeze/2_3;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freeze_angle_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Freeze/1_2_3;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_freeze_dihedral_SE(self):
        self.assertTrue(
            self.run_test(
                theory_level="Semi-empirical",
                method="AM1",
                type="Constrained Optimisation",
                constraints="Freeze/1_2_3_4;",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

    def test_nmr_DFT(self):
        self.assertTrue(
            self.run_test(theory_level="DFT", method="M062X", type="NMR Prediction")
        )

    def test_DFT_pop(self):
        self.assertTrue(
            self.run_test(theory_level="DFT", method="M062X", specifications="pop(NBO)")
        )

        prop = Property.objects.latest("id")
        self.assertIn("NBO:", prop.charges)

    def test_DFT_pop_opt(self):
        self.assertTrue(
            self.run_test(
                type="Geometrical Optimisation",
                theory_level="DFT",
                method="M062X",
                specifications="pop(NBO)",
                callback=partial(self.cb_has_n_conformers, 1),
            )
        )

        prop = Property.objects.latest("id")
        self.assertIn("NBO:", prop.charges)

    def test_DFT_not_pop(self):
        self.assertTrue(self.run_test(theory_level="DFT", method="M062X"))

        prop = Property.objects.latest("id")
        self.assertNotIn("NBO:", prop.charges)

    def test_DFT_multiple_pop(self):
        self.assertTrue(
            self.run_test(
                theory_level="DFT", method="M062X", specifications="pop(NBO, Hirshfeld)"
            )
        )

        prop = Property.objects.latest("id")
        self.assertIn("NBO:", prop.charges)
        self.assertIn("Hirshfeld:", prop.charges)
        self.assertIn("CM5:", prop.charges)

    def test_DFT_multiple_pop(self):
        self.assertTrue(
            self.run_test(theory_level="DFT", method="M062X", specifications="pop(esp)")
        )

        prop = Property.objects.latest("id")
        self.assertIn("ESP:", prop.charges)

    def test_DFT_pop_HLY(self):
        self.assertTrue(
            self.run_test(theory_level="DFT", method="M062X", specifications="pop(hly)")
        )

        prop = Property.objects.latest("id")
        self.assertIn("HLY:", prop.charges)

    def test_scan_pop(self):
        self.assertTrue(
            self.run_test(
                theory_level="HF",
                type="Constrained Optimisation",
                constraints="Scan_3.5_5.0_10/1_2;",
                specifications="pop(nbo)",
                callback=partial(self.cb_has_n_conformers, 11),
            )
        )

        calc = Calculation.objects.latest("id")
        self.assertEqual(calc.parameters.specifications.strip(), "pop(nbo)")
