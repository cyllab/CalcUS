import os
import tempfile
from unittest import mock

from django.test import TransactionTestCase

from . import tasks
from .constants import ErrorCodes
from .models import (
    Calculation,
    CalculationOrder,
    Ensemble,
    Parameters,
    Property,
    Structure,
)


class DuplicatePropertyParserTests(TransactionTestCase):
    def setUp(self):
        self.parameters = Parameters.objects.create(charge=0, multiplicity=1)
        self.input_ensemble = Ensemble.objects.create(name="Input")
        self.input_structure = Structure.objects.create(
            parent_ensemble=self.input_ensemble,
            number=1,
            xyz_structure="1\ninput\nH 0 0 0\n",
        )
        self.result_ensemble = Ensemble.objects.create(name="Result")
        self.order = CalculationOrder.objects.create(
            name="xTB scan",
            structure=self.input_structure,
            parameters=self.parameters,
            result_ensemble=self.result_ensemble,
            constraints="scan",
        )
        self.calc = Calculation.objects.create(
            order=self.order,
            structure=self.input_structure,
            parameters=self.parameters,
            result_ensemble=self.result_ensemble,
            constraints="scan",
        )

    def _write_xtb_scan(self, root, energy, z):
        calc_dir = os.path.join(root, str(self.calc.id))
        os.makedirs(calc_dir, exist_ok=True)
        with open(os.path.join(calc_dir, "xtbscan.log"), "w") as handle:
            handle.write(f"1\nenergy: {energy}\nH 0 0 {z}\n")

    def test_rerun_xtb_scan_reuses_structure_without_creating_duplicate_property(self):
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(
            tasks, "CALCUS_SCR_HOME", tmpdir
        ), mock.patch.object(tasks, "launch_xtb_calc", return_value=ErrorCodes.SUCCESS):
            self._write_xtb_scan(tmpdir, -34.810076205738, 0)
            self.assertEqual(tasks.xtb_scan(self.calc), ErrorCodes.SUCCESS)

            structure = self.result_ensemble.structure_set.get(number=1)
            first_structure_id = structure.pk
            prop = structure.properties.get(parameters=self.parameters)
            self.assertEqual(prop.energy, -34.810076205738)
            self.assertIn("H 0 0 0", structure.xyz_structure)

            self._write_xtb_scan(tmpdir, -34.807453173431, 1)
            self.assertEqual(tasks.xtb_scan(self.calc), ErrorCodes.SUCCESS)

            structure.refresh_from_db()
            self.assertEqual(structure.pk, first_structure_id)
            self.assertIn("H 0 0 1", structure.xyz_structure)
            self.assertEqual(
                Property.objects.filter(
                    parent_structure=structure,
                    parameters=self.parameters,
                ).count(),
                1,
            )
            prop.refresh_from_db()
            self.assertEqual(prop.energy, -34.807453173431)
