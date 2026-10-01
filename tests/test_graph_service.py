import unittest
import os
import time
from unittest.mock import patch
from app.graph_service import _build_sparse_location_graph, compatibility_order_data
from app.matching_service import assign_donors
from app.routes import (get_assignments, get_compatibility_order, get_hospitals,
                        get_blood_banks, get_blood_bank_inventory, get_network,
                        search as search_donors)
from app.utils import haversine_distance
from config import ProductionConfig
from flask import session
from app.routes import get_network, network_page
from app import create_app, db
from app.graph_service import BLOOD_GROUPS, _dijkstra, build_network_data, compatibility_adjacency
from app.models import BloodRequest, BloodBank, BloodInventory, Donor, Hospital, User


class GraphMatchingTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        seeker = User(name="Requester", email="requester@example.test", password_hash="x", phone="1111111111", role="seeker", age=30)
        donor_user = User(name="Verified Donor", email="donor@example.test", password_hash="x", phone="2222222222", role="donor", age=30, is_verified=True)
        db.session.add_all([seeker, donor_user])
        db.session.flush()
        self.seeker = seeker
        self.donor = Donor(user_id=donor_user.user_id, blood_group="O-", latitude=12.01, longitude=77.01, city="Nearby", is_available=True, donation_count=2)
        self.request = BloodRequest(requester_id=seeker.user_id, blood_group="A+", urgency_level="critical", location="City Hospital", latitude=12.0, longitude=77.0, status="active")
        db.session.add_all([self.donor, self.request])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_directed_compatibility_adjacency(self):
        graph = compatibility_adjacency()
        self.assertEqual(set(graph), set(BLOOD_GROUPS))
        self.assertIn("A+", graph["O-"])
        self.assertNotIn("O-", graph["A+"])

    def test_bfs_match_and_dijkstra_route(self):
        result = build_network_data(self.request, donors=[self.donor])
        self.assertEqual([m["donor_id"] for m in result["donors"]], [self.donor.donor_id])
        match = result["donors"][0]
        self.assertTrue(match["route_available"])
        self.assertGreater(match["route_distance_km"], 0)
        self.assertEqual(len(match["route_labels"]), 4)
        self.assertTrue(match["is_verified"])
        self.assertEqual(match["donation_count"], 2)
        self.assertIn("O-", result["bfs_order"])

    def test_network_payload_propagates_rank_score_distance_and_match_level(self):
        result = build_network_data(self.request, donors=[self.donor])
        self.assertEqual(len(result["donors"]), 1)
        match = result["donors"][0]
        self.assertEqual(match["donor_id"], self.donor.donor_id)
        self.assertEqual(match["rank"], 1)
        self.assertEqual(match["match_level"], 2)
        self.assertEqual(match["blood_match"], "Compatible")
        self.assertEqual(match["distance_km"], match["route_distance_km"])
        self.assertTrue(0 <= match["ai_score"] <= 1)
        self.assertIn("Compatible blood group (Level 2)", match["why_recommended"])

        node = next(item for item in result["nodes"] if item.get("type") == "donor")
        self.assertEqual(node["donor_id"], self.donor.donor_id)
        self.assertEqual(node["rank"], match["rank"])
        self.assertEqual(node["ai_score"], match["ai_score"])
        self.assertEqual(node["distance_km"], match["distance_km"])
        self.assertEqual(node["match_level"], match["match_level"])

    def test_duplicate_donor_records_render_once_by_donor_id(self):
        result = build_network_data(self.request, donors=[self.donor, self.donor])
        self.assertEqual([item["donor_id"] for item in result["donors"]],
                         [self.donor.donor_id])
        donor_nodes = [item for item in result["nodes"]
                       if item.get("type") == "donor" and item.get("donor_id") == self.donor.donor_id]
        donor_edges = [edge for edge in result["edges"]
                       if edge["type"] == "compatible_donor"
                       and edge["source"] == f"donor:{self.donor.donor_id}"]
        self.assertEqual(len(donor_nodes), 1)
        self.assertEqual(len(donor_edges), 1)

    def test_network_score_uses_its_dijkstra_distance(self):
        match = build_network_data(self.request, donors=[self.donor])["donors"][0]
        distance = match["distance_km"]
        reliability = match["reliability_score"]
        expected = round(0.60 * (1 - min(distance / 50, 1))
                         + 0.20 * (reliability / 100), 4)
        self.assertEqual(match["distance_km"], match["route_distance_km"])
        self.assertEqual(match["ai_score"], expected)

    def test_search_and_network_share_rank_score_distance_and_donor_id(self):
        near_compatible = self._make_donor(
            "Near A negative", "A-", 12.001, 77.0, verified=False
        )
        farther_exact = self._make_donor(
            "Far A positive", "A+", 12.08, 77.0, verified=False
        )
        db.session.commit()
        search_payload = {
            "blood_group": self.request.blood_group,
            "latitude": self.request.latitude,
            "longitude": self.request.longitude,
            "radius_km": 1,
            "urgency": 3,
        }
        with self.app.test_request_context("/api/search", method="POST", json=search_payload):
            search_response, search_status = search_donors()
        self.assertEqual(search_status, 200)
        search_matches = search_response.get_json()["donors"]

        with self.app.test_request_context(f"/api/network?request_id={self.request.request_id}"):
            session["user_id"] = self.seeker.user_id
            network_response, network_status = get_network()
        self.assertEqual(network_status, 200)
        network_matches = {item["donor_id"]: item for item in network_response.get_json()["donors"]}

        # The farther exact match ranks first globally; radius filtering leaves a
        # lower global rank on Search, which must still match Network for that ID.
        self.assertGreater(network_matches[farther_exact.donor_id]["distance_km"], 1)
        self.assertEqual(len(search_matches), 1)
        search_match = search_matches[0]
        self.assertEqual(search_match["donor_id"], near_compatible.donor_id)
        network_match = network_matches[near_compatible.donor_id]
        for field in ("donor_id", "rank", "ai_score", "distance_km", "reliability_score", "match_level"):
            self.assertEqual(search_match[field], network_match[field], field)
        self.assertGreater(search_match["rank"], 1)
        self.assertTrue(0 <= search_match["ai_score"] <= 1)

    def test_network_routes_require_login_and_scope_requests(self):
        with self.app.test_request_context("/network"):
            self.assertEqual(network_page().status_code, 302)
        with self.app.test_request_context("/api/network"):
            self.assertEqual(get_network()[1], 401)
        with self.app.test_request_context("/api/assign"):
            self.assertEqual(get_assignments()[1], 401)
        other = User(name="Other", email="other@example.test", password_hash="x",
                     phone="3333333333", role="seeker", age=30)
        db.session.add(other)
        db.session.flush()
        private_request = BloodRequest(requester_id=other.user_id, blood_group="B+",
                                      status="active", location="Private location")
        db.session.add(private_request)
        db.session.commit()
        with self.app.test_request_context("/network"):
            session["user_id"] = self.seeker.user_id
            self.assertIn("BloodLink Network", network_page())
        with self.app.test_request_context(f"/api/network?request_id={self.request.request_id}"):
            session["user_id"] = self.seeker.user_id
            self.assertEqual(get_network()[1], 200)
        with self.app.test_request_context(f"/api/network?request_id={private_request.request_id}"):
            session["user_id"] = self.seeker.user_id
            self.assertEqual(get_network()[1], 404)

    def test_dijkstra_returns_shortest_weighted_route(self):
        graph = {"start": [("far", 8), ("near", 2)], "near": [("far", 1), ("end", 7)],
                 "far": [("end", 1)], "end": []}
        distance, path = _dijkstra(graph, "start", "end")
        self.assertEqual(distance, 4)
        self.assertEqual(path, ["start", "near", "far", "end"])

    def test_unavailable_donor_is_excluded(self):
        self.donor.is_available = False
        db.session.commit()
        self.assertEqual(build_network_data(self.request, donors=[self.donor])["donors"], [])


    def _make_donor(self, name, group, latitude, longitude, verified=False):
        user = User(name=name, email=name.lower().replace(" ", ".") + "@example.test",
                    password_hash="x", phone="4444444444", role="donor",
                    age=30, is_verified=verified)
        db.session.add(user)
        db.session.flush()
        donor = Donor(user_id=user.user_id, blood_group=group, latitude=latitude,
                      longitude=longitude, city=name, is_available=True, donation_count=0)
        db.session.add(donor)
        db.session.flush()
        return donor

    def test_all_64_blood_group_pairs_follow_existing_abo_rh_rules(self):
        graph = compatibility_adjacency()
        for donor in BLOOD_GROUPS:
            for recipient in BLOOD_GROUPS:
                donor_abo, donor_rh = donor[:-1], donor[-1]
                recipient_abo, recipient_rh = recipient[:-1], recipient[-1]
                abo_ok = donor_abo == "O" or donor_abo == recipient_abo or recipient_abo == "AB"
                rh_ok = donor_rh == "-" or recipient_rh == "+"
                self.assertEqual(recipient in graph[donor], abo_ok and rh_ok,
                                 f"{donor} -> {recipient}")

    def test_hasse_order_properties_and_cover_edges(self):
        result = compatibility_order_data()
        self.assertTrue(result["reflexive"])
        self.assertTrue(result["antisymmetric"])
        self.assertTrue(result["transitive"])
        self.assertTrue(result["is_partial_order"])
        self.assertEqual(result["minimal_element"], "O-")
        self.assertEqual(result["maximal_element"], "AB+")
        self.assertEqual(len(result["cover_edges"]), 12)

    def test_bfs_match_levels_for_a_positive_request(self):
        donors = [
            self._make_donor("Level A+", "A+", 12.001, 77.0),
            self._make_donor("Level A-", "A-", 12.002, 77.0),
            self._make_donor("Level O+", "O+", 12.003, 77.0),
            self._make_donor("Level O-", "O-", 12.004, 77.0),
        ]
        result = build_network_data(self.request, donors=donors)
        levels = {item["blood_group"]: item["match_level"] for item in result["donors"]}
        self.assertEqual(levels, {"A+": 0, "A-": 1, "O+": 1, "O-": 2})

    def test_sparse_graph_bridges_disconnected_components(self):
        locations = [("west-a", 0.0, 0.0), ("west-b", 0.0, 0.001),
                     ("east-a", 0.0, 1.0), ("east-b", 0.0, 1.001)]
        graph = _build_sparse_location_graph(locations, k=0)
        seen = {"west-a"}
        queue = ["west-a"]
        while queue:
            for neighbor, _ in graph[queue.pop()]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        self.assertEqual(seen, {item[0] for item in locations})
        self.assertTrue(all(
            any(other == node for other, _ in graph[neighbor])
            for node, neighbors in graph.items() for neighbor, _ in neighbors
        ))

    def test_sparse_graph_uses_intermediate_route_against_costlier_direct_edge(self):
        locations = [(f"p{i}", 0.0, i * 0.01) for i in range(5)]
        graph = _build_sparse_location_graph(locations, k=3)
        self.assertNotIn("p4", dict(graph["p0"]))
        direct = haversine_distance(0.0, 0.0, 0.0, 0.04)
        # A more expensive direct graph edge is a competing path; Dijkstra selects the
        # lower-weight intermediate route. Production edge weights remain Haversine.
        graph["p0"].append(("p4", direct * 2))
        graph["p4"].append(("p0", direct * 2))
        distance, path = _dijkstra(graph, "p0", "p4")
        self.assertGreater(len(path), 2)
        self.assertLess(distance, direct * 2)
        self.assertGreaterEqual(distance, direct - 0.001)

    def test_urgency_weights_change_normalized_donor_order(self):
        near = self._make_donor("Near A negative", "A-", 12.009, 77.0, verified=False)
        far = self._make_donor("Far A positive", "A+", 12.53, 77.0, verified=True)
        self.request.urgency_level = "critical"
        critical = build_network_data(self.request, donors=[near, far])["donors"]
        self.assertEqual(critical[0]["donor_id"], near.donor_id)
        self.assertTrue(all(0 <= item["ai_score"] <= 1 for item in critical))
        self.request.urgency_level = "urgent"
        urgent = build_network_data(self.request, donors=[near, far])["donors"]
        self.assertEqual(urgent[0]["donor_id"], near.donor_id)
        self.assertTrue(all(0 <= item["ai_score"] <= 1 for item in urgent))
        self.request.urgency_level = "normal"
        normal = build_network_data(self.request, donors=[near, far])["donors"]
        self.assertEqual(normal[0]["donor_id"], far.donor_id)
        self.assertTrue(all(0 <= item["ai_score"] <= 1 for item in normal))

    def test_missing_coordinates_score_none_and_sort_last(self):
        near = self._make_donor("Located A positive", "A+", 12.01, 77.0)
        missing = self._make_donor("Unlocated O negative", "O-", None, None)
        result = build_network_data(self.request, donors=[missing, near])["donors"]
        self.assertEqual(result[-1]["donor_id"], missing.donor_id)
        self.assertIsNone(result[-1]["ai_score"])

    def test_global_assignment_and_hall_explanation(self):
        other_user = User(name="Second Requester", email="second@example.test",
                          password_hash="x", phone="5555555555", role="seeker", age=30)
        db.session.add(other_user)
        db.session.flush()
        other_request = BloodRequest(requester_id=other_user.user_id, blood_group="B+",
                                     urgency_level="normal", status="active")
        db.session.add(other_request)
        db.session.commit()
        result = assign_donors([self.request, other_request], [self.donor])
        self.assertEqual(len(result["assignments"]), 1)
        self.assertEqual(result["assignments"][0]["request"].request_id, self.request.request_id)
        self.assertEqual(len(result["unmatched_requests"]), 1)
        unmatched = result["unmatched_requests"][0]
        self.assertEqual(unmatched["request"].request_id, other_request.request_id)
        self.assertIn("Hall's condition", unmatched["hall_explanation"])
        self.assertEqual(len(unmatched["hall_request_ids"]), 2)
        self.assertEqual(len(unmatched["hall_donor_ids"]), 1)

    def test_assignment_api_scopes_users_and_hides_donor_identity(self):
        other_user = User(name="Private Requester", email="private@example.test",
                          password_hash="x", phone="6666666666", role="seeker", age=30)
        db.session.add(other_user)
        db.session.flush()
        other_request = BloodRequest(requester_id=other_user.user_id, blood_group="B+",
                                     urgency_level="normal", status="active")
        db.session.add(other_request)
        db.session.commit()
        with self.app.test_request_context("/api/assign"):
            session["user_id"] = self.seeker.user_id
            response, status = get_assignments()
            self.assertEqual(status, 200)
            payload = response.get_json()
            encoded = response.get_data(as_text=True)
            self.assertEqual(len(payload["assignments"]), 1)
            self.assertEqual(payload["assignments"][0]["request"]["request_id"], self.request.request_id)
            self.assertTrue(payload["assignments"][0]["donor_assigned"])
            self.assertNotIn("donor", payload["assignments"][0])
            self.assertNotIn("Private Requester", encoded)
            self.assertNotIn("Verified Donor", encoded)
            self.assertNotIn("donor@example.test", encoded)
            self.assertNotIn(str(other_request.request_id), encoded)
        admin = User(name="Admin", email="admin-test@example.test", password_hash="x",
                     phone="7777777777", role="admin", age=40)
        db.session.add(admin)
        db.session.commit()
        with self.app.test_request_context("/api/assign"):
            session["user_id"] = admin.user_id
            response, status = get_assignments()
            self.assertEqual(status, 200)
            payload = response.get_json()
            self.assertEqual(payload["assignment_count"], 1)
            self.assertEqual(payload["unmatched_count"], 1)
            self.assertEqual(payload["assignments"][0]["donor"]["email"], "donor@example.test")

    def test_compatibility_order_api(self):
        with self.app.test_request_context("/api/compatibility/order"):
            response, status = get_compatibility_order()
        self.assertEqual(status, 200)
        self.assertEqual(len(response.get_json()["cover_edges"]), 12)

    def test_production_requires_environment_secret(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SECRET_KEY", None)
            with self.assertRaises(RuntimeError):
                ProductionConfig()
            os.environ["SECRET_KEY"] = "test-only-production-key"
            self.assertEqual(ProductionConfig().SECRET_KEY, "test-only-production-key")

    def test_400_donor_network_stays_below_payload_and_time_limits(self):
        self.request.blood_group = "AB+"
        users = [
            User(name=f"Bulk Donor {i}", email=f"bulk-{i}@example.test",
                 password_hash="x", phone="8888888888", role="donor", age=30,
                 is_verified=(i % 2 == 0))
            for i in range(399)
        ]
        db.session.add_all(users)
        db.session.flush()
        donors = [self.donor]
        donors.extend(
            Donor(user_id=user.user_id, blood_group="AB+",
                  latitude=12.0 + (i % 20) * 0.002,
                  longitude=77.0 + (i // 20) * 0.002,
                  city="Grid", is_available=True, donation_count=i % 8)
            for i, user in enumerate(users)
        )
        db.session.add_all(donors[1:])
        db.session.commit()
        donors = Donor.query.options(__import__("sqlalchemy.orm").orm.joinedload(Donor.user)).all()
        start = time.perf_counter()
        result = build_network_data(self.request, donors=donors)
        elapsed = time.perf_counter() - start
        self.assertLess(len(result["edges"]), 2000)
        self.assertLess(elapsed, 0.5, f"build_network_data took {elapsed:.3f}s")


    def test_hospital_blood_bank_models_and_public_apis(self):
        hospital = Hospital(
            name="Test General Hospital", address="1 Sample Road",
            city="Test City", phone="5550100", is_demo=True,
        )
        bank = BloodBank(
            name="Test Blood Bank", address="2 Sample Road",
            city="Test City", is_demo=True,
        )
        bank.inventory.extend([
            BloodInventory(blood_group="A+", units=4, is_demo=True),
            BloodInventory(blood_group="O-", units=2, is_demo=True),
        ])
        db.session.add_all([hospital, bank])
        db.session.commit()

        with self.app.test_request_context("/api/hospitals"):
            hospitals, status = get_hospitals()
        self.assertEqual(status, 200)
        self.assertEqual(hospitals.get_json()["hospitals"][0]["name"], "Test General Hospital")
        self.assertTrue(hospitals.get_json()["hospitals"][0]["is_demo"])

        with self.app.test_request_context("/api/blood-banks"):
            banks, status = get_blood_banks()
        self.assertEqual(status, 200)
        bank_data = banks.get_json()["blood_banks"][0]
        self.assertEqual(bank_data["name"], "Test Blood Bank")
        self.assertEqual({item["blood_group"] for item in bank_data["inventory"]}, {"A+", "O-"})
        self.assertIn("not live availability", banks.get_json()["inventory_notice"])

        with self.app.test_request_context(f"/api/blood-banks/{bank.id}/inventory"):
            detail, status = get_blood_bank_inventory(bank.id)
        self.assertEqual(status, 200)
        self.assertEqual(len(detail.get_json()["inventory"]), 2)
        self.assertTrue(all(item["is_demo"] for item in detail.get_json()["inventory"]))
        with self.app.test_request_context("/api/blood-banks/9999/inventory"):
            missing, status = get_blood_bank_inventory(9999)
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
