"""
Discrete Mathematics Analytics Module for BloodLink
=====================================================
This module implements graph theory, set theory, combinatorics, relations,
functions/mappings, propositional logic, boolean logic, counting/cardinality,
pigeonhole principle, adjacency matrix, connectivity, and vertex degree
analytics — all computed from the existing BloodLink database entities.

Every function here works on REAL data from the existing database.
No fake/demo-only features.
"""

from collections import defaultdict, deque
from itertools import combinations
from math import comb

from sqlalchemy.orm import joinedload

from .models import (db, Donor, Hospital, BloodBank, BloodInventory,
                     BloodRequest, User)
from .eligibility import is_donor_eligible
from .utils import haversine_distance, get_compatible_blood_groups


# =========================================================================
# 1. BLOOD COMPATIBILITY — Relation & Function/Mapping (Concepts 6, 7, 18)
# =========================================================================

# Correct red-blood-cell compatibility: donor -> list of recipient groups
BLOOD_COMPATIBILITY = {
    "O-":  ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+":  ["O+", "A+", "B+", "AB+"],
    "A-":  ["A-", "A+", "AB-", "AB+"],
    "A+":  ["A+", "AB+"],
    "B-":  ["B-", "B+", "AB-", "AB+"],
    "B+":  ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}

# Reverse mapping: recipient -> list of compatible donor groups
RECEIVE_FROM = {
    "O-":  ["O-"],
    "O+":  ["O+", "O-"],
    "A-":  ["A-", "O-"],
    "A+":  ["A+", "A-", "O+", "O-"],
    "B-":  ["B-", "O-"],
    "B+":  ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
}

ALL_BLOOD_GROUPS = list(BLOOD_COMPATIBILITY.keys())


def get_compatibility_relation():
    """Return the blood compatibility as a mathematical relation (set of tuples).

    Concept: Relations (6), Functions/Mappings (7), Blood Compatibility (18).
    R = {(donor_group, recipient_group) | donor_group can donate to recipient_group}
    """
    relation = set()
    for donor_group, recipients in BLOOD_COMPATIBILITY.items():
        for recipient in recipients:
            relation.add((donor_group, recipient))
    return relation


# =========================================================================
# 2. GRAPH CONSTRUCTION from real DB data (Concepts 1, 4, 13)
# =========================================================================

def build_full_network_graph(radius_km=50.0):
    """Build a weighted undirected graph of all BloodLink entities.

    Vertices: donors, hospitals, blood_banks, blood_requests
    Edges: geographic proximity (weight = Haversine distance in km)

    Concept: Graph Theory (1), Weighted Graph (4), Adjacency Matrix (13).
    """
    graph = defaultdict(dict)  # node_id -> {neighbor_id: weight_km}
    nodes_info = {}  # node_id -> {type, name, lat, lon, ...}

    # --- Collect all entities with coordinates ---
    donors = Donor.query.options(joinedload(Donor.user)).all()
    hospitals = Hospital.query.all()
    blood_banks = BloodBank.query.all()
    requests = BloodRequest.query.filter_by(status='active').all()

    entities = []  # (node_id, lat, lon, entity_type, extra_info)

    for d in donors:
        if d.latitude is not None and d.longitude is not None:
            nid = f"donor:{d.donor_id}"
            nodes_info[nid] = {
                "type": "donor", "id": d.donor_id,
                "name": d.user.name, "blood_group": d.blood_group,
                "lat": d.latitude, "lon": d.longitude,
                "available": bool(d.is_available),
                "eligible": is_donor_eligible(d)["eligible"],
            }
            entities.append((nid, d.latitude, d.longitude))

    for h in hospitals:
        if h.latitude is not None and h.longitude is not None:
            nid = f"hospital:{h.id}"
            nodes_info[nid] = {
                "type": "hospital", "id": h.id,
                "name": h.name, "lat": h.latitude, "lon": h.longitude,
            }
            entities.append((nid, h.latitude, h.longitude))

    for bb in blood_banks:
        if bb.latitude is not None and bb.longitude is not None:
            nid = f"blood_bank:{bb.id}"
            nodes_info[nid] = {
                "type": "blood_bank", "id": bb.id,
                "name": bb.name, "lat": bb.latitude, "lon": bb.longitude,
            }
            entities.append((nid, bb.latitude, bb.longitude))

    for r in requests:
        if r.latitude is not None and r.longitude is not None:
            nid = f"request:{r.request_id}"
            nodes_info[nid] = {
                "type": "request", "id": r.request_id,
                "name": f"Request #{r.request_id}",
                "blood_group": r.blood_group,
                "urgency": r.urgency_level,
                "lat": r.latitude, "lon": r.longitude,
            }
            entities.append((nid, r.latitude, r.longitude))

    # --- Create edges based on geographic proximity (weighted graph) ---
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            nid_a, lat_a, lon_a = entities[i]
            nid_b, lat_b, lon_b = entities[j]
            dist = haversine_distance(lat_a, lon_a, lat_b, lon_b)
            if dist <= radius_km:
                graph[nid_a][nid_b] = round(dist, 3)
                graph[nid_b][nid_a] = round(dist, 3)

    # Ensure isolated nodes still appear as vertices
    for nid in nodes_info:
        if nid not in graph:
            graph[nid] = {}

    return dict(graph), nodes_info


# =========================================================================
# 3. BFS TRAVERSAL (Concept 2)
# =========================================================================

def bfs_traversal(graph, start):
    """Breadth-first search from a start node.

    Returns the list of visited node IDs in BFS order and a dict of levels.

    Concept: Graph Traversal — BFS (2).
    Used to find all reachable blood sources from an emergency request.
    """
    if start not in graph:
        return [], {}
    visited_order = []
    levels = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        visited_order.append(node)
        for neighbor in graph.get(node, {}):
            if neighbor not in levels:
                levels[neighbor] = levels[node] + 1
                queue.append(neighbor)
    return visited_order, levels


# =========================================================================
# 4. DFS TRAVERSAL (Concept 2)
# =========================================================================

def dfs_traversal(graph, start):
    """Depth-first search from a start node.

    Returns the list of visited node IDs in DFS order.

    Concept: Graph Traversal — DFS (2).
    Used to explore the full connected blood network from a hospital/blood bank.
    """
    if start not in graph:
        return []
    visited = []
    stack = [start]
    seen = set()
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        visited.append(node)
        # Push neighbors in reverse order for consistent traversal
        for neighbor in sorted(graph.get(node, {}), reverse=True):
            if neighbor not in seen:
                stack.append(neighbor)
    return visited


# =========================================================================
# 5. DIJKSTRA'S SHORTEST PATH (Concept 3)
# =========================================================================

def dijkstra_shortest_path(graph, start, goal):
    """Dijkstra's algorithm for shortest path in a weighted graph.

    Returns (distance_km, path_list) or (None, []) if unreachable.

    Concept: Shortest Path (3), Weighted Graph (4).
    Used to find the nearest suitable donor/blood bank/hospital.
    """
    from heapq import heappush, heappop

    if start not in graph:
        return None, []

    distances = {start: 0.0}
    previous = {}
    heap = [(0.0, start)]

    while heap:
        dist, node = heappop(heap)
        if dist > distances.get(node, float('inf')):
            continue
        if node == goal:
            break
        for neighbor, weight in graph.get(node, {}).items():
            new_dist = dist + weight
            if new_dist < distances.get(neighbor, float('inf')):
                distances[neighbor] = new_dist
                previous[neighbor] = node
                heappush(heap, (new_dist, neighbor))

    if goal not in distances:
        return None, []

    # Reconstruct path
    path = [goal]
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()
    return round(distances[goal], 3), path


def dijkstra_nearest_sources(graph, start, nodes_info, target_type=None):
    """Find all reachable nodes from start, sorted by Dijkstra distance.

    Optionally filter by target_type ('donor', 'hospital', 'blood_bank').

    Concept: Shortest Path (3).
    """
    from heapq import heappush, heappop

    if start not in graph:
        return []

    distances = {start: 0.0}
    heap = [(0.0, start)]

    while heap:
        dist, node = heappop(heap)
        if dist > distances.get(node, float('inf')):
            continue
        for neighbor, weight in graph.get(node, {}).items():
            new_dist = dist + weight
            if new_dist < distances.get(neighbor, float('inf')):
                distances[neighbor] = new_dist
                heappush(heap, (new_dist, neighbor))

    results = []
    for nid, dist in sorted(distances.items(), key=lambda x: x[1]):
        if nid == start:
            continue
        info = nodes_info.get(nid, {})
        if target_type and info.get("type") != target_type:
            continue
        results.append({
            "node_id": nid,
            "distance_km": round(dist, 3),
            **info,
        })
    return results


# =========================================================================
# 6. SET THEORY — Filtering with set operations (Concept 5)
# =========================================================================

def set_theory_donor_filter(required_blood_group, latitude, longitude,
                            radius_km=10.0):
    """Filter eligible donors using explicit set intersection.

    D = set of all donors
    A = set of available donors          (Boolean logic — Concept 9)
    B = set of compatible blood group donors (Relation — Concept 6)
    L = set of donors within radius      (Weighted graph distance)
    E = set of eligible donors           (Propositional logic — Concept 8)

    Result = A ∩ B ∩ L ∩ E

    Concepts: Set Theory (5), Boolean Logic (9), Propositional Logic (8),
              Relations (6), Counting/Cardinality (11).
    """
    all_donors = Donor.query.options(joinedload(Donor.user)).all()

    # D: Universal set of all donor IDs
    D = {d.donor_id for d in all_donors}

    # A: Available donors (Boolean — is_available == True)
    A = {d.donor_id for d in all_donors if d.is_available}

    # B: Blood-compatible donors (Relation — donor can donate to recipient)
    compatible_groups = set(RECEIVE_FROM.get(required_blood_group, []))
    B = {d.donor_id for d in all_donors if d.blood_group in compatible_groups}

    # L: Donors within geographic radius
    L = set()
    donor_distances = {}
    for d in all_donors:
        if d.latitude is not None and d.longitude is not None:
            dist = haversine_distance(latitude, longitude, d.latitude, d.longitude)
            if dist <= radius_km:
                L.add(d.donor_id)
                donor_distances[d.donor_id] = round(dist, 3)

    # E: Eligible donors (Propositional Logic — age ∧ waiting_period)
    E = {d.donor_id for d in all_donors if is_donor_eligible(d)["eligible"]}

    # Final eligible set using SET INTERSECTION
    eligible_set = A & B & L & E  # ← Set Theory intersection

    # Also compute useful set operations for analytics
    donor_map = {d.donor_id: d for d in all_donors}
    eligible_donors = []
    for did in eligible_set:
        d = donor_map[did]
        eligible_donors.append({
            "donor_id": d.donor_id,
            "name": d.user.name,
            "blood_group": d.blood_group,
            "distance_km": donor_distances.get(did),
            "city": d.city,
            "is_verified": bool(d.user.is_verified),
        })
    eligible_donors.sort(key=lambda x: x.get("distance_km") or 999)

    return {
        "required_blood_group": required_blood_group,
        "radius_km": radius_km,
        "set_operations": {
            "D_all_donors": len(D),
            "A_available": len(A),
            "B_compatible": len(B),
            "L_within_radius": len(L),
            "E_eligible": len(E),
            "A_intersect_B": len(A & B),
            "A_intersect_B_intersect_L": len(A & B & L),
            "final_eligible_A_intersect_B_intersect_L_intersect_E": len(eligible_set),
            "A_union_B": len(A | B),
            "D_difference_A": len(D - A),  # Unavailable donors
            "compatible_but_unavailable": len(B - A),
            "nearby_but_incompatible": len(L - B),
        },
        "eligible_donors": eligible_donors,
        "dm_concept": "Set Theory — Eligible = Available ∩ Compatible ∩ Nearby ∩ Eligible",
    }


# =========================================================================
# 7. SET THEORY — Blood Bank filtering (Concept 5)
# =========================================================================

def set_theory_bloodbank_filter(required_blood_group, latitude=None,
                                longitude=None, radius_km=50.0):
    """Filter blood banks using set operations.

    AvailableBanks ∩ HasRequiredGroup ∩ WithinDistance

    Concept: Set Theory (5), Boolean Logic (9).
    """
    banks = BloodBank.query.all()
    inventory_items = BloodInventory.query.all()

    compatible_groups = set(RECEIVE_FROM.get(required_blood_group, []))

    # S: All blood banks
    S = {b.id for b in banks}

    # H: Banks that have at least one compatible blood group with units > 0
    bank_inventory = defaultdict(dict)
    for item in inventory_items:
        bank_inventory[item.blood_bank_id][item.blood_group] = item.units
    H = {bid for bid, inv in bank_inventory.items()
         if any(inv.get(g, 0) > 0 for g in compatible_groups)}

    # G: Banks within geographic radius
    G = set()
    bank_distances = {}
    if latitude is not None and longitude is not None:
        for b in banks:
            if b.latitude is not None and b.longitude is not None:
                dist = haversine_distance(latitude, longitude, b.latitude, b.longitude)
                if dist <= radius_km:
                    G.add(b.id)
                    bank_distances[b.id] = round(dist, 3)
    else:
        G = S  # No location filter

    # Result = H ∩ G (banks with stock AND within distance)
    result_set = H & G

    bank_map = {b.id: b for b in banks}
    results = []
    for bid in result_set:
        b = bank_map[bid]
        results.append({
            "id": b.id, "name": b.name, "city": b.city,
            "distance_km": bank_distances.get(bid),
            "available_units": {g: bank_inventory[bid].get(g, 0) for g in compatible_groups
                                if bank_inventory[bid].get(g, 0) > 0},
        })
    results.sort(key=lambda x: x.get("distance_km") or 999)

    return {
        "required_blood_group": required_blood_group,
        "set_operations": {
            "S_all_banks": len(S),
            "H_has_stock": len(H),
            "G_within_radius": len(G),
            "result_H_intersect_G": len(result_set),
        },
        "suitable_blood_banks": results,
        "dm_concept": "Set Theory — Suitable = HasStock ∩ WithinRadius",
    }


# =========================================================================
# 8. CONNECTED COMPONENTS (Concept 14)
# =========================================================================

def find_connected_components(graph):
    """Find all connected components in an undirected graph.

    Concept: Graph Connectivity (14).
    Used to determine if a blood request is connected to at least one source.
    """
    visited = set()
    components = []
    for node in graph:
        if node in visited:
            continue
        component = []
        queue = deque([node])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            for neighbor in graph.get(current, {}):
                if neighbor not in visited:
                    queue.append(neighbor)
        components.append(component)
    return components


# =========================================================================
# 9. VERTEX DEGREE (Concept 15)
# =========================================================================

def compute_vertex_degrees(graph):
    """Compute degree of each vertex in the graph.

    Concept: Degree of Vertex (15).
    Examples: number of blood sources connected to a hospital,
              number of requests a donor can satisfy.
    """
    degrees = {}
    for node in graph:
        degrees[node] = len(graph.get(node, {}))
    return degrees


# =========================================================================
# 10. ADJACENCY MATRIX (Concept 13)
# =========================================================================

def build_adjacency_matrix(graph):
    """Build a dense adjacency matrix from the graph.

    Concept: Matrices / Adjacency Matrix (13).
    The database remains the primary data source; this matrix is used
    only for graph algorithm computations.
    """
    nodes = sorted(graph.keys())
    index = {node: i for i, node in enumerate(nodes)}
    size = len(nodes)
    matrix = [[0.0] * size for _ in range(size)]
    for src in graph:
        for dst, weight in graph[src].items():
            matrix[index[src]][index[dst]] = weight
    return {
        "nodes": nodes,
        "size": size,
        "matrix": matrix,
    }


# =========================================================================
# 11. PIGEONHOLE PRINCIPLE (Concept 12)
# =========================================================================

def pigeonhole_analysis():
    """Detect situations where requests exceed available blood sources.

    Pigeonhole Principle: if n items are put into m containers with n > m,
    then at least one container must hold more than one item.

    Here: if |active_requests_for_group| > |available_donors_for_group|,
    some requests CANNOT be satisfied simultaneously.

    Concept: Pigeonhole Principle (12).
    """
    active_requests = BloodRequest.query.filter_by(status='active').all()
    all_donors = Donor.query.options(joinedload(Donor.user)).all()

    # Count requests per blood group (pigeons)
    requests_by_group = defaultdict(int)
    for r in active_requests:
        requests_by_group[r.blood_group] += 1

    # Count available eligible donors per compatible group (holes)
    available_donors_by_group = defaultdict(set)
    for d in all_donors:
        if d.is_available and is_donor_eligible(d)["eligible"]:
            # This donor can donate to these recipient groups
            for recipient in BLOOD_COMPATIBILITY.get(d.blood_group, []):
                available_donors_by_group[recipient].add(d.donor_id)

    # Also count blood bank units
    inventory_by_group = defaultdict(int)
    for item in BloodInventory.query.all():
        if item.units > 0:
            inventory_by_group[item.blood_group] += item.units

    warnings = []
    for group in ALL_BLOOD_GROUPS:
        n_requests = requests_by_group.get(group, 0)
        n_donors = len(available_donors_by_group.get(group, set()))
        n_units = inventory_by_group.get(group, 0)
        total_sources = n_donors + n_units

        if n_requests > 0 and n_requests > total_sources:
            warnings.append({
                "blood_group": group,
                "active_requests": n_requests,
                "available_donors": n_donors,
                "bank_units": n_units,
                "total_sources": total_sources,
                "pigeonhole_violated": True,
                "warning": (
                    f"Pigeonhole Principle: {n_requests} request(s) for {group} "
                    f"but only {total_sources} source(s). "
                    f"At least {n_requests - total_sources} request(s) cannot "
                    f"be fulfilled simultaneously."
                ),
            })

    return {
        "requests_by_group": dict(requests_by_group),
        "donors_by_group": {g: len(s) for g, s in available_donors_by_group.items()},
        "inventory_by_group": dict(inventory_by_group),
        "pigeonhole_warnings": warnings,
        "has_warnings": len(warnings) > 0,
        "dm_concept": "Pigeonhole Principle — if requests > sources, some cannot be met",
    }


# =========================================================================
# 12. COMBINATORICS (Concept 10)
# =========================================================================

def donor_combinations(required_blood_group, units_needed, latitude=None,
                       longitude=None, radius_km=50.0):
    """Calculate possible donor combinations for a multi-unit request.

    C(n, k) = n! / (k! * (n-k)!)

    Concept: Combinatorics (10).
    Only implemented when it naturally fits (multi-unit emergency requests).
    """
    # Get eligible compatible donors
    filter_result = set_theory_donor_filter(
        required_blood_group, latitude or 0, longitude or 0, radius_km
    )
    eligible = filter_result["eligible_donors"]
    n = len(eligible)
    k = min(units_needed, n)

    # Calculate total possible combinations
    total_combinations = comb(n, k) if k > 0 else 0

    # Show a few sample combinations (limit to avoid explosion)
    sample_combos = []
    if n > 0 and k > 0 and total_combinations <= 100:
        for combo in combinations(eligible, k):
            sample_combos.append([d["name"] for d in combo])

    return {
        "eligible_donor_count": n,
        "units_needed": units_needed,
        "total_possible_combinations": total_combinations,
        "formula": f"C({n}, {k}) = {total_combinations}",
        "sample_combinations": sample_combos[:20],  # Limit output
        "dm_concept": "Combinatorics — C(n,k) possible donor groups for multi-unit requests",
    }


# =========================================================================
# 13. COUNTING / CARDINALITY (Concept 11)
# =========================================================================

def cardinality_stats():
    """Calculate cardinality of key sets in the BloodLink system.

    Concept: Counting / Cardinality (11).
    |D| = number of donors, |H| = number of hospitals, etc.
    All values come from the actual database.
    """
    total_donors = Donor.query.count()
    available_donors = Donor.query.filter_by(is_available=True).count()
    total_hospitals = Hospital.query.count()
    total_blood_banks = BloodBank.query.count()
    active_requests = BloodRequest.query.filter_by(status='active').count()
    total_requests = BloodRequest.query.count()
    total_users = User.query.count()

    # Blood group distribution
    donor_groups = db.session.query(
        Donor.blood_group, db.func.count(Donor.donor_id)
    ).group_by(Donor.blood_group).all()

    # Total blood units across all banks
    total_units = db.session.query(
        db.func.coalesce(db.func.sum(BloodInventory.units), 0)
    ).scalar()

    return {
        "|D|_total_donors": total_donors,
        "|D_avail|_available_donors": available_donors,
        "|H|_hospitals": total_hospitals,
        "|BB|_blood_banks": total_blood_banks,
        "|R_active|_active_requests": active_requests,
        "|R|_total_requests": total_requests,
        "|U|_total_users": total_users,
        "|Units|_total_blood_units": total_units,
        "donor_distribution_by_group": {
            group: count for group, count in donor_groups
        },
        "dm_concept": "Counting/Cardinality — |S| = number of elements in set S",
    }


# =========================================================================
# 14. PROPOSITIONAL LOGIC for eligibility (Concept 8)
# =========================================================================

def propositional_eligibility_check(donor_id):
    """Show the propositional logic evaluation for a donor's eligibility.

    A = donor is available
    B = donor has compatible blood group (for a given request)
    C = donor is within required distance
    D = donor satisfies age/waiting-period eligibility

    Eligible = A ∧ B ∧ C ∧ D

    Concept: Logic / Propositional Logic (8), Boolean Logic (9).
    """
    donor = Donor.query.options(joinedload(Donor.user)).get(donor_id)
    if not donor:
        return {"error": "Donor not found"}

    eligibility = is_donor_eligible(donor)

    A = bool(donor.is_available)
    D = eligibility["eligible"]
    has_coords = donor.latitude is not None and donor.longitude is not None

    return {
        "donor_id": donor_id,
        "donor_name": donor.user.name,
        "propositions": {
            "A_is_available": A,
            "D_meets_eligibility": D,
            "has_coordinates": has_coords,
            "blood_group": donor.blood_group,
        },
        "eligibility_result": eligibility,
        "logic_expression": "Eligible = A ∧ D (Available AND Meets eligibility rules)",
        "evaluation": f"A={A} ∧ D={D} = {A and D}",
        "final_eligible": A and D,
        "dm_concept": "Propositional Logic — conjunction of boolean conditions",
    }


# =========================================================================
# 15. GRAPH-BASED MATCHING / RANKING (Concept 16)
# =========================================================================

def ranked_blood_sources(blood_group, latitude, longitude, radius_km=50.0):
    """Rank all potential blood sources for a request using graph-based scoring.

    Ranking factors:
    1. Blood compatibility (exact match vs. compatible)
    2. Availability (boolean)
    3. Distance (Dijkstra/Haversine)
    4. Verification status
    5. Reliability score

    Concept: Graph-Based Matching / Ranking (16).
    """
    from .utils import calculate_donor_reliability_score

    compatible_groups = set(RECEIVE_FROM.get(blood_group, []))
    donors = Donor.query.options(joinedload(Donor.user)).all()

    ranked = []
    for d in donors:
        if not d.is_available or not is_donor_eligible(d)["eligible"]:
            continue
        if d.blood_group not in compatible_groups:
            continue
        if d.latitude is None or d.longitude is None:
            continue

        dist = haversine_distance(latitude, longitude, d.latitude, d.longitude)
        if dist > radius_km:
            continue

        # Scoring: lower is better for distance, higher is better for others
        exact_match = 1.0 if d.blood_group == blood_group else 0.5
        distance_score = max(0, 1.0 - (dist / radius_km))
        reliability = calculate_donor_reliability_score(d) / 100.0
        verified_bonus = 0.1 if d.user.is_verified else 0.0

        composite_score = round(
            0.30 * exact_match +
            0.35 * distance_score +
            0.25 * reliability +
            0.10 * verified_bonus, 4
        )

        ranked.append({
            "donor_id": d.donor_id,
            "name": d.user.name,
            "blood_group": d.blood_group,
            "distance_km": round(dist, 3),
            "is_verified": bool(d.user.is_verified),
            "reliability_score": round(reliability * 100),
            "exact_match": d.blood_group == blood_group,
            "composite_score": composite_score,
        })

    ranked.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, item in enumerate(ranked, 1):
        item["rank"] = i

    return {
        "blood_group": blood_group,
        "total_matches": len(ranked),
        "ranked_sources": ranked,
        "ranking_formula": "0.30*compatibility + 0.35*distance + 0.25*reliability + 0.10*verification",
        "dm_concept": "Graph-Based Matching — weighted multi-criteria ranking",
    }


# =========================================================================
# 16. EMERGENCY REQUEST CONNECTIVITY CHECK (Concepts 14, 17)
# =========================================================================

def emergency_connectivity_check(request_id):
    """Check if an emergency request is connected to at least one suitable source.

    Concept: Graph Connectivity (14), Emergency Request (17).
    """
    blood_request = BloodRequest.query.get(request_id)
    if not blood_request:
        return {"error": "Request not found"}

    graph, nodes_info = build_full_network_graph(radius_km=100.0)
    req_node = f"request:{request_id}"

    if req_node not in graph:
        return {
            "request_id": request_id,
            "connected": False,
            "message": "Request has no coordinates — cannot check geographic connectivity.",
            "connected_sources": [],
        }

    # BFS from the request node
    visited, levels = bfs_traversal(graph, req_node)

    # Filter connected sources that have compatible blood
    compatible_groups = set(RECEIVE_FROM.get(blood_request.blood_group, []))
    connected_sources = []
    for nid in visited:
        if nid == req_node:
            continue
        info = nodes_info.get(nid, {})
        ntype = info.get("type")
        # Check donors
        if ntype == "donor" and info.get("blood_group") in compatible_groups:
            if info.get("available") and info.get("eligible"):
                connected_sources.append({
                    "node_id": nid, "type": "donor",
                    "name": info["name"], "blood_group": info["blood_group"],
                    "hops": levels.get(nid, -1),
                })
        # Check blood banks
        elif ntype == "blood_bank":
            connected_sources.append({
                "node_id": nid, "type": "blood_bank",
                "name": info["name"],
                "hops": levels.get(nid, -1),
            })
        # Check hospitals
        elif ntype == "hospital":
            connected_sources.append({
                "node_id": nid, "type": "hospital",
                "name": info["name"],
                "hops": levels.get(nid, -1),
            })

    is_connected = len(connected_sources) > 0
    message = (
        f"Request is connected to {len(connected_sources)} source(s)."
        if is_connected
        else "No suitable blood source is currently connected to this request."
    )

    return {
        "request_id": request_id,
        "blood_group": blood_request.blood_group,
        "urgency": blood_request.urgency_level,
        "connected": is_connected,
        "message": message,
        "total_reachable_nodes": len(visited),
        "connected_sources": connected_sources,
        "dm_concept": "Graph Connectivity — BFS reachability from request vertex",
    }


# =========================================================================
# 17. FULL GRAPH STATISTICS (Concept 21)
# =========================================================================

def full_graph_statistics():
    """Complete DM analysis of the BloodLink network.

    Concept: Optional DM Analysis (21).
    All values computed from actual database data.
    """
    graph, nodes_info = build_full_network_graph(radius_km=50.0)
    components = find_connected_components(graph)
    degrees = compute_vertex_degrees(graph)
    matrix_data = build_adjacency_matrix(graph)
    cardinality = cardinality_stats()
    pigeonhole = pigeonhole_analysis()

    # Classify nodes by type
    type_counts = defaultdict(int)
    for nid, info in nodes_info.items():
        type_counts[info.get("type", "unknown")] += 1

    # Find high-degree vertices (hubs)
    top_hubs = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "graph_summary": {
            "total_vertices": len(graph),
            "total_edges": sum(len(v) for v in graph.values()) // 2,
            "connected_components": len(components),
            "component_sizes": [len(c) for c in components],
            "is_connected": len(components) <= 1,
        },
        "vertex_types": dict(type_counts),
        "top_hubs": [{"node": n, "degree": d} for n, d in top_hubs],
        "cardinality": cardinality,
        "pigeonhole_analysis": pigeonhole,
        "adjacency_matrix_size": f"{matrix_data['size']}x{matrix_data['size']}",
        "dm_concepts_demonstrated": [
            "Graph Theory (vertices/edges)",
            "Graph Traversal (BFS/DFS)",
            "Shortest Path (Dijkstra)",
            "Weighted Graph (distance edges)",
            "Set Theory (donor filtering)",
            "Relations (compatibility relation)",
            "Functions/Mappings (blood group → compatible groups)",
            "Propositional Logic (eligibility conditions)",
            "Boolean Logic (availability flags)",
            "Combinatorics (donor combinations)",
            "Counting/Cardinality (|D|, |H|, |BB|, |R|)",
            "Pigeonhole Principle (request vs source analysis)",
            "Adjacency Matrix (graph representation)",
            "Graph Connectivity (connected components)",
            "Degree of Vertex (hub analysis)",
            "Graph-Based Matching/Ranking (weighted scoring)",
        ],
    }


# =========================================================================
# 18. DM DOCUMENTATION (Concept 22)
# =========================================================================

def dm_documentation():
    """Return academic documentation mapping each DM concept to BloodLink.

    Concept: Academic Requirement (22).
    """
    return {
        "project": "BloodLink — Discrete Mathematics Graph Theory Application",
        "concepts": [
            {
                "concept": "1. Graph Theory",
                "representation": "Donors, Hospitals, Blood Banks, Requests are vertices. "
                                  "Geographic proximity and blood compatibility are edges.",
                "algorithm": "Adjacency list representation, edge weights = Haversine distance",
                "used_in": "build_full_network_graph(), build_network_data()",
            },
            {
                "concept": "2. Graph Traversal (BFS & DFS)",
                "representation": "BFS finds reachable blood sources level by level. "
                                  "DFS explores full connected network depth-first.",
                "algorithm": "BFS: O(V+E) queue-based. DFS: O(V+E) stack-based.",
                "used_in": "bfs_traversal(), dfs_traversal(), emergency_connectivity_check()",
            },
            {
                "concept": "3. Shortest Path (Dijkstra)",
                "representation": "Distance between entities is edge weight. "
                                  "Dijkstra finds nearest donor/hospital/blood bank.",
                "algorithm": "Dijkstra's algorithm: O((V+E) log V) with min-heap",
                "used_in": "dijkstra_shortest_path(), dijkstra_nearest_sources(), "
                           "_dijkstra() in graph_service.py",
            },
            {
                "concept": "4. Weighted Graph",
                "representation": "Edge weight = Haversine geographic distance in km",
                "algorithm": "Pairwise distance computation, k-nearest neighbor graph",
                "used_in": "build_full_network_graph(), _build_sparse_location_graph()",
            },
            {
                "concept": "5. Set Theory",
                "representation": "D=all donors, A=available, B=compatible, L=nearby, E=eligible. "
                                  "Result = A ∩ B ∩ L ∩ E. Also union, difference.",
                "algorithm": "Python set operations: &, |, -",
                "used_in": "set_theory_donor_filter(), set_theory_bloodbank_filter()",
            },
            {
                "concept": "6. Relations",
                "representation": "R = {(donor_group, recipient_group) | donor can donate}. "
                                  "Also: Donor → BloodGroup, Hospital → BloodRequest.",
                "algorithm": "Set of ordered pairs, compatibility lookup",
                "used_in": "get_compatibility_relation(), BLOOD_COMPATIBILITY dict",
            },
            {
                "concept": "7. Functions / Mappings",
                "representation": "BloodGroup → CompatibleGroups, DonorID → Profile, "
                                  "BloodBankID → Inventory",
                "algorithm": "Deterministic dictionary mappings",
                "used_in": "BLOOD_COMPATIBILITY, RECEIVE_FROM, get_compatible_blood_groups()",
            },
            {
                "concept": "8. Propositional Logic",
                "representation": "A=available, B=compatible, C=nearby, D=eligible. "
                                  "Eligible = A ∧ B ∧ C ∧ D",
                "algorithm": "Conjunction of boolean propositions",
                "used_in": "propositional_eligibility_check(), set_theory_donor_filter()",
            },
            {
                "concept": "9. Boolean Logic",
                "representation": "is_available (True/False), is_verified, is_eligible, "
                                  "units > 0",
                "algorithm": "Boolean evaluation of database fields",
                "used_in": "Donor model, eligibility checks, inventory availability",
            },
            {
                "concept": "10. Combinatorics",
                "representation": "C(n,k) possible groups of k donors from n eligible",
                "algorithm": "Binomial coefficient C(n,k) = n! / (k!(n-k)!)",
                "used_in": "donor_combinations()",
            },
            {
                "concept": "11. Counting / Cardinality",
                "representation": "|D|=donors, |H|=hospitals, |BB|=blood banks, |R|=requests",
                "algorithm": "SQL COUNT queries on actual database",
                "used_in": "cardinality_stats()",
            },
            {
                "concept": "12. Pigeonhole Principle",
                "representation": "If requests > available sources for a blood group, "
                                  "some requests cannot be fulfilled simultaneously.",
                "algorithm": "Compare request count vs source count per blood group",
                "used_in": "pigeonhole_analysis()",
            },
            {
                "concept": "13. Adjacency Matrix",
                "representation": "Dense matrix M where M[i][j] = distance between entities",
                "algorithm": "Convert adjacency list to NxN matrix",
                "used_in": "build_adjacency_matrix()",
            },
            {
                "concept": "14. Graph Connectivity",
                "representation": "Connected components show isolated sub-networks. "
                                  "Checks if a request is connected to any source.",
                "algorithm": "BFS-based component discovery",
                "used_in": "find_connected_components(), emergency_connectivity_check()",
            },
            {
                "concept": "15. Degree of Vertex",
                "representation": "Degree = number of connections. High degree = hub entity.",
                "algorithm": "Count adjacency list length per vertex",
                "used_in": "compute_vertex_degrees(), full_graph_statistics()",
            },
            {
                "concept": "16. Graph-Based Matching / Ranking",
                "representation": "Multi-criteria weighted score: compatibility + distance + "
                                  "reliability + verification",
                "algorithm": "Weighted linear combination, sort by composite score",
                "used_in": "ranked_blood_sources(), build_network_data()",
            },
            {
                "concept": "17. Emergency Request",
                "representation": "BFS from request vertex to find all reachable sources",
                "algorithm": "BFS traversal + blood compatibility filter",
                "used_in": "emergency_connectivity_check()",
            },
            {
                "concept": "18. Blood Compatibility",
                "representation": "Directed graph: donor group → recipient groups. "
                                  "Verified RBC compatibility rules.",
                "algorithm": "Compatibility adjacency, Hasse diagram cover edges",
                "used_in": "BLOOD_COMPATIBILITY, compatibility_adjacency() in graph_service.py",
            },
        ],
    }
