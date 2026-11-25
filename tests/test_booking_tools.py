import unittest
from unittest.mock import patch

from booking_tools import confirm_booking, propose_booking, reject_booking


class BookingToolsTests(unittest.TestCase):
    def setUp(self):
        self.request = {'event_id': 'EVT-001', 'slot_id': 'SLOT-0002',
                        'venue_id': 'VEN-001', 'date': '2026-12-13',
                        'start_time': '10:00', 'end_time': '14:00'}

    def test_approval_is_required_and_confirmation_is_separate(self):
        booking = propose_booking(self.request)
        self.assertEqual(booking['status'], 'pending_approval')
        with self.assertRaises(PermissionError):
            confirm_booking(booking)
        confirmed = confirm_booking(booking, approved=True)
        self.assertEqual(confirmed['proposal']['status'], 'approved')
        self.assertEqual(booking['proposal']['status'], 'pending_approval')
        self.assertEqual(confirmed['trace'][-1]['action'], 'confirm_mock_booking')

    def test_rejection_cannot_be_confirmed(self):
        rejected = reject_booking(propose_booking(self.request))
        self.assertEqual(rejected['status'], 'rejected')
        with self.assertRaises(ValueError):
            confirm_booking(rejected, approved=True)

    def test_unavailable_and_recheck(self):
        invalid = propose_booking({**self.request, 'slot_id': 'SLOT-0001'})
        self.assertEqual(invalid['status'], 'error')
        booking = propose_booking(self.request)
        with patch('booking_tools._check_availability', return_value=False):
            result = confirm_booking(booking, approved=True)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['proposal']['status'], 'pending_approval')


if __name__ == '__main__':
    unittest.main()
