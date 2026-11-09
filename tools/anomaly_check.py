"""Optional anomaly demonstration; fit only clean1 and score another run."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from twin.anomaly import HealthyAnomalyModel
from twin.data import is_fake, read_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean1", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--contamination", type=float, default=0.02)
    args = parser.parse_args()
    try:
        if is_fake(args.clean1) != is_fake(args.run):
            raise ValueError("Do not mix FAKE and real recordings.")
        model = HealthyAnomalyModel().fit(read_run(args.clean1), args.contamination)
        scores = model.score(read_run(args.run))
        print(f"{'FAKE / ' if is_fake(args.run) else ''}{args.run.name}: {np.mean(scores < 0)*100:.1f}% of readings unusual.")
        print("Secondary flag only: different does not mean worse. It cannot identify a fault or verify service.")
        print("Contamination is an operator-supplied demo value; validate it against recorded blocked runs.")
    except ImportError:
        parser.exit(1, "Install optional dependencies: python -m pip install -r requirements-optional.txt\n")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Anomaly check failed: {exc}\n")


if __name__ == "__main__":
    main()
