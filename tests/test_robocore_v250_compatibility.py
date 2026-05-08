# Copyright (c) 2025 Synria Robotics Co., Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Tests for RoboCore v2.5.0 API compatibility with Alicia-D SDK.

These tests verify that all RoboCore APIs used by the SDK are still
available and functional after upgrading to v2.5.0.
"""

from __future__ import annotations

import numpy as np
import pytest


class _DummySerialComm:
    def is_connected(self):
        return False


class _DummyServoDriver:
    def __init__(self):
        self.data_parser = object()
        self.debug_mode = False
        self.serial_comm = _DummySerialComm()

    def connect(self):
        return False

    def stop_update_thread(self):
        return None

    def disconnect(self):
        return None


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------

class TestRoboCoreVersion:
    """Verify that RoboCore v2.5.0 (or later) is installed."""

    def test_robocore_importable(self):
        """RoboCore must be importable."""
        import robocore  # noqa: F401

    def test_robocore_version_is_2_5_0_or_later(self):
        """Installed RoboCore version must be >= 2.5.0."""
        import robocore
        from packaging.version import Version

        installed = Version(robocore.__version__)
        required = Version("2.5.0")
        assert installed >= required, (
            f"Expected synria-robocore >= 2.5.0, got {robocore.__version__}"
        )

    def test_robocore_set_backend_available(self):
        """robocore.set_backend and get_backend must be top-level attributes."""
        import robocore
        assert callable(robocore.set_backend)
        assert callable(robocore.get_backend)


# ---------------------------------------------------------------------------
# Modeling
# ---------------------------------------------------------------------------

class TestModelingAPI:
    """Verify robocore.modeling public API."""

    def test_robot_model_importable(self):
        from robocore.modeling import RobotModel  # noqa: F401

    def test_chain_view_importable(self):
        from robocore.modeling import ChainView  # noqa: F401


# ---------------------------------------------------------------------------
# Kinematics
# ---------------------------------------------------------------------------

class TestKinematicsAPI:
    """Verify robocore.kinematics public API used by the SDK."""

    def test_forward_kinematics_importable(self):
        from robocore.kinematics import forward_kinematics  # noqa: F401
        assert callable(forward_kinematics)

    def test_inverse_kinematics_importable(self):
        from robocore.kinematics import inverse_kinematics  # noqa: F401
        assert callable(inverse_kinematics)

    def test_jacobian_importable(self):
        from robocore.kinematics import jacobian  # noqa: F401
        assert callable(jacobian)

    def test_ik_submodule_importable(self):
        """The SDK imports from robocore.kinematics.ik directly at some call sites."""
        from robocore.kinematics.ik import inverse_kinematics  # noqa: F401
        assert callable(inverse_kinematics)


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

class TestTransformAPI:
    """Verify robocore.transform public API used by the SDK."""

    def test_make_transform_importable(self):
        from robocore.transform import make_transform  # noqa: F401
        assert callable(make_transform)

    def test_quaternion_to_matrix_importable(self):
        from robocore.transform import quaternion_to_matrix  # noqa: F401
        assert callable(quaternion_to_matrix)

    def test_rpy_to_matrix_importable(self):
        from robocore.transform import rpy_to_matrix  # noqa: F401
        assert callable(rpy_to_matrix)

    def test_matrix_to_quaternion_importable(self):
        from robocore.transform import matrix_to_quaternion  # noqa: F401
        assert callable(matrix_to_quaternion)

    def test_matrix_to_euler_importable(self):
        from robocore.transform import matrix_to_euler  # noqa: F401
        assert callable(matrix_to_euler)

    def test_se3_get_rotation_importable(self):
        from robocore.transform.se3 import get_rotation  # noqa: F401
        assert callable(get_rotation)

    def test_conversions_matrix_to_axis_angle_importable(self):
        from robocore.transform.conversions import matrix_to_axis_angle  # noqa: F401
        assert callable(matrix_to_axis_angle)

    def test_make_transform_returns_4x4(self):
        """make_transform(R, t) -> 4x4 homogeneous matrix."""
        from robocore.transform import make_transform
        R = np.eye(3)
        t = np.array([1.0, 2.0, 3.0])
        T = make_transform(R, t)
        assert np.array(T).shape == (4, 4)

    def test_rpy_to_matrix_returns_3x3(self):
        """rpy_to_matrix(roll, pitch, yaw) -> 3x3 rotation matrix."""
        from robocore.transform import rpy_to_matrix
        R = rpy_to_matrix(0.0, 0.0, 0.0)
        assert np.array(R).shape == (3, 3)


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------

class TestUtilsAPI:
    """Verify robocore.utils public API used by the SDK."""

    def test_backend_module_importable(self):
        from robocore.utils import backend  # noqa: F401

    def test_to_numpy_importable(self):
        from robocore.utils.backend import to_numpy  # noqa: F401
        assert callable(to_numpy)

    def test_set_backend_importable(self):
        from robocore.utils.backend import set_backend, get_backend  # noqa: F401
        assert callable(set_backend)
        assert callable(get_backend)

    def test_cpp_backend_selectable(self):
        import robocore

        previous = robocore.get_backend()
        try:
            robocore.set_backend('cpp')
            assert robocore.get_backend() == 'cpp'
        finally:
            if previous == 'torch':
                robocore.set_backend('torch', device='cpu')
            else:
                robocore.set_backend(previous)

    def test_beauty_print_importable(self):
        from robocore.utils.beauty_logger import beauty_print  # noqa: F401
        assert callable(beauty_print)

    def test_beauty_print_array_importable(self):
        from robocore.utils.beauty_logger import beauty_print_array  # noqa: F401
        assert callable(beauty_print_array)

    def test_to_numpy_converts_list(self):
        from robocore.utils.backend import to_numpy
        result = to_numpy([1.0, 2.0, 3.0])
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

class TestPlanningAPI:
    """Verify robocore.planning public API used by the SDK."""

    def test_bspline_planner_importable(self):
        from robocore.planning import BSplinePlanner  # noqa: F401

    def test_multi_segment_planner_importable(self):
        from robocore.planning import MultiSegmentPlanner  # noqa: F401

    def test_spline_curve_planner_importable(self):
        from robocore.planning import SplineCurvePlanner  # noqa: F401

    def test_plot_joint_trajectory_importable(self):
        from robocore.planning import plot_joint_trajectory  # noqa: F401
        assert callable(plot_joint_trajectory)

    def test_plot_cartesian_with_ik_importable(self):
        from robocore.planning import plot_cartesian_with_ik  # noqa: F401
        assert callable(plot_cartesian_with_ik)


class TestSdkBackendBehavior:
    """Verify Alicia-D SDK backend defaults and overrides."""

    def test_synria_robot_api_defaults_to_cpp_backend(self, monkeypatch):
        from alicia_d_sdk.api.synria_robot_api import SynriaRobotAPI

        set_backend_calls = []

        def fake_set_backend(backend, device='cpu'):
            set_backend_calls.append((backend, device))

        monkeypatch.setattr(
            'alicia_d_sdk.api.synria_robot_api.rc.set_backend',
            fake_set_backend,
        )

        SynriaRobotAPI(
            servo_driver=_DummyServoDriver(),
            robot_model=object(),
            auto_connect=False,
        )

        assert set_backend_calls == [('cpp', 'cpu')]

    def test_get_pose_respects_explicit_numpy_backend(self, monkeypatch):
        from alicia_d_sdk.api.synria_robot_api import SynriaRobotAPI

        set_backend_calls = []

        def fake_set_backend(backend, device='cpu'):
            set_backend_calls.append((backend, device))

        monkeypatch.setattr(
            'alicia_d_sdk.api.synria_robot_api.rc.set_backend',
            fake_set_backend,
        )
        monkeypatch.setattr(
            SynriaRobotAPI,
            'get_robot_state',
            lambda self, info_type='joint', timeout=1.0, cache=True: [0.0] * 6,
        )
        monkeypatch.setattr(
            'alicia_d_sdk.api.synria_robot_api.forward_kinematics',
            lambda robot_model, joint_angles, return_end=True: np.eye(4),
        )
        monkeypatch.setattr(
            'alicia_d_sdk.api.synria_robot_api.matrix_to_euler',
            lambda rotation, seq='xyz': np.zeros(3),
        )
        monkeypatch.setattr(
            'alicia_d_sdk.api.synria_robot_api.matrix_to_quaternion',
            lambda rotation: np.array([0.0, 0.0, 0.0, 1.0]),
        )

        robot = SynriaRobotAPI(
            servo_driver=_DummyServoDriver(),
            robot_model=object(),
            auto_connect=False,
        )
        set_backend_calls.clear()

        robot.get_pose(backend='numpy')

        assert set_backend_calls == [('numpy', 'cpu')]
