"""Deterministic checks of causal behavior, recovery parity and forecast isolation."""

import copy
import unittest
from simulator import Simulator, TOPOLOGY
import engine


class EngineTests(unittest.TestCase):
    def incident(self, target="payment-db", ticks=7, seed=42):
        s = Simulator(seed=seed)
        s.inject_chaos(target, 0.13)
        for _ in range(ticks):
            s.tick()
        return s

    def test_nominal_does_not_alert_over_long_run(self):
        s = Simulator(seed=42)
        for _ in range(150):
            s.tick()
        a = engine.analyze(s)
        self.assertIsNone(a["root_cause"])
        self.assertEqual(a["predictions"], [])
        self.assertEqual(a["system_risk"], 0)

    def test_root_cause_generalizes_across_all_services_and_seeds(self):
        for seed in [7, 42, 99]:
            for target in TOPOLOGY:
                with self.subTest(seed=seed, target=target):
                    s = self.incident(target, seed=seed)
                    _, own = engine.cascade_risk(s.services, s.tick_no)
                    self.assertEqual(
                        engine.root_cause(s.services, own)["service"], target
                    )

    def test_forecast_predicts_still_healthy_caller_before_failure(self):
        s = self.incident(ticks=4)
        risk, _ = engine.cascade_risk(s.services, s.tick_no)
        predictions = engine.predict_next_failures(s.services, risk)
        self.assertTrue(
            any(
                p["service"] == "payment-service" and p["state"] == "healthy"
                for p in predictions
            )
        )
        for _ in range(30):
            s.tick()
        self.assertEqual(s.services["payment-service"].state, "failed")

    def test_counterfactuals_do_not_mutate_live_state_or_random_stream(self):
        s = self.incident()
        before = s.snapshot()
        rng = s.rng.getstate()
        first = engine.recommend_strategies(s, "payment-db")
        self.assertEqual(first, engine.recommend_strategies(s, "payment-db"))
        self.assertEqual(before, s.snapshot())
        self.assertEqual(rng, s.rng.getstate())
        self.assertEqual(len(first[0]), 5)

    def test_counterfactual_matches_actual_simulator_action(self):
        s = self.incident()
        for name in engine.STRATEGIES:
            with self.subTest(strategy=name):
                trial = copy.deepcopy(s)
                trial.apply_fix("payment-db", name)
                risks = []
                for _ in range(engine.HORIZON):
                    trial.tick()
                    risks.append(engine.operational_risk(trial))
                mean, end = engine.forecast(s, "payment-db", name)
                self.assertAlmostEqual(mean, sum(risks) / len(risks))
                self.assertAlmostEqual(end, risks[-1])

    def test_best_recovery_clears_fault_and_recovers_entire_chain(self):
        s = self.incident(ticks=15)
        recs, _ = engine.recommend_strategies(s, "payment-db")
        s.apply_fix("payment-db", recs[0]["strategy"])
        for _ in range(100):
            s.tick()
        self.assertTrue(all(x.health == 1 for x in s.services.values()))
        self.assertIsNone(engine.analyze(s)["root_cause"])

    def test_demo_recovery_reaches_healthy_callers_within_one_minute(self):
        s = self.incident(ticks=12)
        s.apply_fix("payment-db", "failover")
        for _ in range(30):
            s.tick()
        self.assertTrue(all(x.state == "healthy" for x in s.services.values()))

    def test_circuit_breaker_protects_caller_and_expires(self):
        s = self.incident(ticks=10)
        s.services["payment-service"].health = 1
        s.apply_fix("payment-db", "circuit_breaker")
        for _ in range(10):
            s.tick()
        self.assertEqual(s.services["payment-service"].health, 1)
        self.assertLess(s.services["payment-db"].health, 0.7)
        for _ in range(15):
            s.tick()
        self.assertLess(s.services["payment-service"].health, 1)

    def test_reset_restores_reference_and_clears_incident(self):
        s = self.incident()
        s.reset(seed=42)
        self.assertEqual(s.tick_no, 0)
        self.assertFalse(s.events)
        self.assertTrue(all(len(x.history) == 24 for x in s.services.values()))
        self.assertEqual(engine.analyze(s)["system_risk"], 0)

    def test_reject_unknown_strategy_without_mutation(self):
        s = self.incident()
        before = s.snapshot()
        with self.assertRaises(ValueError):
            s.apply_fix("payment-db", "magic")
        self.assertEqual(before, s.snapshot())


if __name__ == "__main__":
    unittest.main()
