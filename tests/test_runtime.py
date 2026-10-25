"""Playback, evidence provenance, observed outcomes and reset contracts."""

import unittest
from runtime import Runtime
import engine


class RuntimeTests(unittest.TestCase):
    def incident(self, steps=12):
        r = Runtime()
        r.control(paused=True)
        r.scenario("payment")
        for _ in range(steps):
            r.step()
        return r

    def test_pause_prevents_background_advance_and_step_is_exact(self):
        r = Runtime()
        r.control(paused=True)
        self.assertFalse(r.advance())
        self.assertEqual(r.sim.tick_no, 0)
        r.step()
        self.assertEqual(r.sim.tick_no, 1)
        r.control(paused=False)
        with self.assertRaises(ValueError):
            r.step()

    def test_speed_is_wall_clock_only_and_scenario_preserves_playback(self):
        r = Runtime()
        r.control(paused=True, speed=4)
        r.scenario("payment")
        self.assertTrue(r.paused)
        self.assertEqual(r.speed, 4)
        self.assertEqual(r.sim.tick_no, 0)
        for _ in range(5):
            r.step()
        self.assertEqual(r.state()["tick_seconds"], 2)
        self.assertEqual(r.state()["playback"]["wall_tick_seconds"], 0.5)
        for speed in (0, 3, True):
            with self.assertRaises(ValueError):
                r.control(speed=speed)

    def test_incident_origin_is_inferred_then_retained(self):
        r = self.incident(0)
        self.assertIsNone(r.incident["initial_origin"])
        for _ in range(12):
            r.step()
        self.assertEqual(r.incident["initial_origin"], "payment-db")
        self.assertGreater(r.incident["detected_tick"], r.incident["start_tick"])
        r.fix("payment-db", "failover")
        for _ in range(35):
            r.step()
        self.assertEqual(r.incident["initial_origin"], "payment-db")
        self.assertEqual(r.incident["phase"], "resolved")
        self.assertGreater(r.state()["incident"]["recovery_s"], 0)

    def test_lead_time_requires_warning_while_healthy_before_observed_failure(self):
        r = self.incident(25)
        leads = r.state()["incident"]["verified_leads"]
        self.assertTrue(
            any(p["service"] == "payment-service" and p["lead_s"] > 0 for p in leads)
        )
        for name, failure in r.incident["failures"].items():
            warning = r.incident["warnings"].get(name)
            if warning:
                self.assertLess(warning["tick"], failure["tick"])

    def test_saved_forecast_matches_observed_same_model_outcome(self):
        r = self.incident(8)
        r.fix("payment-db", "failover")
        for _ in range(engine.HORIZON):
            r.step()
        d = r.state()["last_decision"]
        self.assertEqual(d["status"], "complete")
        self.assertEqual(len(d["observed"]), 20)
        self.assertEqual(d["mean_absolute_error"], 0)

    def test_second_fault_invalidates_pending_forecast(self):
        r = self.incident(8)
        r.fix("payment-db", "failover")
        r.step()
        r.inject("redis-cache", severity=0.13)
        self.assertEqual(r.last_decision["status"], "interrupted")
        self.assertIsNone(r.last_decision["mean_absolute_error"])

    def test_fix_refreshes_health_classification_without_a_tick(self):
        r = self.incident(12)
        self.assertEqual(r.sim.services["payment-db"].state, "failed")
        tick = r.sim.tick_no
        r.fix("payment-db", "failover")
        self.assertEqual(r.sim.tick_no, tick)
        self.assertEqual(r.sim.services["payment-db"].state, "degraded")
        self.assertTrue(r.paused)

    def test_reset_changes_world_and_discards_stale_reports_and_playback(self):
        r = self.incident()
        world = r.world_id
        r.control(speed=4)
        r.reset()
        self.assertNotEqual(world, r.world_id)
        self.assertIsNone(r.incident)
        self.assertIsNone(r.last_decision)
        self.assertFalse(r.paused)
        self.assertEqual(r.speed, 1)
        self.assertEqual(r.state()["analysis"]["system_risk"], 0)

    def test_telemetry_contains_cpu_and_only_real_ticks_count_as_observed(self):
        r = Runtime()
        r.control(paused=True)
        r.step()
        h = r.state()["services"]["payment-db"]["history"]
        observed = [s for s in h if s["tick"] >= 0]
        self.assertEqual(len(observed), 1)
        self.assertIn("cpu", observed[0])
        self.assertIn("mem", observed[0])

    def test_trajectory_end_and_mean_match_strategy_summary(self):
        r = self.incident(8)
        a = r.state()["analysis"]
        for recommendation in a["recommendations"]:
            points = recommendation["trajectory"]
            self.assertEqual(points[0]["seconds"], 0)
            self.assertEqual(points[-1]["seconds"], 40)
            self.assertAlmostEqual(
                points[-1]["risk"], recommendation["end_risk"], delta=0.051
            )
            self.assertAlmostEqual(
                sum(p["risk"] for p in points[1:]) / 20,
                recommendation["projected_risk"],
                delta=0.051,
            )


if __name__ == "__main__":
    unittest.main()
