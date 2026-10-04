/**
 * Local, decorative studio mannequins with no gender or personal identity cues. These illustrations are UI-only: they
 * never enter state_json, the generation prompt, or the model's image inputs.
 * A fresh suffix protects gradients even if callers reuse an instance prefix.
 */
let avatarSequence = 0;

const VIEWS = new Set([
  "face_front", "face_left", "body_front", "body_left", "body_back", "hands", "feet",
]);

function definitions(id) {
  return `<defs>
    <linearGradient id="${id}-silver" x1="0" y1="0" x2="1" y2=".16">
      <stop stop-color="#647e89"/><stop offset=".25" stop-color="#b8cbd0"/>
      <stop offset=".47" stop-color="#e5eeee"/><stop offset=".7" stop-color="#9eb6bd"/>
      <stop offset="1" stop-color="#4f6b78"/>
    </linearGradient>
    <linearGradient id="${id}-body" x1="0" y1="0" x2=".95" y2=".35">
      <stop stop-color="#587582"/><stop offset=".25" stop-color="#c2d5d8"/>
      <stop offset=".48" stop-color="#dce6e7"/><stop offset=".77" stop-color="#91afb7"/>
      <stop offset="1" stop-color="#476474"/>
    </linearGradient>
    <linearGradient id="${id}-limb" x1="0" y1="0" x2="1" y2=".05">
      <stop stop-color="#607d89"/><stop offset=".36" stop-color="#d2e0e2"/>
      <stop offset=".65" stop-color="#abc2c8"/><stop offset="1" stop-color="#4f6a78"/>
    </linearGradient>
    <linearGradient id="${id}-boot" x1="0" y1="0" x2=".95" y2=".2">
      <stop stop-color="#3e5968"/><stop offset=".3" stop-color="#90aeb8"/>
      <stop offset=".55" stop-color="#b7cbd1"/><stop offset=".82" stop-color="#6d8d9b"/>
      <stop offset="1" stop-color="#334e60"/>
    </linearGradient>
    <linearGradient id="${id}-edge" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#f3ffff" stop-opacity=".95"/><stop offset="1" stop-color="#c6ebea" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="${id}-face" cx=".32" cy=".28" r=".85">
      <stop stop-color="#edf4f3"/><stop offset=".38" stop-color="#d0dfe0"/>
      <stop offset=".72" stop-color="#8eaab4"/><stop offset="1" stop-color="#4d6c7b"/>
    </radialGradient>
    <radialGradient id="${id}-shadow">
      <stop stop-color="#203b49" stop-opacity=".32"/><stop offset="1" stop-color="#203b49" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="${id}-glow">
      <stop stop-color="#c5eeed" stop-opacity=".19"/><stop offset="1" stop-color="#c5eeed" stop-opacity="0"/>
    </radialGradient>
  </defs>`;
}

/** Blank, hairless head: only the oval volume and unobtrusive ear forms. */
function headFront(id) {
  return `<g stroke-linecap="round" stroke-linejoin="round">
    <path d="M-22 27C-29 25-28 38-23 42L-20 37M22 27C29 25 28 38 23 42L20 37" fill="url(#${id}-silver)" stroke="#718d98" stroke-width=".55"/>
    <path d="M0-5C-16-5-25 7-24 25L-21 42C-20 54-11 64 0 65C11 64 20 54 21 42L24 25C25 7 16-5 0-5Z" fill="url(#${id}-face)" stroke="#6d8994" stroke-width=".65"/>
    <path d="M-18 17C-18 6-10 0 0 0" fill="none" stroke="url(#${id}-edge)" stroke-width="1.2" opacity=".42"/>
  </g>`;
}

/** Hands hang with separate fingers, rather than ending the arm in an oval. */
function hangingHand(id, mirror = false) {
  return `<g${mirror ? ' transform="translate(160 0) scale(-1 1)"' : ""}>
    <path d="M39 135L47 137L47 144L50 149Q51 152 49 152L46 148L46 157Q45 159 44 157L43 150L43 160Q41 162 40 159L40 151L39 160Q37 161 37 158L37 149L36 156Q34 158 34 155L35 143Z" fill="url(#${id}-limb)" stroke="#5c7b88" stroke-width=".55"/>
    <path d="M39 141L44 142M39 145L43 146" fill="none" stroke="#e9f6f1" stroke-width=".6" opacity=".55"/>
  </g>`;
}

function bodyFront(id) {
  return `
    <ellipse cx="80" cy="246" rx="44" ry="6" fill="url(#${id}-shadow)"/>
    <path d="M64 124C59 139 59 151 61 165L65 194L64 222L75 224L79 190L80 151L83 190L86 224L98 222L96 194L100 161C102 147 100 134 96 124Z" fill="url(#${id}-body)" stroke="#607f8a" stroke-width=".7"/>
    <path d="M65 142C64 159 67 169 68 184M91 144C94 156 91 173 91 183" fill="none" stroke="url(#${id}-edge)" stroke-width="2.5" opacity=".6"/>
    <path d="M79 146L78 181M66 189Q71 192 76 188M85 188Q90 192 96 188" fill="none" stroke="#5a7b87" stroke-width=".8" opacity=".5"/>
    <path d="M65 214L77 215L76 230C75 233 73 234 71 236L70 242C67 245 57 245 56 241C56 237 61 231 63 228Z" fill="url(#${id}-boot)" stroke="#4b6b7a" stroke-width=".7"/>
    <path d="M85 215L97 214L99 228C100 232 105 236 105 240C105 245 92 245 90 241L89 235L86 231Z" fill="url(#${id}-boot)" stroke="#4b6b7a" stroke-width=".7"/>
    <path d="M57 240Q63 243 70 240M91 240Q98 243 104 240M65 219L76 220M86 220L97 219" fill="none" stroke="#d0e5e7" stroke-width=".75" opacity=".6"/>
    <path d="M71 49L89 49L90 59L97 63L83 77L65 63L70 58Z" fill="url(#${id}-silver)" stroke="#698690" stroke-width=".65"/>
    <path d="M72 52Q79 58 88 52L89 58Q80 63 71 58Z" fill="#526f7d" opacity=".28"/>
    <path d="M62 64C51 60 47 71 44 88L38 116L37 140Q41 143 47 141L50 119L57 98L64 80Z" fill="url(#${id}-limb)" stroke="#5b7987" stroke-width=".7"/>
    <path d="M98 64C108 61 113 71 116 88L122 116L123 140Q120 143 113 141L110 119L103 98L97 80Z" fill="url(#${id}-limb)" stroke="#5b7987" stroke-width=".7"/>
    <path d="M48 114Q44 119 46 125M114 114Q118 119 116 125" fill="none" stroke="#658390" stroke-width=".75" opacity=".65"/>
    ${hangingHand(id)}${hangingHand(id, true)}
    <path d="M71 58C66 59 61 62 59 69C57 77 61 87 62 101L61 116L60 131Q80 138 100 131L99 116L98 101C99 87 103 77 101 69C99 62 94 59 89 58Q80 62 71 58Z" fill="url(#${id}-body)" stroke="#617f8a" stroke-width=".75"/>
    <path d="M69 62Q80 66 91 62M64 124Q80 129 96 124" fill="none" stroke="#6e8e98" stroke-width=".8" opacity=".5"/>
    <path d="M67 82C66 89 67 99 67 107" fill="none" stroke="#eaf7f2" stroke-width=".9" opacity=".65"/>
    <path d="M62 70C61 77 63 83 64 88M65 112L65 121M100 71L100 79M49 82L42 112" fill="none" stroke="url(#${id}-edge)" stroke-width="1.6" opacity=".7"/>
    <g transform="translate(80 17) scale(.55)">${headFront(id)}</g>`;
}

function bodyBack(id) {
  return `<ellipse cx="80" cy="246" rx="44" ry="6" fill="url(#${id}-shadow)"/>
    <path d="M64 123C59 139 60 157 62 171L65 195L64 222L76 225L79 190L80 153L83 190L85 225L98 222L96 194L99 168C101 151 101 136 96 124Z" fill="url(#${id}-body)" stroke="#607f8a" stroke-width=".7"/>
    <path d="M68 168L70 183M92 168L90 183" fill="none" stroke="#6c8a95" stroke-width=".85" opacity=".65"/>
    <path d="M65 215L77 216L76 233L77 241Q71 246 61 242L62 233Z" fill="url(#${id}-boot)" stroke="#4b6b7a" stroke-width=".7"/>
    <path d="M85 216L97 215L100 234L101 241Q93 247 84 242L85 233Z" fill="url(#${id}-boot)" stroke="#4b6b7a" stroke-width=".7"/>
    <path d="M62 239Q69 242 76 239M85 239Q93 243 100 239M70 220L69 234M91 220L92 234" fill="none" stroke="#d0e5e7" stroke-width=".75" opacity=".58"/>
    <path d="M71 48L89 48L91 62L80 69L69 61Z" fill="url(#${id}-silver)" stroke="#698690" stroke-width=".6"/>
    <path d="M63 65C51 60 47 72 44 88L38 116L37 141Q42 144 47 140L50 119L57 98L64 80Z" fill="url(#${id}-limb)" stroke="#5b7987" stroke-width=".7"/>
    <path d="M98 64C108 61 113 71 116 88L122 116L123 141Q119 144 113 140L110 119L103 98L97 80Z" fill="url(#${id}-limb)" stroke="#5b7987" stroke-width=".7"/>
    ${hangingHand(id)}${hangingHand(id, true)}
    <path d="M71 59C66 60 61 62 59 69C57 77 61 88 62 102L61 116L60 131Q80 138 100 131L99 116L98 102C99 88 103 77 101 69C99 62 94 60 89 59Q80 62 71 59Z" fill="url(#${id}-body)" stroke="#607f8a" stroke-width=".75"/>
    <path d="M80 74L80 120" fill="none" stroke="#5e7d89" stroke-width="1" opacity=".45"/>
    <path d="M78 77L78 112" fill="none" stroke="#e6f1ef" stroke-width="1.5" opacity=".55"/>
    <path d="M65 124Q80 129 95 124" fill="none" stroke="#6a8a95" stroke-width=".85" opacity=".55"/>
    <path d="M62 70C61 77 63 83 64 88M49 81L42 111M66 151L67 177M87 154L88 177" fill="none" stroke="url(#${id}-edge)" stroke-width="1.7" opacity=".6"/>
    <path d="M80 14C70 14 64 22 65 34C65 44 72 53 80 53C89 53 96 44 96 34C97 22 90 14 80 14Z" fill="url(#${id}-face)" stroke="#6d8994" stroke-width=".65"/>
    <path d="M69 29C69 23 73 18 80 18" fill="none" stroke="url(#${id}-edge)" stroke-width=".75" opacity=".4"/>`;
}

/** Camera sees the subject's anatomical LEFT; the nose points image-right. */
function bodyLeft(id) {
  return `<ellipse cx="81" cy="246" rx="34" ry="6" fill="url(#${id}-shadow)"/>
    <path d="M77 127L94 126C98 144 93 164 89 184L88 220L79 222L77 188L74 156Z" fill="#7895a2" stroke="#526e7d" stroke-width=".7"/>
    <path d="M79 216L89 216L90 230C94 233 106 236 105 240Q100 244 81 242L77 239Z" fill="#6a8997" stroke="#4b6b7a" stroke-width=".7"/>
    <path d="M68 127L87 128C91 144 86 163 82 186L82 223L71 224L68 187L65 155Z" fill="url(#${id}-limb)" stroke="#607f8a" stroke-width=".7"/>
    <path d="M70 145C73 155 72 169 74 180M72 190L75 212" fill="none" stroke="url(#${id}-edge)" stroke-width="2" opacity=".55"/>
    <path d="M70 215L82 215L83 230C90 233 104 234 105 240L104 243Q90 247 69 242L68 235Z" fill="url(#${id}-boot)" stroke="#4b6b7a" stroke-width=".75"/>
    <path d="M69 239Q89 243 104 240M72 220L81 220M81 230Q86 234 94 235" fill="none" stroke="#d0e5e7" stroke-width=".85" opacity=".65"/>
    <path d="M74 45L90 44L89 57L93 65L76 72L69 62Z" fill="url(#${id}-silver)" stroke="#65838f" stroke-width=".6"/>
    <path d="M75 51L88 51L87 56Q80 59 73 56Z" fill="#587585" opacity=".3"/>
    <path d="M76 58C66 61 63 72 64 86L66 105L65 117L64 131Q78 137 95 130L94 116L94 99L95 82C96 72 92 63 87 60Z" fill="url(#${id}-body)" stroke="#597b88" stroke-width=".75"/>
    <path d="M67 126Q80 130 92 126" fill="none" stroke="#60838e" stroke-width=".85" opacity=".55"/>
    <path d="M74 65C63 63 62 73 63 87L66 110L67 140Q71 144 78 141L77 114L81 88C84 75 82 68 74 65Z" fill="url(#${id}-limb)" stroke="#587885" stroke-width=".75"/>
    <path d="M68 73C65 85 69 97 70 109L71 130" fill="none" stroke="url(#${id}-edge)" stroke-width="1.9" opacity=".7"/>
    <path d="M67 137L77 137L77 145L80 150Q81 154 79 154L76 150L77 158Q77 161 75 160L72 151L73 162Q71 164 70 161L69 152L69 161Q67 164 66 160L65 149Z" fill="url(#${id}-limb)" stroke="#5c7b88" stroke-width=".55"/>
    <path d="M70 115Q73 117 76 114" fill="none" stroke="#6e8b98" stroke-width=".8"/>
    <path d="M81 14C71 14 66 22 67 33C67 43 73 51 81 53C88 54 94 50 96 44L96 40L101 38Q102 37 99 35L95 32L95 26C94 18 89 14 81 14Z" fill="url(#${id}-face)" stroke="#6d8994" stroke-width=".65"/>
    <path d="M78 31C74 30 73 39 78 41Q82 40 81 35" fill="url(#${id}-silver)" stroke="#809ba5" stroke-width=".5"/>
    <path d="M71 27C71 21 75 18 81 18" fill="none" stroke="url(#${id}-edge)" stroke-width=".8" opacity=".4"/>`;
}

function faceFront(id) {
  return `<ellipse cx="80" cy="242" rx="66" ry="9" fill="url(#${id}-shadow)"/>
    <path d="M62 138L98 138L100 163C109 171 123 174 132 185C143 198 144 219 144 238Q80 249 16 238C16 219 17 198 28 185C37 174 51 171 60 163Z" fill="url(#${id}-body)" stroke="#718c97" stroke-width=".8"/>
    <path d="M63 145Q80 157 97 145L98 155Q80 166 62 155Z" fill="#557584" opacity=".16"/>
    <path d="M31 192C25 202 24 216 24 229M65 168Q79 175 95 168" fill="none" stroke="url(#${id}-edge)" stroke-width="2" opacity=".48"/>
    <g transform="translate(80 30) scale(1.82)">${headFront(id)}</g>`;
}

/** Same anatomical-left fallback, cropped to a head-and-chest portrait. */
function faceLeft(id) {
  return `<svg x="0" y="0" width="160" height="260" viewBox="50 8 65 105" preserveAspectRatio="xMidYMid meet" overflow="hidden">${bodyLeft(id)}</svg>`;
}

/** One open hand with a thumb and four individually drawn tapered fingers. */
function detailHand(id, transform) {
  return `<g transform="${transform}" stroke-linecap="round" stroke-linejoin="round">
    <path d="M35 175L34 154C31 146 25 139 23 130L20 118L9 99Q5 90 10 87Q15 85 19 92L31 107L28 64Q27 55 32 54Q38 53 39 62L43 98L43 46Q43 38 49 38Q55 39 54 47L55 96L59 50Q60 42 65 44Q70 46 69 54L65 101L72 68Q74 61 79 63Q84 65 82 73L76 116C75 130 68 145 64 153L64 175Z" fill="url(#${id}-silver)" stroke="#5a7a89" stroke-width="1"/>
    <path d="M32 112C40 114 44 123 43 133M34 143Q45 133 58 139M44 121Q52 116 65 119M38 154Q48 158 61 154M39 162Q48 165 61 162" fill="none" stroke="#668794" stroke-width="1" opacity=".75"/>
    <path d="M31 84L39 83M44 72L53 72M58 76L66 77M69 93L77 95M25 114L30 111" fill="none" stroke="#738f9b" stroke-width=".8" opacity=".7"/>
    <path d="M32 66L35 93M48 49L49 92M63 56L61 95M76 73L70 106M28 124Q31 135 36 141M41 165L42 172" fill="none" stroke="url(#${id}-edge)" stroke-width="2" opacity=".72"/>
    <path d="M47 118Q43 129 48 141M63 129Q59 140 57 150" fill="none" stroke="#edf8f3" stroke-width="1" opacity=".42"/>
  </g>`;
}

function hands(id) {
  return `<ellipse cx="80" cy="224" rx="70" ry="10" fill="url(#${id}-shadow)"/>
    ${detailHand(id, "translate(-4 30) scale(.94)")}
    ${detailHand(id, "translate(164 30) scale(-.94 .94)")}`;
}

function detailBoot(id, transform) {
  return `<g transform="${transform}" stroke-linecap="round" stroke-linejoin="round">
    <path d="M22 36L57 37L55 106C56 116 63 123 73 127L89 132Q100 136 101 146L100 153C91 160 62 161 35 155L22 153L20 143L22 120Z" fill="url(#${id}-boot)" stroke="#4e6e7e" stroke-width="1"/>
    <path d="M22 39Q40 44 57 40L57 49Q38 52 22 48Z" fill="url(#${id}-silver)" stroke="#7694a1" stroke-width=".65"/>
    <path d="M24 119Q37 127 56 123M24 127Q42 134 60 128M22 143Q61 155 101 145L100 153Q65 164 22 153Z" fill="#405e70" fill-opacity=".48" stroke="#456779" stroke-width=".75"/>
    <path d="M25 144Q64 155 97 147M24 151L37 154M57 151L57 156M73 150L73 156M89 148L89 154" fill="none" stroke="#a0bac5" stroke-width=".8" opacity=".75"/>
    <path d="M30 54L29 103Q28 116 34 119M35 133C48 139 72 142 87 139" fill="none" stroke="url(#${id}-edge)" stroke-width="2.7" opacity=".75"/>
    <path d="M47 51L45 106Q44 114 49 117M60 127Q69 131 73 138" fill="none" stroke="#537787" stroke-width="1.1" opacity=".65"/>
    <path d="M26 109Q38 113 52 110M26 114Q38 118 53 115" fill="none" stroke="#cee2e6" stroke-width=".7" opacity=".6"/>
  </g>`;
}

function feet(id) {
  return `<ellipse cx="80" cy="221" rx="70" ry="9" fill="url(#${id}-shadow)"/>
    ${detailBoot(id, "translate(89 48) scale(-.82 .98)")}
    ${detailBoot(id, "translate(60 69) scale(.86 .96)")}`;
}

/**
 * Return an accessible-decoration SVG for a supported character-sheet view.
 * @param {string} view A canonical view ID.
 * @param {string} idPrefix A caller-owned node/card or preview identifier.
 * @returns {string} SVG markup, viewBox="0 0 160 260".
 */
export function avatarSVG(view, idPrefix = "h3-avatar") {
  if (!VIEWS.has(view)) throw new RangeError(`Unknown mannequin view: ${view}`);
  // Restrict IDs to a safe XML/CSS alphabet; do not interpolate untrusted text.
  const prefix = String(idPrefix).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 100);
  const id = `h3-${prefix}-${++avatarSequence}`;
  const art = {
    face_front: faceFront,
    face_left: faceLeft,
    body_front: bodyFront,
    body_left: bodyLeft,
    body_back: bodyBack,
    hands,
    feet,
  }[view](id);
  return `<svg xmlns="http://www.w3.org/2000/svg" class="h3-avatar h3-avatar-${view}" viewBox="0 0 160 260" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false" role="presentation">
    ${definitions(id)}
    <ellipse cx="76" cy="122" rx="76" ry="120" fill="url(#${id}-glow)"/>
    <g stroke-linejoin="round" stroke-linecap="round">${art}</g>
  </svg>`;
}
