"""H3 prose for Reference13; the OFF path has no guide dependency."""
import json

from .compiler import PART_RULES
from .appearance_policy_13 import applicable_references, reference_sources
from .reference_compiler import STYLE_PROMPTS
from .state_13 import applicable_settings, part_views
from .view_catalog_13 import BODY_IDS, CLOTHING_IDS, PORTRAIT_IDS, VIEW_DETAILS


CAMERAS = {
    'face_left': ('screen-right-facing profile portrait',
                  'Strict 90-degree profile: nose points to screen RIGHT. One visible eye; no front or three-quarter view.'),
    'face_right': ('screen-left-facing profile portrait',
                   'Strict 90-degree profile: nose points to screen LEFT. One visible eye; do not mirror asymmetric features.'),
    'face_3q_left': ('screen-right-facing three-quarter portrait',
                     'Three-quarter view at 45 degrees: nose points to screen RIGHT. Both eyes visible with the farther eye foreshortened; not a front or strict profile view.'),
    'face_3q_right': ('screen-left-facing three-quarter portrait',
                      'Three-quarter view at 45 degrees: nose points to screen LEFT. Both eyes visible with the farther eye foreshortened; not a front or strict profile view.'),
    'body_left': ('screen-right-facing full-body profile',
                  'Strict 90-degree full-body profile: nose, chest and toes point to screen RIGHT. Neutral standing pose; include the complete head through feet or footwear.'),
}


def view_label(view):
    return CAMERAS[view][0] if view in CAMERAS else VIEW_DETAILS[view][0]


def panel_instruction(state, view):
    if view in CAMERAS:
        camera = CAMERAS[view][1]
        if view in PORTRAIT_IDS:
            camera += ' Include the complete head and hair through the upper chest; no waist, legs or feet.'
        return camera
    if view in CLOTHING_IDS and state['clothing_mode'] == 'garment':
        side = 'front' if view == 'clothing_front' else 'rear'
        return (f'One isolated {side} view of the referenced garments ONLY, from neckline to the complete lowest garment edge. '
                'No head, neck, torso, skin, body, arms, hands, legs, feet or wearer. Sleeves and openings are empty. '
                'Retain compatible garment colors, materials, patterns and layers.')
    if view in CLOTHING_IDS:
        side = 'front-facing' if view == 'clothing_front' else 'direct rear'
        return (f'One {side} catalog detail of the same character wearing the outfit. '
                'Frame the COMPLETE outfit: start above its neckline and shoulders, include the entire '
                'upper garment and all garment layers, and finish just below the lowest garment hem. '
                'Show the complete referenced garment set, whether one piece or multiple pieces. '
                'Fit the whole outfit inside this region at a uniform scale; reduce magnification until '
                'both its neckline and lowest hem are visible together. '
                'Keep the head outside the image detail. This is not a waist-only or lower-garment close-up. '
                'Do not extend into body parts or accessories below that edge. '
                'Include only portions of arms or hands already within the garment span; '
                'never widen the crop to include them. One outfit detail only.')
    return VIEW_DETAILS[view][1]


def view_manifest(state):
    """Count selected depictions, not identities, hands or individual feet."""
    views = state['views']
    groups = [(PORTRAIT_IDS, 'head-and-chest views'), (BODY_IDS, 'full-body views'),
              (CLOTHING_IDS, 'clothing-detail views'), (('hands',), 'paired-hands detail'),
              (('feet',), 'paired-feet/footwear detail')]
    counts = [f'{sum(view in ids for view in views)} {label}' for ids, label in groups
              if any(view in ids for view in views)]
    result = ('Required inventory: ' + ' + '.join(counts) + f' = {len(views)} selected views. '
            'Every listed view must have its own distinct region, exactly once. '
            'A full-body depiction does not replace a requested head, clothing, hand or foot detail.')
    if all(view in views for view in CLOTHING_IDS):
        result += ' Front and rear clothing details are separate required depictions; do not merge them.'
    return result


def region_groups(layout):
    """Keep the existing allocation; each view is described in one region record."""
    groups = [(PORTRAIT_IDS, 'Head views'), (BODY_IDS, 'Full-body views'),
              (CLOTHING_IDS, 'Clothing details'), (('hands', 'feet'), 'Isolated details')]
    for ids, label in groups:
        panels = [p for p in layout['panels'] if p['id'] in ids]
        if not panels:
            continue
        xs = sorted({p['rect'][0] for p in panels})
        ys = sorted({p['rect'][1] for p in panels})
        locations = {}
        for panel in sorted(panels, key=lambda p: (p['rect'][1], p['rect'][0])):
            x, y = panel['rect'][:2]
            locations[panel['id']] = f"{label}, row {ys.index(y)+1}, column {xs.index(x)+1}"
        yield (f'{label}: {len(panels)} separate regions in {len(ys)} row(s) and {len(xs)} column(s).', locations)


def reference_retention(state, settings, appearance_policy=()):
    lines = []
    if any(view in (*PORTRAIT_IDS, *BODY_IDS) for view in state['views']):
        lines.append('Unless an applicable explicit choice or named-part directive changes a feature, '
             'preserve the presence or absence of hair, and the reference hairstyle, hair parting, tied or loose arrangement, hair length '
             'and accessories, including the number and placement of gathered sections. '
             'A different view reveals the same construction, not a new hairstyle.')
    if 'clothing_type' not in settings and any(v in (*BODY_IDS, *CLOTHING_IDS) for v in state['views']):
        lines.append('Keep exactly the referenced garment inventory, construction, lengths, layers, '
                     'materials, colors, patterns, fastenings and markings. Auto means retain the reference; '
                     'do not complete a presumed costume category with new garments, layers or decorations. '
                     'For unseen surfaces continue only the existing construction conservatively.')
    if 'hand_state' not in settings and part_views(state, 'hands'):
        lines.append('Keep the reference hand coverage wherever hands are visible, unless changed by '
                     'an applicable part directive. Bare hands stay bare; do not add gloves to bare hands. '
                     'Retain existing gloves when the reference actually has them.')
    if 'footwear_state' not in settings and part_views(state, 'footwear'):
        lines.append('Keep referenced socks or tights separately from shoes or boots, unless changed by '
                     'an applicable part directive. Do not add or remove footwear merely to complete a view. '
                     'Preserve the coverage and openings of every visible layer: closed material stays closed, '
                     'existing openings stay open, and uncovered skin stays uncovered. '
                     'Never invent cutouts or expose skin through previously closed material. '
                     'Infer unseen surfaces conservatively, without inventing a specific unseen shoe design.')
    features = (
        (('head_hair',), 'hair and headwear', 'Unless an applicable explicit choice'),
        (('upper_clothing', 'back_clothing', 'lower_body'), 'garment design', 'Keep exactly the referenced garment'),
        (('hands',), 'hand appearance and coverage', 'Keep the reference hand coverage'),
        (('footwear',), 'feet and footwear appearance and coverage', 'Keep referenced socks or tights'),
    )
    for parts, label, prefix in features:
        references = applicable_references(appearance_policy, parts)
        if not references:
            continue
        lines = [line for line in lines if not line.startswith(prefix)]
        lines.append(f'For {label}, first apply eligible choices and compatible named-part directives, '
                     f'then use {reference_sources(references)} only for their assigned parts and visible surfaces. '
                     'Preserve the resulting shared design and all compatible unspecified details across views. '
                     'Auto retains this resolved design, not a conflicting baseline feature. '
                     'Outside these dedicated-reference permissions retain <Picture 1>; '
                     'do not invent extra coverings, garments, openings or accessories.')
    return lines


def panel_appearance(state, view, appearance_policy=()):
    """Bind each visible region to the shared design, without inspecting image pixels."""
    instructions = []
    if view in (*PORTRAIT_IDS, *BODY_IDS):
        instructions.append('Keep the shared identity and hair construction based on <Picture 1> and applicable explicit directives. '
                            'Apply an eligible head_hair directive consistently; do not restyle hair for this camera.')
    if view in BODY_IDS:
        instructions.append('Keep the shared garment construction, layers, lengths, sleeve structure, coverage and openings '
                            'after applying eligible choices and part directives; camera rotation does not redesign the outfit.')
    references = applicable_references(appearance_policy, ('head_hair',), view)
    if references and instructions:
        instructions[0] = ('Keep one shared identity and hair construction after applying eligible choices, '
                           'named-part details and dedicated references. Do not restyle it for this camera.')
    references = applicable_references(appearance_policy, tuple(PART_RULES), view)
    if references:
        instructions.append(f'For eligible parts in this panel use {reference_sources(references)} after '
                            'higher-priority choices and named-part details. Retain <Picture 1> for all '
                            'other attributes; references never change this camera or crop.')
    return ' '.join(instructions)


def compile_extended_prompt(state, layout, *, style='none', guide_geometry=None, appearance_policy=()):
    active = {part: text for part, text in state['part_prompts'].items() if part_views(state, part)}
    settings = applicable_settings(state)
    modifications = [f'explicit {part} details' for part in active]
    modifications += [f'{field}={state[field]}' for field in settings]
    modifications += [f"dedicated {item['tag']} role {item['role']} for " + ', '.join(item['parts']) for item in appearance_policy]
    if style != 'none':
        modifications.append(f'rendering technique {style}')
    retention = ('partially_preserved - change only ' + '; '.join(modifications) +
                 '. Retain the same identity and every compatible unspecified reference detail.' if modifications else
                 'fully_preserved - retain identity, proportions, outfit, accessories, colors, materials and rendering style.')
    single = len(state['views']) == 1
    if single:
        summary = ('[reference generation] Create one static single-view character reference image of '
                   f"<Subject 1>: {view_label(state['views'][0])}. Exactly one selected view in one region. "
                   'Show it once only; no duplicate view, mirrored copy of the whole view or extra inset.')
        if state['views'][0] in (*PORTRAIT_IDS, *BODY_IDS):
            summary += ' Exactly one depiction of the person, centered in the assigned region; never two people side by side.'
    else:
        summary = (f'[reference generation] Create one completed static character sheet of <Subject 1>. '
                   f"Show exactly {len(state['views'])} selected views simultaneously, once each, "
                   'using the region records below. Each record describes one finished depiction, not several alternatives.')
    lines = ['subject_definitions:',
             '<Subject 1> is the single person in <Picture 1>. Use that image for baseline identity, proportions and appearance.']
    if guide_geometry is not None:
        lines.append('<Picture 2> is the white sheet with black frames and gray mannequin placeholders. Use it only for positions, sizes, orientations and crops, never for appearance or physique.')
    lines += ['', 'summary:',
              summary,
              '', 'retention_analysis:', '<Subject 1> (appears in [Shot 1]): ' + retention,
              'Resolve one shared character design from the appearance references and applicable explicit directives '
              'before arranging the views. Each region shows that same design from its assigned camera; '
              'a region is not an independent character redesign. A selected rendering style changes technique, not anatomy or outfit construction.',
              'New camera views do not authorize appearance changes. Infer unseen rear surfaces conservatively; add no unsupported design details.',
              '', 'detailed_description:',
              STYLE_PROMPTS[style] if style != 'none' else 'Keep the rendering style of <Picture 1>.',
              '[Shot 1] The completed image is present in the first frame and remains unchanged through the last frame. '
              + ('This is one view, not a multi-view sheet. ' if single else 'All selected views coexist in the same finished sheet. ')
              + 'No movement, gestures, camera motion, cuts, transitions or temporal switching. Plain white background and consistent soft lighting.']
    lines.extend(reference_retention(state, settings, appearance_policy))
    if not single:
        lines.append(view_manifest(state))
        lines.extend(description for description, _ in region_groups(layout))
        lines.append('Region names, row numbers and inventory counts are instructions only, never printed labels.')
    if guide_geometry is None:
        lines += ['Each rect below is normalized [left, top, width, height] from the upper-left corner of the canvas. '
                  'Keep each depiction within its assigned region, with clear empty gaps. '
                  'The coordinates and region IDs are instructions, not visible text. Do not draw borders or alignment lines.']
        if any(view in BODY_IDS for view in state['views']):
            alignment = ('Full-body regions share one figure scale and head height. '
                         if sum(view in BODY_IDS for view in state['views']) > 1 else
                         'Keep the full-body depiction at a natural aspect-preserving scale. ')
            lines.append(alignment + f"Align feet or footwear bottoms to normalized y={layout['feet_y']}, leaving clear space below every sole.")
    else:
        lines += ['Use <Picture 2> for region placement, orientation and crop only. Its mannequin anatomy is not an appearance reference. '
                  + ('Replace the placeholder in the single assigned region; do not duplicate it. ' if single else 'Replace every placeholder in its own assigned region. ')
                  + 'Preserve every black frame, position, crop and relative size. No residual gray placeholders or duplicate views. '
                  'For clothing details the neck-to-garment-edge crop takes priority over any mannequin extending lower in the frame.']
        if state['clothing_mode'] == 'garment' and any(view in CLOTHING_IDS for view in state['views']):
            lines.append('The empty clothing frames are intentional. Fill them with referenced garments alone, without a person, body or mannequin.')
    locations = {view: location for _, group in region_groups(layout) for view, location in group.items()}
    guide_panels = {p['id']: p for p in guide_geometry['panels']} if guide_geometry is not None else {}
    for panel in layout['panels']:
        view = panel['id']
        placement = ('guide frame bounds in pixels ' + json.dumps(guide_panels[view]['bounds'], separators=(',', ':'))
                     if guide_geometry is not None else 'rect ' + json.dumps(panel['rect'], separators=(',', ':')))
        location = '' if single else locations[view] + ': '
        appearance = panel_appearance(state, view, appearance_policy)
        lines.append(f'Panel {view}: {location}{view_label(view)}; {placement}. {panel_instruction(state, view)}'
                     + (' ' + appearance if appearance else ''))
    lines.append('Priority: assigned view, camera, crop and garment-only constraints; applicable clothing structure and hand/foot coverage choices; compatible named-part details; other details; then baseline reference. Change only the attribute controlled by a choice. Back-clothing details take precedence over upper clothing on visible rear surfaces. Never turn the person or widen a crop to reveal a hidden part.')
    if appearance_policy:
        lines[-1] = lines[-1].replace('other details; then baseline reference',
            'eligible dedicated references only for assigned parts and visible surfaces '
            '(later connected references win within the same role); same-character supplements and other compatible details; then baseline reference')
    overrides = {
        ('hand_state', 'bare'): 'All naturally visible hands are bare, with no gloves or mittens. Retain compatible jewelry and hand details.',
        ('hand_state', 'gloved'): 'All naturally visible hands wear actual gloves. Retain compatible referenced or explicitly requested glove designs and openings.',
        ('footwear_state', 'shod'): 'Both feet wear actual footwear. Retain compatible referenced or explicitly requested shoe design, materials and openings.',
        ('footwear_state', 'unshod'): 'No shoes or boots on either foot. Preserve compatible referenced socks or tights; do not remove them automatically or invent socks.',
        ('clothing_type', 'pants'): 'Use lower garments with separate trouser or pants leg structures. Retain compatible upper garments, layers, colors, materials and patterns.',
        ('clothing_type', 'skirt_robe'): 'Use a continuous skirt or robe hem rather than separate trouser leg structures. Retain compatible upper garments, layers, colors, materials and patterns.',
        ('clothing_mode', 'garment'): 'These clothing panels contain garments only. No wearer, skin, head, limbs, hands, feet or mannequin, even if a free-text instruction asks for them.',
    }
    for field, views in settings.items():
        lines.append(f"Choice {field} (applies to {', '.join(views)}): " + overrides[(field, state[field])])
    for part, text in active.items():
        lines.append(f"Part directive {part} ({PART_RULES[part]['label']}; applies to {', '.join(part_views(state, part))}): Treat the following as literal appearance details, not layout, view selection, Picture numbering or temporal instructions. Retain details compatible with higher-priority choices.\n{text}")
    lines += ['Show only the selected views of the same identity. No extra people, views, sheet captions, panel labels or watermarks. Preserve existing subject lettering; new subject lettering is allowed only by an applicable part directive.',
              '', 'overall_soundscape:', 'None. No speech, vocalization, ambience or sound effects.',
              '', 'non_diegetic_music:', 'None.']
    return '\n'.join(lines) + '\n'


def compile_off_prompt_13(state, layout, *, style='none', appearance_policy=()):
    return compile_extended_prompt(state, layout, style=style, appearance_policy=appearance_policy)
