"""
tests/fixtures/generate_reference.py
生成各模块的 TDD 基准输出（Fixtures）

用法:
  conda run -n pcl-1.12 python tests/fixtures/generate_reference.py --module <name>
  conda run -n pcl-1.12 python tests/fixtures/generate_reference.py --all
"""
import argparse, pickle, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
REFERENCE = PROJECT_ROOT / "reference_project"
FIXTURES = Path(__file__).parent
FIXTURES.mkdir(exist_ok=True)

# ── 在此添加各模块的 fixture 生成逻辑 ──────────────────────────────
def get_modules():
    return []  # e.g. ["point_cloud_loader", "preprocessor"]

def prepare_inputs(module: str) -> dict:
    raise NotImplementedError(f"请为 '{module}' 实现 prepare_inputs()")

def run_reference(module: str, inputs: dict):
    sys.path.insert(0, str(REFERENCE))
    try:
        raise NotImplementedError(f"请为 '{module}' 实现 run_reference()")
    finally:
        if str(REFERENCE) in sys.path:
            sys.path.remove(str(REFERENCE))
# ──────────────────────────────────────────────────────────────────

def generate(module: str):
    print(f"\n── Fixture: {module} ──")
    inputs = prepare_inputs(module)
    (FIXTURES / f"reference_{module}_input.pkl").write_bytes(pickle.dumps(inputs))
    output = run_reference(module, inputs)
    (FIXTURES / f"reference_{module}_output.pkl").write_bytes(pickle.dumps(output))
    print(f"✅ 已保存 reference_{module}_*.pkl")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--module")
    p.add_argument("--all", action="store_true")
    args = p.parse_args()
    if args.all:
        for m in get_modules(): generate(m)
    elif args.module:
        generate(args.module)
    else:
        p.print_help()
