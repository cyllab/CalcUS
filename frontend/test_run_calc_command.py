from unittest import mock

from django.test import SimpleTestCase

from .management.commands.run_calc import update_calculation_on_batch_termination


class BatchTerminationTests(SimpleTestCase):
    def test_intermediate_preemption_returns_calculation_to_queue(self):
        calc = mock.Mock(status=1)

        update_calculation_on_batch_termination(calc, attempt=2, max_retries=5)

        self.assertEqual(calc.status, 0)
        self.assertEqual(calc.current_status, "Spot VM preempted; waiting for retry")
        self.assertEqual(calc.error_message, "")
        self.assertIsNone(calc.date_started)
        self.assertIsNone(calc.date_finished)
        calc.save.assert_called_once_with()

    @mock.patch("frontend.management.commands.run_calc.timezone.now")
    def test_final_preemption_marks_calculation_failed(self, now):
        finished_at = mock.Mock()
        now.return_value = finished_at
        calc = mock.Mock(status=1)

        update_calculation_on_batch_termination(calc, attempt=5, max_retries=5)

        self.assertEqual(calc.status, 3)
        self.assertEqual(calc.current_status, "")
        self.assertEqual(
            calc.error_message,
            "The calculation was preempted after all Spot VM retries.",
        )
        self.assertIs(calc.date_finished, finished_at)
        calc.save.assert_called_once_with()

    def test_termination_does_not_overwrite_finished_calculation(self):
        calc = mock.Mock(status=2)

        update_calculation_on_batch_termination(calc, attempt=5, max_retries=5)

        calc.save.assert_not_called()
