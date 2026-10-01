"""Blood compatibility and location graph algorithms for the BloodLink network."""
from collections import defaultdict
from heapq import heappop, heappush
from math import asin, cos, radians, sin, sqrt
from itertools import count

from sqlalchemy.orm import joinedload

from .eligibility import is_donor_eligible
from .models import Donor
from .utils import calculate_donor_reliability_score, get_compatible_blood_groups

BLOOD_GROUPS = ("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+")


def compatibility_adjacency():
    """Build directed donor-group -> recipient-group adjacency from existing rules."""
    graph = {group: [] for group in BLOOD_GROUPS}
    for recipient in BLOOD_GROUPS:
        for donor in get_compatible_blood_groups(recipient, urgency=3):
            if donor in graph and recipient not in graph[donor]:
                graph[donor].append(recipient)
    return graph


def hasse_cover_edges(graph=None):
    """Compute the transitive reduction of the existing compatibility relation."""
    graph = graph or compatibility_adjacency()
    relation = {(source, target) for source, targets in graph.items() for target in targets}
    covers = []
    for source, target in sorted(relation):
        if source == target:
            continue
        # A comparable middle element means this edge is implied transitively.
        if not any(middle not in (source, target)
                   and (source, middle) in relation and (middle, target) in relation
                   for middle in graph):
            covers.append({"source": source, "target": target})
    return covers


def compatibility_order_data():
    """Calculate partial-order properties and extrema from the actual graph."""
    graph = compatibility_adjacency()
    relation = {(source, target) for source, targets in graph.items() for target in targets}
    covers = hasse_cover_edges(graph)
    reflexive = all((group, group) in relation for group in graph)
    antisymmetric = all(not (a != b and (a, b) in relation and (b, a) in relation)
                        for a in graph for b in graph)
    transitive = all((a, c) in relation
                     for a, b in relation for b2, c in relation if b == b2)
    incoming = {group: 0 for group in graph}
    outgoing = {group: 0 for group in graph}
    for edge in covers:
        outgoing[edge["source"]] += 1
        incoming[edge["target"]] += 1
    minimal = [group for group in graph if incoming[group] == 0]
    maximal = [group for group in graph if outgoing[group] == 0]
    return {
        "nodes": list(graph),
        "cover_edges": covers,
        "reflexive": reflexive,
        "antisymmetric": antisymmetric,
        "transitive": transitive,
        "is_partial_order": reflexive and antisymmetric and transitive,
        "minimal_element": minimal[0] if len(minimal) == 1 else minimal,
        "maximal_element": maximal[0] if len(maximal) == 1 else maximal,
    }


def _dijkstra(graph, start, goal):
    """Heap-based Dijkstra; O((V + E) log V)."""
    serial, distances, previous = count(), {start: 0.0}, {}
    queue = [(0.0, next(serial), start)]
    while queue:
        distance, _, node = heappop(queue)
        if distance != distances.get(node):
            continue
        if node == goal:
            break
        for neighbor, weight in graph.get(node, ()):
            candidate = distance + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor], previous[neighbor] = candidate, node
                heappush(queue, (candidate, next(serial), neighbor))
    if goal not in distances:
        return None, []
    path = [goal]
    while path[-1] != start:
        path.append(previous[path[-1]])
    return distances[goal], list(reversed(path))



def _dijkstra_tree(graph, start):
    """Run one source Dijkstra for all destinations in O((V + E) log V)."""
    serial, distances, previous = count(), {start: 0.0}, {}
    queue = [(0.0, next(serial), start)]
    while queue:
        distance, _, node = heappop(queue)
        if distance != distances.get(node):
            continue
        for neighbor, weight in graph.get(node, ()):
            candidate = distance + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor], previous[neighbor] = candidate, node
                heappush(queue, (candidate, next(serial), neighbor))
    return distances, previous


def _path_from_tree(start, goal, distances, previous):
    if goal not in distances:
        return None, []
    path = [goal]
    while path[-1] != start:
        parent = previous.get(path[-1])
        if parent is None:
            return None, []
        path.append(parent)
    return distances[goal], list(reversed(path))


def _bfs_levels(graph, start):
    """BFS levels over adjacency lists; O(V + E)."""
    queue, cursor, levels = [start], 0, {start: 0}
    while cursor < len(queue):
        node = queue[cursor]
        cursor += 1
        for neighbor in graph.get(node, ()):
            if neighbor not in levels:
                levels[neighbor] = levels[node] + 1
                queue.append(neighbor)
    return queue, levels


def _build_sparse_location_graph(locations, k=3):
    """Build an undirected k-nearest-neighbor graph and bridge components.

    Pairwise Haversine distances are computed once. The kNN edges keep the
    graph sparse; disconnected components are repeatedly joined by their
    nearest cross-component location pair. This is connectivity repair, not
    an MST/Kruskal feature.
    """
    ids = [item[0] for item in locations]
    id_index = {node: index for index, node in enumerate(ids)}
    size = len(ids)
    graph = {node: {} for node in ids}
    if size < 2:
        return {node: [] for node in ids}
    # Precompute radians and cosine(latitude) once per location; this is the
    # same Haversine calculation, avoiding repeated conversions/cosines per pair.
    radians_locations = [
        (radians(lat), radians(lon), cos(radians(lat)))
        for _, lat, lon in locations
    ]
    distances = [[0.0] * size for _ in range(size)]
    earth_diameter_km = 2 * 6371
    for i in range(size):
        lat1, lon1, cos_lat1 = radians_locations[i]
        for j in range(i + 1, size):
            lat2, lon2, cos_lat2 = radians_locations[j]
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = sin(dlat / 2) ** 2 + cos_lat1 * cos_lat2 * sin(dlon / 2) ** 2
            distance = earth_diameter_km * asin(sqrt(min(1.0, a)))
            distances[i][j] = distances[j][i] = distance

    def connect(i, j):
        weight = distances[i][j]
        graph[ids[i]][ids[j]] = weight
        graph[ids[j]][ids[i]] = weight

    for i in range(size):
        nearest = sorted(
            (j for j in range(size) if j != i),
            key=distances[i].__getitem__,
        )[:max(0, k)]
        for j in nearest:
            connect(i, j)

    def connected_components():
        remaining = set(range(size))
        components = []
        while remaining:
            root = remaining.pop()
            component, queue, cursor = {root}, [root], 0
            while cursor < len(queue):
                current = queue[cursor]
                cursor += 1
                for neighbor_id in graph[ids[current]]:
                    neighbor = id_index[neighbor_id]
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        component.add(neighbor)
                        queue.append(neighbor)
            components.append(component)
        return components

    # Bridge each current component to its nearest other component; repeat in
    # case simultaneous nearest links do not connect every component at once.
    while True:
        components = connected_components()
        if len(components) <= 1:
            break
        bridges = []
        for component in components:
            nearest = min(
                ((distances[i][j], i, j)
                 for i in component
                 for other in components if other is not component
                 for j in other),
                key=lambda edge: edge[0],
            )
            bridges.append((nearest[1], nearest[2]))
        for i, j in bridges:
            connect(i, j)

    return {node: list(neighbors.items()) for node, neighbors in graph.items()}


def _compatibility_levels(recipient_group, covers):
    """Traverse cover edges backwards from recipient; exact type is level zero."""
    incoming = defaultdict(list)
    for edge in covers:
        incoming[edge["target"]].append(edge["source"])
    _, levels = _bfs_levels(incoming, recipient_group)
    return levels

def build_network_data(blood_request, donors=None):
    """Build a request graph, discover matches, and return sparse-graph routes."""
    compatibility = compatibility_adjacency()
    covers = hasse_cover_edges(compatibility)
    nodes = [{"id": f"group:{group}", "type": "blood_group", "label": group}
             for group in BLOOD_GROUPS]
    # The public graph contains compatibility and matching edges only, plus routes.
    edges = [{"source": f"group:{source}", "target": f"group:{target}",
              "type": "compatible_blood_group"}
             for source, targets in compatibility.items() for target in targets]
    if blood_request is None:
        return {"blood_groups": list(BLOOD_GROUPS), "compatibility": compatibility,
                "cover_edges": covers, "nodes": nodes, "edges": edges, "donors": [],
                "bfs_order": [], "selected_request": None}

    req = blood_request
    req_node, req_group = f"request:{req.request_id}", req.blood_group
    donor_groups = [group for group in get_compatible_blood_groups(req_group, urgency=3)
                    if group in BLOOD_GROUPS]
    group_bfs_order, group_levels = _bfs_levels(
        defaultdict(list, {group: [edge["source"] for edge in covers if edge["target"] == group]
                           for group in BLOOD_GROUPS}), req_group)
    nodes.append({"id": req_node, "type": "request",
                  "label": f"Request #{req.request_id} · {req_group}",
                  "blood_group": req_group, "urgency": req.urgency_level})

    has_req_coords = req.latitude is not None and req.longitude is not None
    req_loc = f"location:request:{req.request_id}"
    locations = [(req_loc, req.latitude, req.longitude)] if has_req_coords else []
    nodes_by_id = {node["id"]: node["label"] for node in nodes}
    route_graph = {req_node: []}
    route_weights = {}

    def add_route_edge(source, target, weight):
        route_graph.setdefault(source, []).append((target, weight))
        route_weights[(source, target)] = weight

    if has_req_coords:
        nodes.append({"id": req_loc, "type": "location",
                      "label": req.location or "Request location",
                      "latitude": req.latitude, "longitude": req.longitude})
        nodes_by_id[req_loc] = req.location or "Request location"
        add_route_edge(req_node, req_loc, 0.0)
        add_route_edge(req_loc, req_node, 0.0)

    donors = (list(donors) if donors is not None else
              Donor.query.options(joinedload(Donor.user)).all())
    matches, donor_locations, donor_nodes_by_id = [], {}, {}
    seen_donor_ids = set()
    urgency_weights = {
        "critical": (0.60, 0.20, 0.20),
        "urgent": (0.45, 0.35, 0.20),
        "normal": (0.30, 0.50, 0.20),
    }
    w_dist, w_rel, w_exact = urgency_weights.get(
        (req.urgency_level or "normal").lower(), urgency_weights["normal"]
    )
    for donor in donors:
        if donor.donor_id in seen_donor_ids:
            continue
        if donor.blood_group not in donor_groups or not donor.is_available:
            continue
        if not is_donor_eligible(donor)["eligible"]:
            continue
        seen_donor_ids.add(donor.donor_id)
        donor_node = f"donor:{donor.donor_id}"
        donor_loc = f"location:donor:{donor.donor_id}"
        has_coords = donor.latitude is not None and donor.longitude is not None
        level = group_levels.get(donor.blood_group)
        if level is None:
            continue
        donor_node_data = {
            "id": donor_node, "type": "donor", "donor_id": donor.donor_id,
            "label": donor.user.name, "blood_group": donor.blood_group,
            "city": donor.city, "verified": bool(donor.user.is_verified),
        }
        nodes.append(donor_node_data)
        donor_nodes_by_id[donor.donor_id] = donor_node_data
        nodes_by_id[donor_node] = donor.user.name
        # This edge is the compatibility match relationship; no contact data is emitted.
        edges.append({"source": donor_node, "target": req_node, "type": "compatible_donor"})
        route_graph.setdefault(donor_node, [])
        if has_coords:
            label = donor.city or donor.address or "Donor location"
            nodes.append({"id": donor_loc, "type": "location", "label": label,
                          "latitude": donor.latitude, "longitude": donor.longitude})
            nodes_by_id[donor_loc] = label
            donor_locations[donor.donor_id] = (donor_loc, donor.latitude, donor.longitude)
            locations.append((donor_loc, donor.latitude, donor.longitude))
            add_route_edge(donor_node, donor_loc, 0.0)
            add_route_edge(donor_loc, donor_node, 0.0)
        matches.append({
            "donor_id": donor.donor_id, "name": donor.user.name,
            "blood_group": donor.blood_group, "city": donor.city,
            "is_verified": bool(donor.user.is_verified),
            "donation_count": donor.donation_count or 0,
            "last_donation_date": donor.last_donation_date.isoformat() if donor.last_donation_date else None,
            "reliability_score": calculate_donor_reliability_score(donor),
            "is_available": bool(donor.is_available), "is_eligible": True,
            "ai_score": None, "match_level": level,
            "distance_km": None, "route_distance_km": None,
            "route": [], "route_labels": [], "route_available": False,
            "match_reasons": [
                f"{donor.blood_group} is compatible with {req_group} under BloodLink's existing rules.",
                f"Blood-group match level {level} (0 is exact).",
                "Available and currently eligible to donate.",
                "Verified donor." if donor.user.is_verified else "Account is not verified.",
                f"{donor.donation_count or 0} recorded donation(s).",
            ],
        })

    # The complete routing adjacency stays private to this service.
    location_graph = _build_sparse_location_graph(locations, k=3)
    for source, neighbors in location_graph.items():
        for target, weight in neighbors:
            add_route_edge(source, target, weight)

    all_distances, all_previous = _dijkstra_tree(route_graph, req_node) if has_req_coords else ({}, {})
    for match in matches:
        donor_id = match["donor_id"]
        if has_req_coords and donor_id in donor_locations:
            distance, path = _path_from_tree(req_node, f"donor:{donor_id}", all_distances, all_previous)
            match["distance_km"] = round(distance, 3) if distance is not None else None
            match["route_distance_km"] = match["distance_km"]
            match["route"] = path
            match["route_labels"] = [nodes_by_id.get(node, node) for node in path]
            match["route_available"] = bool(path)
        distance = match["distance_km"]
        if distance is not None:
            exact = 1 if match["blood_group"] == req_group else 0
            # The specified urgency weights produce a normalized base score.
            match["ai_score"] = round(
                w_dist * (1 - min(distance / 50, 1))
                + w_rel * (match["reliability_score"] / 100)
                + w_exact * exact, 4
            )

    # Prefer closer blood-group cover levels, then score, then a coordinate-backed route.
    matches.sort(key=lambda item: (
        item["ai_score"] is not None,
        item["ai_score"] if item["ai_score"] is not None else float("-inf"),
        -item["match_level"],
    ), reverse=True)

    # Preserve one backend rank as the source of truth for both pages and graph nodes.
    routed_distances = [
        item["distance_km"] for item in matches if item["distance_km"] is not None
    ]
    shortest_distance = min(routed_distances) if routed_distances else None
    for rank, match in enumerate(matches, start=1):
        match["rank"] = rank
        match["blood_match"] = "Exact" if match["match_level"] == 0 else "Compatible"
        why = [
            "Exact blood-group match" if match["match_level"] == 0
            else f"Compatible blood group (Level {match['match_level']})",
            "Available and eligible to donate",
        ]
        if (shortest_distance is not None and match["distance_km"] is not None
                and abs(match["distance_km"] - shortest_distance) < 0.0005):
            why.append("Shortest Dijkstra distance among compatible candidates")
        if match["is_verified"]:
            why.append("Verified donor")
        why.append(f"Reliability score {match['reliability_score']}/100")
        match["why_recommended"] = why

        donor_node = donor_nodes_by_id.get(match["donor_id"])
        if donor_node is not None:
            donor_node.update({
                "rank": rank,
                "ai_score": match["ai_score"],
                "reliability_score": match["reliability_score"],
                "distance_km": match["distance_km"],
                "match_level": match["match_level"],
                "blood_match": match["blood_match"],
                "why_recommended": list(why),
            })

    # Add only edges from returned shortest paths; never serialize every routing edge.
    seen_route_edges = set()
    for match in matches:
        path = match["route"]
        for source, target in zip(path, path[1:]):
            key = (source, target)
            if key in seen_route_edges:
                continue
            seen_route_edges.add(key)
            edges.append({"source": source, "target": target, "type": "shortest_route",
                          "weight_km": round(route_weights.get(key, 0.0), 3)})

    bfs_order = group_bfs_order
    return {
        "blood_groups": list(BLOOD_GROUPS), "compatibility": compatibility,
        "cover_edges": covers, "nodes": nodes, "edges": edges, "donors": matches,
        "bfs_order": bfs_order,
        "selected_request": {"request_id": req.request_id, "blood_group": req_group,
                             "urgency_level": req.urgency_level, "location": req.location,
                             "latitude": req.latitude, "longitude": req.longitude, "status": req.status},
        "algorithm_notes": {
            "bfs": "O(V + E) using adjacency lists",
            "dijkstra": "O((V + E) log V) using a min-heap",
            "location_graph": "Undirected k=3 nearest-neighbor graph with nearest-component connectivity bridges.",
            "distance_basis": "Haversine distance between saved coordinates; straight-line, not road navigation.",
        },
    }
