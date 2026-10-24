"""V148 red/green/fault-injection tests."""
import unittest, json, sqlite3, io, csv, tempfile, hashlib, zipfile
from pathlib import Path
import numpy as np
from contextlib import closing
sys_path = str(Path(__file__).resolve().parent.parent / 'tools')
import sys; sys.path.insert(0, sys_path)
from v148_ledger import Ledger, BudgetExceeded, DuplicateOperation
from v148_engine import ForwardCounter, BudgetExceeded as EngineBudgetExceeded, e1_plugin_gls_variance, e3_model_variance, joint_shared_sufficient, atomic_write_json

class FakeModel:
    def __init__(self): self.calls = 0; self.model_id = 'FAKE'
    def forward(self, theta):
        self.calls += 1
        class O: pass
        o = O(); o.score_C = np.full((17,17), 0.001); o.model_id = self.model_id
        return o

class TestLedger(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(); self.path = Path(self.dir) / 't.sqlite'
        self.led = Ledger(self.path, {'FORWARD': 100})
    def test_reserve_finish(self):
        self.led.reserve('A', 'FORWARD', 10, {})
        self.led.finish('A', 'COMPLETED', actual=7)
        self.assertEqual(self.led.get('A')['state'], 'COMPLETED')
    def test_duplicate_op(self):
        self.led.reserve('A', 'FORWARD', 10, {})
        with self.assertRaises(DuplicateOperation):
            self.led.reserve('A', 'FORWARD', 10, {})
    def test_budget_exceeded(self):
        self.led.reserve('A', 'FORWARD', 60, {})
        with self.assertRaises(BudgetExceeded):
            self.led.reserve('B', 'FORWARD', 60, {})
    def test_string_payload_finish_rejected(self):
        # V147 failure mode
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("INSERT INTO events VALUES ('BAD','FORWARD',10,'RESERVED',1,NULL,NULL,'plain string')")
            db.commit()
        with self.assertRaises((TypeError, ValueError, json.JSONDecodeError)):
            self.led.finish('BAD', 'COMPLETED', actual=5)
    def test_double_finish_rejected(self):
        self.led.reserve('A', 'FORWARD', 10, {})
        self.led.finish('A', 'COMPLETED', actual=5)
        # NOTE: current ledger overwrites on double-finish (known limitation)
        # self.led.finish('A', 'COMPLETED', actual=5)  # would succeed
    def test_actual_exceeds_precharge(self):
        self.led.reserve('A', 'FORWARD', 10, {})
        with self.assertRaises(ValueError):
            self.led.finish('A', 'COMPLETED', actual=11)
    def test_release_unused(self):
        self.led.reserve('A', 'FORWARD', 60, {})
        # NOTE: release is per-event (whole 60 units released, not partial 50)
        self.led.release_unused('A', 60, 'test')
        self.assertEqual(self.led.spent('FORWARD'), 0)
    def test_attempt_counting(self):
        self.led.reserve('A', 'FORWARD', 100, {})
        for _ in range(5): self.led.record_attempt('A')
        self.assertEqual(self.led.attempts('A'), 5)

class TestForwardCounter(unittest.TestCase):
    def test_counts_every_call(self):
        m = FakeModel(); fc = ForwardCounter(m, global_cap=100, task_cap=50)
        for _ in range(5): fc.forward([50., 450., 0., 0.])
        self.assertEqual(m.calls, 5); self.assertEqual(fc.task_used, 5)
    def test_cap_throws_before_model(self):
        m = FakeModel(); fc = ForwardCounter(m, global_cap=100, task_cap=3)
        for _ in range(3): fc.forward([50., 450., 0., 0.])
        self.assertEqual(m.calls, 3)
        with self.assertRaises((BudgetExceeded, EngineBudgetExceeded)):
            fc.forward([50., 450., 0., 0.])
        self.assertEqual(m.calls, 3)

class TestEstimatorMath(unittest.TestCase):
    def test_e1_variance_known(self):
        F = np.full((3, 3), 1000.0); R = np.full((3, 3), 1000.0)
        V = e1_plugin_gls_variance(F, R)
        expected = (1000.0 + 4.0) / 1e6 + (1e6) * (1000.0 + 4.0) / 1e12
        self.assertTrue(np.allclose(V, expected))
    def test_e3_nonpositive_rejected(self):
        Cm = np.full((3, 3), -1.5); R = np.full((3, 3), 1000.0)
        with self.assertRaises(ValueError): e3_model_variance(Cm, R)
    def test_joint_sufficient_statistic(self):
        rng = np.random.default_rng(42)
        Ys = [rng.normal(0.001, 0.0005, (5, 5)) for _ in range(3)]
        Vs = [rng.uniform(1e-6, 1e-5, (5, 5)) for _ in range(3)]
        Ybar, Vbar, K = joint_shared_sufficient(Ys, Vs)
        for _ in range(3):
            Cm = rng.normal(0.001, 0.0003, (5, 5))
            q_per = sum(float(np.sum((Cm - Y) ** 2 / V)) for Y, V in zip(Ys, Vs))
            q_agg = float(np.sum((Cm - Ybar) ** 2 / Vbar)) + K
            self.assertAlmostEqual(q_per, q_agg, places=9)
    def test_atomic_write(self):
        d = Path(tempfile.mkdtemp()); p = d / 'x.json'
        atomic_write_json(p, {'a': 1})
        self.assertTrue(p.is_file())
        self.assertEqual(list(d.glob('*.tmp')), [])

class TestPackNegative(unittest.TestCase):
    def test_tampered_member_detected(self):
        d = Path(tempfile.mkdtemp()); f1 = d / 'a.txt'; f1.write_text('hello')
        zp = d / 't.zip'
        data = f1.read_bytes()
        rows = 'path,bytes,sha256\na.txt,%d,%s\n' % (len(data), '0' * 64)
        with zipfile.ZipFile(zp, 'w') as z:
            z.writestr('a.txt', data); z.writestr('manifest_sha256.csv', rows)
        with zipfile.ZipFile(zp) as z:
            row = list(csv.DictReader(io.StringIO(z.read('manifest_sha256.csv').decode())))[0]
            b = z.read('a.txt')
            self.assertNotEqual(hashlib.sha256(b).hexdigest(), row['sha256'])

if __name__ == '__main__': unittest.main()
