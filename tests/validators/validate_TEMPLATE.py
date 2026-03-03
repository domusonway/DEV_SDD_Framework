"""
tests/validators/validate_TEMPLATE.py
复制此文件: cp validate_TEMPLATE.py validate_<module>.py
替换下方三个占位符，其余不改。
"""
import pickle, sys, numpy as np
from pathlib import Path

MODULE_NAME   = "<module_name>"
IMPL_MODULE   = "modules.<module_name>"
IMPL_FUNCTION = "<function_name>"

FIXTURES = Path(__file__).parent.parent / "fixtures"
TOL = dict(rtol=1e-5, atol=1e-7)

def compare(actual, expected, path="root"):
    errs = []
    if isinstance(expected, np.ndarray):
        if actual.shape != expected.shape:
            errs.append(f"shape mismatch @ {path}: {actual.shape} vs {expected.shape}")
        else:
            try: np.testing.assert_allclose(actual, expected, **TOL)
            except AssertionError:
                diff = np.max(np.abs(actual - expected))
                errs.append(f"value diff @ {path}: max_abs={diff:.2e}")
    elif isinstance(expected, dict):
        for k in expected:
            errs += compare(actual.get(k), expected[k], f"{path}.{k}")
    elif isinstance(expected, (list, tuple)):
        for i,(a,e) in enumerate(zip(actual,expected)):
            errs += compare(a, e, f"{path}[{i}]")
    else:
        if actual != expected: errs.append(f"mismatch @ {path}: {actual!r} != {expected!r}")
    return errs

def main():
    print(f"{'='*50}\n校验器: {MODULE_NAME}\n{'='*50}")
    ref_in  = pickle.loads((FIXTURES/f"reference_{MODULE_NAME}_input.pkl").read_bytes())
    ref_out = pickle.loads((FIXTURES/f"reference_{MODULE_NAME}_output.pkl").read_bytes())

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    import importlib
    mod = importlib.import_module(IMPL_MODULE)
    actual = getattr(mod, IMPL_FUNCTION)(**ref_in)

    errs = compare(actual, ref_out)
    if not errs:
        print(f"✅ 通过（rtol={TOL['rtol']:.0e}）")
        sys.exit(0)
    else:
        print(f"❌ 失败 {len(errs)} 处:")
        for e in errs: print(f"  • {e}")
        print("→ 修改实现代码，不要降低容差")
        sys.exit(1)

if __name__ == "__main__": main()
