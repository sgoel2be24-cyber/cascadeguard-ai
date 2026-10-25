"""Rubric-critical behavior: causal comparisons, action diversity and policy enforcement."""

import copy
import unittest
import engine
from runtime import Runtime, PolicyViolation
from evaluation import run_suite, load_evidence


class PlannerTests(unittest.TestCase):
    def incident(self, scenario="payment", steps=8):
        r = Runtime()
        r.control(paused=True)
        r.scenario(scenario)
        for _ in range(steps):
            r.step()
        return r

    def test_mechanisms_produce_distinct_computed_recoveries(self):
        expected = {
            "payment": "failover",
            "cache": "scale_out",
            "search": "rollback",
            "network": "circuit_breaker",
        }
        for scenario, strategy in expected.items():
            with self.subTest(scenario=scenario):
                r = self.incident(scenario)
                recs = r.state()["analysis"]["recommendations"]
                self.assertEqual(recs[0]["strategy"], strategy)
                self.assertTrue(recs[0]["eligible"])
                self.assertGreater(recs[0]["risk_reduction"], 0)

    def test_no_standby_excludes_failover_and_blocks_execution_without_mutation(self):
        r = self.incident()
        r.set_policy(standby_available=False)
        recs = r.state()["analysis"]["recommendations"]
        row = next(x for x in recs if x["strategy"] == "failover")
        self.assertFalse(row["eligible"])
        before = r.sim.snapshot()
        rng = r.sim.rng.getstate()
        with self.assertRaises(PolicyViolation):
            r.fix("payment-db", "failover")
        self.assertEqual(r.sim.snapshot(), before)
        self.assertEqual(r.sim.rng.getstate(), rng)

    def test_zero_downtime_budget_ranks_only_feasible_options_first(self):
        r = self.incident()
        r.set_policy(max_downtime_s=0)
        recs = r.state()["analysis"]["recommendations"]
        self.assertEqual(
            {x["strategy"] for x in recs if x["eligible"]},
            {"scale_out", "circuit_breaker"},
        )
        self.assertTrue(recs[0]["eligible"])
        with self.assertRaises(PolicyViolation):
            r.fix("payment-db", "restart")

    def test_policy_and_guard_survive_scenario_but_reset_disarms(self):
        r = Runtime()
        r.set_policy(max_downtime_s=10, standby_available=False)
        r.set_guard(True)
        r.scenario("search")
        self.assertEqual(r.policy, {"max_downtime_s": 10, "standby_available": False})
        self.assertTrue(r.guard_enabled)
        r.reset()
        self.assertFalse(r.guard_enabled)
        self.assertEqual(r.policy["max_downtime_s"], 60)

    def test_invalid_partial_policy_cannot_partially_change_valid_values(self):
        r = Runtime()
        before = dict(r.policy)
        for kwargs in [
            {"max_downtime_s": True},
            {"max_downtime_s": -1},
            {"max_downtime_s": 121},
            {"max_downtime_s": 0, "standby_available": "false"},
        ]:
            with self.assertRaises(ValueError):
                r.set_policy(**kwargs)
            self.assertEqual(r.policy, before)

    def test_physics_noise_stays_paired_across_action_and_log_branches(self):
        r = self.incident()
        left = copy.deepcopy(r.sim)
        right = copy.deepcopy(r.sim)
        left.apply_fix("payment-db", "failover")
        right.apply_fix("payment-db", "rollback")
        for _ in range(20):
            left.tick()
            right.tick()
            self.assertEqual(left.rng.getstate(), right.rng.getstate())
            self.assertEqual(
                left.services["user-db"].latency, right.services["user-db"].latency
            )
        self.assertNotEqual(left.log_rng.getstate(), right.log_rng.getstate())

    def test_fault_type_metadata_does_not_leak_into_origin_detection(self):
        r = self.incident()
        risk, own = engine.cascade_risk(r.sim.services, r.sim.tick_no)
        origin = engine.root_cause(r.sim.services, own)
        r.sim.services["payment-db"].fault_kind = "network"
        new_risk, new_own = engine.cascade_risk(r.sim.services, r.sim.tick_no)
        self.assertEqual(risk, new_risk)
        self.assertEqual(origin, engine.root_cause(r.sim.services, new_own))

    def test_armed_guard_acts_before_gateway_failure(self):
        r = Runtime()
        r.control(paused=True)
        r.set_guard(True)
        r.scenario("payment")
        for _ in range(35):
            r.step()
            self.assertNotEqual(r.sim.services["api-gateway"].state, "failed")
        self.assertEqual(r.incident["actions"][0]["initiated_by"], "guard")
        self.assertEqual(r.incident["actions"][0]["strategy"], "failover")
        self.assertEqual(r.incident["phase"], "resolved")

    def test_guard_honors_zero_downtime_and_missing_standby(self):
        r = Runtime()
        r.control(paused=True)
        r.set_policy(max_downtime_s=0, standby_available=False)
        r.set_guard(True)
        r.scenario("payment")
        for _ in range(12):
            r.step()
        self.assertTrue(r.incident["actions"])
        self.assertTrue(
            all(
                engine.STRATEGIES[a["strategy"]]["downtime_s"] == 0
                for a in r.incident["actions"]
            )
        )
        self.assertFalse(
            any(a["strategy"] == "failover" for a in r.incident["actions"])
        )

    def test_guard_replans_when_network_containment_expires(self):
        r = Runtime(seed=203)
        r.control(paused=True)
        r.set_guard(True)
        r.scenario("network")
        for _ in range(70):
            r.step()
            self.assertNotEqual(r.sim.services["api-gateway"].state, "failed")
        self.assertGreaterEqual(len(r.incident["actions"]), 2)

    def test_profile_effects_repair_only_the_modeled_cause(self):
        r = self.incident("search")
        s = r.sim.services["elastic-cluster"]
        r.sim.apply_fix("elastic-cluster", "failover")
        self.assertIsNotNone(s.fault)
        r.sim.apply_fix("elastic-cluster", "rollback")
        self.assertIsNone(s.fault)
        r = self.incident("network")
        r.sim.apply_fix("message-queue", "circuit_breaker")
        self.assertIsNotNone(r.sim.services["message-queue"].fault)
        self.assertGreater(
            r.sim.services["message-queue"].isolated_until, r.sim.tick_no
        )

    def test_paired_evaluation_includes_containment_cost_and_one_shot_control(self):
        live = self.incident()
        before = live.sim.snapshot()
        rng = live.sim.rng.getstate()
        result = run_suite(seeds=(203,), scenarios=("network",))
        case = result["cases"][0]["arms"]
        self.assertLess(
            case["predictive"]["gateway_failed_s"],
            case["single_action"]["gateway_failed_s"],
        )
        self.assertGreater(case["predictive"]["isolation_service_s"], 0)
        self.assertGreaterEqual(
            case["predictive"]["service_unavailable_s"],
            case["predictive"]["service_failed_s"],
        )
        self.assertEqual(before, live.sim.snapshot())
        self.assertEqual(rng, live.sim.rng.getstate())
        saved = load_evidence()
        self.assertEqual(saved["status"], "current")
        self.assertEqual(saved["summary"]["case_count"], 40)
        self.assertNotIn(saved["method"]["design_seed"], saved["method"]["seeds"])


if __name__ == "__main__":
    unittest.main()
