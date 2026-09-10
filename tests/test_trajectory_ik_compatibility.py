import unittest
from unittest.mock import patch

import numpy as np

from alicia_d_sdk.api.synria_robot_api import SynriaRobotAPI
from alicia_d_sdk.execution.trajectory_executor import CartesianTrajectoryExecutor


class _RobotModelStub:
    num_dof = 6


class _RobotApiStub:
    robot_model = _RobotModelStub()


class TrajectoryIkCompatibilityTest(unittest.TestCase):
    @patch("robocore.kinematics.ik.inverse_kinematics")
    def test_first_failed_pose_uses_public_dof_api(self, inverse_kinematics):
        inverse_kinematics.return_value = {
            "success": False,
            "q": None,
            "pos_err": 1.0,
            "ori_err": 1.0,
        }

        result = SynriaRobotAPI.solve_ik_for_trajectory(
            _RobotApiStub(),
            target_poses=np.eye(4)[None, ...],
            q_init=np.zeros(6),
        )

        self.assertEqual(result["joint_angles"].shape, (1, 6))
        self.assertEqual(result["success_rate"], 0.0)

    def test_low_ik_success_is_blocked_without_explicit_override(self):
        executor = CartesianTrajectoryExecutor(robot=object())

        result = executor.execute(
            joint_angles=np.zeros((10, 6)),
            trajectory_times=np.linspace(0.0, 1.0, 10),
            ik_success_rate=0.002,
            min_success_rate=0.8,
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["executed"], 0)
        self.assertTrue(result["cancelled"])


if __name__ == "__main__":
    unittest.main()
