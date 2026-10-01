"""Global donor assignment using urgency-ordered Kuhn bipartite matching."""
from .eligibility import is_donor_eligible
from .graph_service import compatibility_adjacency
from .utils import calculate_donor_reliability_score, haversine_distance


URGENCY_ORDER = {"critical": 0, "urgent": 1, "normal": 2}


def _request_order(request):
    urgency = (request.urgency_level or "normal").lower()
    created = request.created_at.isoformat() if request.created_at else ""
    return (URGENCY_ORDER.get(urgency, 2), created, request.request_id)


def _hall_witness(start_request, adjacency, request_match, donor_match):
    """Return the alternating-reachable Hall-deficient request/donor sets."""
    left_seen, right_seen = {start_request}, set()
    queue, cursor = [start_request], 0
    while cursor < len(queue):
        request_id = queue[cursor]
        cursor += 1
        matched_donor = request_match.get(request_id)
        for donor_id in adjacency.get(request_id, ()):
            # Alternating paths go left->right through unmatched edges.
            if donor_id == matched_donor or donor_id in right_seen:
                continue
            right_seen.add(donor_id)
            paired_request = donor_match.get(donor_id)
            if paired_request is not None and paired_request not in left_seen:
                left_seen.add(paired_request)
                queue.append(paired_request)
    return left_seen, right_seen


def assign_donors(requests, donors):
    """Assign at most one request to each available eligible compatible donor.

    Kuhn's augmenting-path algorithm finds a maximum-cardinality matching;
    requests are attempted in critical, urgent, normal order. Its worst-case
    complexity is O(VE) for this bipartite graph.
    """
    blood_graph = compatibility_adjacency()
    donor_by_id = {}
    for donor in donors:
        if donor.is_available and is_donor_eligible(donor)["eligible"]:
            donor_by_id[donor.donor_id] = donor

    request_by_id = {request.request_id: request for request in requests}
    adjacency = {}
    for request in requests:
        compatible = []
        for donor_id, donor in donor_by_id.items():
            if request.blood_group not in blood_graph.get(donor.blood_group, ()):
                continue
            if (request.latitude is not None and request.longitude is not None
                    and donor.latitude is not None and donor.longitude is not None):
                distance = haversine_distance(
                    request.latitude, request.longitude, donor.latitude, donor.longitude
                )
            else:
                distance = float("inf")
            reliability = calculate_donor_reliability_score(donor)
            compatible.append((donor_id, distance, donor.blood_group != request.blood_group,
                               -reliability))
        compatible.sort(key=lambda item: (item[2], item[1], item[3]))
        adjacency[request.request_id] = [item[0] for item in compatible]

    donor_match, request_match = {}, {}

    def augment(request_id, seen_donors):
        for donor_id in adjacency.get(request_id, ()):
            if donor_id in seen_donors:
                continue
            seen_donors.add(donor_id)
            previous_request = donor_match.get(donor_id)
            if previous_request is None or augment(previous_request, seen_donors):
                donor_match[donor_id] = request_id
                request_match[request_id] = donor_id
                return True
        return False

    ordered_requests = sorted(requests, key=_request_order)
    for blood_request in ordered_requests:
        augment(blood_request.request_id, set())

    assignments = []
    for blood_request in ordered_requests:
        donor_id = request_match.get(blood_request.request_id)
        if donor_id is not None:
            assignments.append({"request": blood_request, "donor": donor_by_id[donor_id]})

    unmatched = []
    for blood_request in ordered_requests:
        request_id = blood_request.request_id
        if request_id in request_match:
            continue
        hall_requests, hall_donors = _hall_witness(request_id, adjacency, request_match, donor_match)
        explanation = (
            f"{len(hall_requests)} active request(s) in this compatible group share only "
            f"{len(hall_donors)} available eligible donor(s). Hall's condition "
            f"|S| > |N(S)| shows they cannot all be matched at once."
        )
        unmatched.append({
            "request": blood_request,
            "hall_explanation": explanation,
            "hall_request_ids": sorted(hall_requests),
            "hall_donor_ids": sorted(hall_donors),
        })
    return {"assignments": assignments, "unmatched_requests": unmatched}
