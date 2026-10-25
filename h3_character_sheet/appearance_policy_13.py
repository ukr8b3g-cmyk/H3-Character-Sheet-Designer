"""Connected, view-scoped appearance permissions for Reference13 only."""
from .state_13 import part_views


ROLE_PARTS = {
    'face': ('face',),
    'head': ('head_hair', 'face'),
    'clothing': ('upper_clothing', 'back_clothing', 'lower_body'),
    'clothing_front': ('upper_clothing', 'lower_body'),
    'clothing_back': ('upper_clothing', 'back_clothing', 'lower_body'),
    'hands': ('hands',),
    'footwear': ('footwear',),
}
REAR_VIEWS = frozenset(('face_back', 'body_back', 'clothing_back'))


def build_appearance_policy(state, references):
    policy = []
    for reference in references:
        role = reference['role']
        scopes = {}
        for part in ROLE_PARTS.get(role, ()):
            views = part_views(state, part)
            if role == 'face':
                views = tuple(view for view in views if view not in REAR_VIEWS)
            elif role == 'clothing_front':
                views = tuple(view for view in views if view not in REAR_VIEWS)
            elif role == 'clothing_back':
                # A fixed side camera may reveal a rear garment surface.
                views = tuple(view for view in views if view in REAR_VIEWS or view == 'body_left')
            if views:
                scopes[part] = views
        if scopes:
            policy.append({**reference, 'parts': scopes})
    return tuple(policy)


def applicable_references(policy, parts, view=None):
    return tuple(reference for reference in policy
                 if any(part in reference['parts'] and
                        (view is None or view in reference['parts'][part]) for part in parts))


def reference_sources(references):
    return ', '.join(f"{item['tag']} ({item['role']})" for item in references)
