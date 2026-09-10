from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import alicia_d_sdk


class BundledModelTest(unittest.TestCase):
    def test_model_exists_and_has_valid_joint_limits(self):
        model_path = Path(alicia_d_sdk._BUNDLED_MODEL_PATH)

        self.assertTrue(model_path.is_file())

        root = ET.parse(model_path).getroot()
        joints = {joint.attrib["name"]: joint for joint in root.findall("joint")}

        joint2 = joints["joint2"]
        joint3 = joints["joint3"]

        self.assertEqual(joint2.find("axis").attrib["xyz"], "0 0 1")
        self.assertEqual(joint2.find("limit").attrib["lower"], "-3.14")
        self.assertEqual(joint2.find("limit").attrib["upper"], "0")

        self.assertEqual(joint3.find("axis").attrib["xyz"], "0 0 1")
        self.assertEqual(joint3.find("limit").attrib["lower"], "0")
        self.assertEqual(joint3.find("limit").attrib["upper"], "3.14")


if __name__ == "__main__":
    unittest.main()
