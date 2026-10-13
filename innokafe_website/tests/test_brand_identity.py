import sys
import unittest
from pathlib import Path

# Add tools directory to path
TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from test_brand_identity_suite import (
    TestBrandVectorAssets,
    TestAnimationSuite,
    TestFaviconAndManifestSuite,
    TestNavbarAndHeaderIntegration,
)

if __name__ == "__main__":
    unittest.main(verbosity=2)
