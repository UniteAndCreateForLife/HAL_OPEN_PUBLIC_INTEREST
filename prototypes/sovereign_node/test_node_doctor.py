import unittest

from node_doctor import parse_nvidia_smi, recommend_profile


class NodeDoctorTests(unittest.TestCase):
    def test_parse_nvidia_smi(self):
        rows = parse_nvidia_smi(
            "NVIDIA RTX 4090, 24564, 590.12\n"
            "NVIDIA RTX 2080, 8192, 590.12\n"
        )
        self.assertEqual(rows[0]["name"], "NVIDIA RTX 4090")
        self.assertEqual(rows[0]["memory_mib"], 24564)
        self.assertEqual(rows[1]["memory_mib"], 8192)

    def test_profile_large_gpu(self):
        result = recommend_profile(64, [24])
        self.assertEqual(result["profile"], "gpu-large")
        self.assertFalse(result["guarantee"])

    def test_profile_small_gpu(self):
        self.assertEqual(
            recommend_profile(32, [8])["profile"],
            "gpu-small",
        )

    def test_profile_cpu_fallback(self):
        self.assertEqual(
            recommend_profile(64, [])["profile"],
            "cpu-small",
        )

    def test_profile_minimal(self):
        self.assertEqual(
            recommend_profile(16, [])["profile"],
            "minimal",
        )


if __name__ == "__main__":
    unittest.main()
