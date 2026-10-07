// Walter's Home Check — "My Home" maintenance rules.
//
// Each rule is one recurring job around the house. You can change the words
// between the quotes (title, why, pro). Please keep each "id" exactly as it is:
// people's "Done" ticks and hidden tasks are saved by id.
//
//   id       — never change once published
//   title    — the task, short
//   why      — Walter's one-line reason (why it matters)
//   whyFamily— (optional) wording used instead when kids or older adults live at home
//   months   — month numbers 1–12, and/or season names from SEASONS below
//              (a season name picks the right month for the home's climate)
//   condition— (optional) which homes it applies to. p = the home's details,
//              c = { climate, year }. Leave it out to apply to every home.
//   minutes  — rough time it takes
//   diy      — true = "Do it myself", false = "Call a pro"
//   pro      — who to call (when diy is false, or when something looks wrong)
//   safety   — true = a safety job (shown with a Safety tag)
//   system   — which part of the house (used for the logbook filter too)

// Climate groups. The home's US state picks one; people can change it.
export const CLIMATES = {
  cold: 'Cold winters',
  mixed: 'Mixed',
  hothumid: 'Hot & humid',
  hotdry: 'Hot & dry',
};

// State → climate group. A rough guide only; people can override it.
export const STATES = [
  ['AL', 'Alabama', 'hothumid'], ['AK', 'Alaska', 'cold'], ['AZ', 'Arizona', 'hotdry'], ['AR', 'Arkansas', 'mixed'],
  ['CA', 'California', 'hotdry'], ['CO', 'Colorado', 'cold'], ['CT', 'Connecticut', 'cold'], ['DE', 'Delaware', 'mixed'],
  ['DC', 'District of Columbia', 'mixed'], ['FL', 'Florida', 'hothumid'], ['GA', 'Georgia', 'hothumid'], ['HI', 'Hawaii', 'hothumid'],
  ['ID', 'Idaho', 'cold'], ['IL', 'Illinois', 'cold'], ['IN', 'Indiana', 'cold'], ['IA', 'Iowa', 'cold'],
  ['KS', 'Kansas', 'mixed'], ['KY', 'Kentucky', 'mixed'], ['LA', 'Louisiana', 'hothumid'], ['ME', 'Maine', 'cold'],
  ['MD', 'Maryland', 'mixed'], ['MA', 'Massachusetts', 'cold'], ['MI', 'Michigan', 'cold'], ['MN', 'Minnesota', 'cold'],
  ['MS', 'Mississippi', 'hothumid'], ['MO', 'Missouri', 'mixed'], ['MT', 'Montana', 'cold'], ['NE', 'Nebraska', 'cold'],
  ['NV', 'Nevada', 'hotdry'], ['NH', 'New Hampshire', 'cold'], ['NJ', 'New Jersey', 'mixed'], ['NM', 'New Mexico', 'hotdry'],
  ['NY', 'New York', 'cold'], ['NC', 'North Carolina', 'mixed'], ['ND', 'North Dakota', 'cold'], ['OH', 'Ohio', 'cold'],
  ['OK', 'Oklahoma', 'mixed'], ['OR', 'Oregon', 'mixed'], ['PA', 'Pennsylvania', 'cold'], ['RI', 'Rhode Island', 'cold'],
  ['SC', 'South Carolina', 'hothumid'], ['SD', 'South Dakota', 'cold'], ['TN', 'Tennessee', 'mixed'], ['TX', 'Texas', 'hothumid'],
  ['UT', 'Utah', 'cold'], ['VT', 'Vermont', 'cold'], ['VA', 'Virginia', 'mixed'], ['WA', 'Washington', 'mixed'],
  ['WV', 'West Virginia', 'mixed'], ['WI', 'Wisconsin', 'cold'], ['WY', 'Wyoming', 'cold'],
];

// Season names → month number for each climate group.
export const SEASONS = {
  'early-spring': { cold: 4, mixed: 3, hothumid: 2, hotdry: 2 },
  spring: { cold: 5, mixed: 4, hothumid: 3, hotdry: 3 },
  'late-spring': { cold: 6, mixed: 5, hothumid: 4, hotdry: 4 },
  'late-summer': { cold: 8, mixed: 8, hothumid: 8, hotdry: 8 },
  'early-fall': { cold: 9, mixed: 9, hothumid: 10, hotdry: 10 },
  fall: { cold: 10, mixed: 10, hothumid: 11, hotdry: 11 },
  'late-fall': { cold: 11, mixed: 11, hothumid: 12, hotdry: 12 },
  'pre-freeze': { cold: 10, mixed: 11, hothumid: 12, hotdry: 12 },
  winter: { cold: 1, mixed: 1, hothumid: 1, hotdry: 1 },
  'late-winter': { cold: 3, mixed: 2, hothumid: 2, hotdry: 2 },
  'before-rainy': { cold: 9, mixed: 9, hothumid: 5, hotdry: 10 },
};

// Parts of the house (for tags and the logbook filter).
export const SYSTEMS = {
  roof: 'Roof & gutters',
  hvac: 'Heating & cooling',
  'water-heater': 'Water heater',
  plumbing: 'Plumbing & water',
  electrical: 'Electrical',
  safety: 'Safety',
  appliances: 'Kitchen & laundry',
  outside: 'Outside & yard',
  basement: 'Basement & foundation',
  other: 'Other',
};

// ----- Small helpers used by the conditions below -----
const ALL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
const yes = (v) => v === true;
const notNo = (v) => v !== false; // yes, or "not sure"
const furnace = (p) => /furnace$/.test(p.heatingType || '');
const boiler = (p) => /boiler$/.test(p.heatingType || '');
const heatPump = (p) => p.heatingType === 'heat-pump';
const anyHeat = (p) => p.heatingType !== 'none';
const cooling = (p) => yes(p.centralAC) || heatPump(p);
const hasFilter = (p) => !p.heatingType || furnace(p) || heatPump(p) || yes(p.centralAC);
const tankHeater = (p) => p.waterHeaterType !== 'tankless';
const gasHome = (p) =>
  /^gas-/.test(p.heatingType || '') || p.waterHeaterType === 'tank-gas' || (!p.heatingType && !p.waterHeaterType);
const coldish = (c) => c.climate === 'cold' || c.climate === 'mixed';
const notSlab = (p) => p.foundation !== 'slab';
const yearsSince = (year, c) => (year ? c.year - Number(year) : Infinity);

export const RULES = [
  // ---------- Roof & gutters ----------
  {
    id: 'gutters-spring', system: 'roof', title: 'Clean the gutters and check the downspouts',
    why: 'Clogged gutters spill water right next to the foundation — and that is how basements get wet.',
    months: ['spring'], condition: (p) => notNo(p.gutters), minutes: 60, diy: true, safety: true,
    pro: 'Gutter cleaning service (if you would rather stay off the ladder)',
  },
  {
    id: 'gutters-fall', system: 'roof', title: 'Clean the gutters after the leaves come down',
    why: 'One fall cleaning keeps winter rain and snowmelt going where it should.',
    months: ['late-fall'], condition: (p) => notNo(p.gutters), minutes: 60, diy: true, safety: true,
    pro: 'Gutter cleaning service (if you would rather stay off the ladder)',
  },
  {
    id: 'downspouts', system: 'roof', title: 'Make sure downspouts empty 4–6 feet from the house',
    why: 'A cheap extension piece can save you a wet basement.',
    months: ['early-spring'], condition: (p) => notNo(p.gutters), minutes: 15, diy: true,
  },
  {
    id: 'roof-look', system: 'roof', title: 'Look over the roof from the ground',
    why: 'Binoculars from the yard show missing shingles and loose flashing — no ladder needed.',
    months: ['spring', 'fall'], minutes: 15, diy: true, pro: 'Roofer',
  },
  {
    id: 'attic-look', system: 'roof', title: 'Peek into the attic for leaks and stains',
    why: 'Look for wet spots, dark stains or daylight — and check again after any big storm.',
    months: ['spring', 'fall'], minutes: 15, diy: true, safety: true, pro: 'Roofer',
  },
  {
    id: 'ice-dams', system: 'roof', title: 'Watch for ice dams and heavy snow on the roof',
    why: 'Thick ice at the roof edge can push water under the shingles. Stay off a snowy roof — use a roof rake from the ground or call a pro.',
    months: [12, 1, 2], condition: (p, c) => c.climate === 'cold', minutes: 10, diy: true, safety: true,
    pro: 'Roofer or snow removal service',
  },
  {
    id: 'trim-trees', system: 'roof', title: 'Have branches trimmed back from the roof',
    why: 'Branches rubbing the roof wear it out, and big limbs can come down in a storm. Anything near power lines is a job for a pro.',
    months: ['late-winter'], minutes: 30, diy: false, safety: true, pro: 'Tree service / arborist',
  },

  // ---------- Heating & cooling ----------
  {
    id: 'hvac-filter', system: 'hvac', title: 'Check the furnace / AC filter — replace it if dirty',
    why: 'Most filters need changing every 1–3 months. A clean filter means easier breathing and a system that works less hard.',
    months: [1, 3, 5, 7, 9, 11], condition: hasFilter, minutes: 10, diy: true,
  },
  {
    id: 'heating-tuneup', system: 'hvac', title: 'Book a heating tune-up before the cold weather',
    why: 'A yearly check-up catches small problems early and makes sure the system runs safely.',
    months: ['early-fall'], condition: anyHeat, minutes: 10, diy: false, safety: true, pro: 'HVAC technician',
  },
  {
    id: 'ac-tuneup', system: 'hvac', title: 'Book an AC tune-up before the hot weather',
    why: 'Better to find a problem in spring than on the first hot day of summer, when everyone is calling.',
    months: ['spring'], condition: cooling, minutes: 10, diy: false, pro: 'HVAC technician',
  },
  {
    id: 'ac-outdoor-clear', system: 'hvac', title: 'Clear leaves and weeds around the outdoor AC unit',
    why: 'It needs about 2 feet of open space to breathe. Just tidy around it — leave the panels on.',
    months: ['late-spring'], condition: cooling, minutes: 15, diy: true, pro: 'HVAC technician',
  },
  {
    id: 'heatpump-winter', system: 'hvac', title: 'Keep the outdoor heat pump clear for winter',
    why: 'Leaves, snow and ice piled around it make it struggle. Keep a clear space around the unit all winter.',
    months: ['fall'], condition: heatPump, minutes: 15, diy: true, pro: 'HVAC technician',
  },
  {
    id: 'ac-drain', system: 'hvac', title: 'Check that the AC drain line is dripping outside',
    why: 'A clogged drain line can overflow inside and cause water damage you don\'t notice right away.',
    months: [7], condition: cooling, minutes: 10, diy: true, pro: 'HVAC technician',
  },
  {
    id: 'vents-clear', system: 'hvac', title: 'Vacuum the vents and keep furniture off them',
    why: 'Blocked vents make some rooms too hot or too cold and make the system work harder.',
    months: ['early-fall'], condition: (p) => anyHeat(p) || cooling(p), minutes: 20, diy: true,
  },
  {
    id: 'boiler-look', system: 'hvac', title: 'Look over the boiler and radiators',
    why: 'Look for drips, rust or a pressure gauge outside the normal range. If anything looks off, call a pro — don\'t adjust it yourself.',
    months: ['early-fall'], condition: boiler, minutes: 15, diy: true, pro: 'HVAC technician / boiler service',
  },
  {
    id: 'oil-tank', system: 'hvac', title: 'Check the heating oil level and look at the tank',
    why: 'Order oil before you run low, and watch for rust, damp spots or an oil smell around the tank.',
    months: ['early-fall'], condition: (p) => /^oil-/.test(p.heatingType || ''), minutes: 10, diy: true,
    pro: 'Heating oil company',
  },
  {
    id: 'gas-appliances', system: 'hvac', title: 'Look over the gas appliances',
    why: 'Vent pipes should be firmly connected and flames mostly blue, with no soot. If you ever smell gas, leave the house and call the gas company from outside.',
    months: ['early-fall'], condition: gasHome, minutes: 10, diy: true, safety: true, pro: 'HVAC technician or plumber',
  },

  // ---------- Water heater ----------
  {
    id: 'wh-flush', system: 'water-heater', title: 'Have the water heater flushed',
    why: 'Sediment builds up in the bottom of the tank. A yearly flush helps it last longer and run quieter.',
    months: ['early-spring'], condition: tankHeater, minutes: 10, diy: false, pro: 'Plumber',
  },
  {
    id: 'wh-relief-valve', system: 'water-heater', title: 'Test the water heater relief valve',
    why: 'This valve keeps the tank from building up too much pressure. Lift the lever briefly with a bucket under the pipe — the water is scalding, so keep hands clear. If it keeps dripping afterward, call a plumber.',
    months: ['fall'], condition: tankHeater, minutes: 10, diy: true, safety: true, pro: 'Plumber',
  },
  {
    id: 'tankless-descale', system: 'water-heater', title: 'Have the tankless water heater descaled',
    why: 'Mineral buildup slowly chokes a tankless heater. Once a year keeps it working well — more often with hard water.',
    months: ['spring'], condition: (p) => p.waterHeaterType === 'tankless', minutes: 10, diy: false, pro: 'Plumber',
  },
  {
    id: 'wh-look', system: 'water-heater', title: 'Look around the water heater for rust or drips',
    why: 'Water on the floor or rust at the bottom of the tank is an early warning. Better to plan a replacement than mop up a flood.',
    months: [2, 5, 8, 11], minutes: 5, diy: true, pro: 'Plumber',
  },
  {
    id: 'hot-water-temp', system: 'water-heater', title: 'Check how hot the tap water gets',
    why: 'About 120°F is hot enough for most homes and saves energy. Check it at the kitchen tap with a cooking thermometer.',
    whyFamily: 'With kids or older adults at home, scalding is a real risk. About 120°F at the tap is a safe target — check it with a cooking thermometer, and have a plumber adjust it if it\'s much hotter.',
    months: [1], minutes: 10, diy: true, safety: true, pro: 'Plumber',
  },

  // ---------- Plumbing & water ----------
  {
    id: 'leak-check', system: 'plumbing', title: 'Look under sinks and around toilets for leaks',
    why: 'A slow drip under a cabinet can rot the floor for months before you notice.',
    months: [1, 4, 7, 10], minutes: 15, diy: true, pro: 'Plumber',
  },
  {
    id: 'main-shutoff', system: 'plumbing', title: 'Find and gently turn the main water shut-off',
    why: 'In a burst-pipe emergency, you want to know where it is and that it turns. If it\'s stiff, don\'t force it — have a plumber look.',
    months: [3], minutes: 10, diy: true, pro: 'Plumber',
  },
  {
    id: 'toilet-dye', system: 'plumbing', title: 'Do the food-coloring test on each toilet',
    why: 'A few drops in the tank; if color shows in the bowl after 15 minutes without flushing, the flapper is leaking water all day.',
    months: [9], minutes: 20, diy: true,
  },
  {
    id: 'tub-caulk', system: 'plumbing', title: 'Check the caulk around tubs, showers and sinks',
    why: 'Cracked caulk lets water get behind the tile, where it quietly does damage.',
    months: [2], minutes: 20, diy: true,
  },
  {
    id: 'washer-hoses', system: 'plumbing', title: 'Look at the washing machine hoses',
    why: 'Bulges or cracks mean replace them now. Braided steel hoses are a cheap upgrade over rubber.',
    months: [4], minutes: 10, diy: true, pro: 'Plumber',
  },
  {
    id: 'aerators', system: 'plumbing', title: 'Clean faucet aerators and showerheads',
    why: 'Mineral buildup slows the flow. A soak in vinegar usually does the trick.',
    months: [8], minutes: 30, diy: true,
  },
  {
    id: 'faucets-off', system: 'plumbing', title: 'Disconnect hoses and shut off outdoor faucets',
    why: 'A hose left connected can freeze and split the pipe inside the wall. Shut the inside valve if you have one, and leave the outside tap open to drain.',
    months: ['pre-freeze'], condition: (p, c) => coldish(c), minutes: 20, diy: true, pro: 'Plumber',
  },
  {
    id: 'faucets-on', system: 'plumbing', title: 'Turn outdoor faucets back on and check for leaks',
    why: 'Run each one and check inside the wall behind it — a pipe that split over winter shows up now.',
    months: ['spring'], condition: (p, c) => coldish(c), minutes: 15, diy: true, pro: 'Plumber',
  },
  {
    id: 'pipe-insulation', system: 'plumbing', title: 'Insulate pipes in cold spots before the freeze',
    why: 'Pipes in a crawlspace, garage or outside wall are the ones that freeze. Foam sleeves are cheap and easy.',
    months: ['pre-freeze'], condition: (p, c) => coldish(c), minutes: 60, diy: true, pro: 'Plumber',
  },
  {
    id: 'cold-snap', system: 'plumbing', title: 'Make a plan for very cold nights',
    why: 'On the coldest nights, open the cabinet doors under sinks on outside walls and let a faucet drip.',
    months: [12], condition: (p, c) => coldish(c), minutes: 5, diy: true,
  },
  {
    id: 'sump-spring', system: 'plumbing', title: 'Test the sump pump',
    why: 'Slowly pour a bucket of water into the pit. The pump should start on its own and empty it. Better to find out now than during a storm.',
    months: ['early-spring'], condition: (p) => yes(p.sumpPump), minutes: 15, diy: true, pro: 'Plumber or waterproofing contractor',
  },
  {
    id: 'sump-rainy', system: 'plumbing', title: 'Test the sump pump before the rainy season',
    why: 'Same bucket test as in spring. Also check that the outside discharge pipe is clear.',
    months: ['before-rainy'], condition: (p) => yes(p.sumpPump), minutes: 15, diy: true, pro: 'Plumber or waterproofing contractor',
  },
  {
    id: 'well-test', system: 'plumbing', title: 'Have your well water tested',
    why: 'A private well isn\'t tested by anyone else. Once a year for bacteria and nitrates is the usual advice — your county health department can point you to a lab.',
    months: [5], condition: (p) => yes(p.well), minutes: 30, diy: false, safety: true, pro: 'State-certified water testing lab',
  },
  {
    id: 'well-cap', system: 'plumbing', title: 'Look at the well cap',
    why: 'The cap should be tight and undamaged, and the ground should slope away from it so surface water stays out.',
    months: ['spring'], condition: (p) => yes(p.well), minutes: 10, diy: true, pro: 'Licensed well contractor',
  },
  {
    id: 'septic-pump', system: 'plumbing', title: 'Septic tank: time to have it pumped',
    why: 'Most tanks need pumping every 3–5 years. Not sure when it was last done? Call a septic company — they can tell you from the tank.',
    months: ['spring'],
    condition: (p, c) => yes(p.septic) && yearsSince(p.septicPumpedYear, c) >= 3,
    minutes: 15, diy: false, pro: 'Licensed septic company',
  },
  {
    id: 'septic-field', system: 'plumbing', title: 'Walk over the septic drain field',
    why: 'Soggy spots, a sewage smell or extra-green grass over the field are early signs of trouble.',
    months: ['late-spring'], condition: (p) => yes(p.septic), minutes: 10, diy: true, pro: 'Licensed septic company',
  },

  // ---------- Safety ----------
  {
    id: 'alarms-test', system: 'safety', title: 'Test every smoke and CO alarm',
    why: 'Press the test button on each one. It takes a few minutes and it\'s the most important job on this list.',
    whyFamily: 'Press the test button on each one. With kids or older adults at home, make sure everyone knows the sound and where to go.',
    months: ALL, minutes: 10, diy: true, safety: true,
  },
  {
    id: 'alarm-batteries', system: 'safety', title: 'Change the smoke and CO alarm batteries',
    why: 'An easy habit: do it when the clocks change. Sealed 10-year alarms don\'t need it. Use a sturdy step stool, not a chair.',
    months: [3, 11], minutes: 20, diy: true, safety: true,
  },
  {
    id: 'alarm-dates', system: 'safety', title: 'Check the dates on the back of your alarms',
    why: 'Smoke alarms should be replaced every 10 years, and CO alarms usually every 5–7. The date is printed on the back.',
    months: [1], minutes: 10, diy: true, safety: true,
  },
  {
    id: 'extinguisher', system: 'safety', title: 'Check the fire extinguisher',
    why: 'The needle should be in the green, the pin in place, and it should be easy to grab — kitchen and garage are good spots.',
    months: [1, 7], minutes: 5, diy: true, safety: true,
  },
  {
    id: 'escape-plan', system: 'safety', title: 'Walk through your fire escape plan',
    why: 'Two ways out of every bedroom and one meeting spot outside. October is Fire Prevention Month — a good reminder.',
    whyFamily: 'Two ways out of every bedroom and one meeting spot outside. Practice with the kids, and plan who helps anyone who moves slowly.',
    months: [10], minutes: 15, diy: true, safety: true,
  },
  {
    id: 'emergency-kit', system: 'safety', title: 'Check your emergency kit',
    why: 'Flashlights, fresh batteries, water, a first-aid kit and any medicines you need for a few days.',
    months: [9], minutes: 20, diy: true, safety: true,
  },
  {
    id: 'stair-rails', system: 'safety', title: 'Give the stair railings a firm shake',
    why: 'Handrails should be solid, inside and out. A loose one is an easy fix for a handyman.',
    whyFamily: 'With kids or older adults at home, solid handrails matter. Check every stair, inside and out — a loose one is an easy fix for a handyman.',
    months: ['early-fall'], minutes: 10, diy: true, safety: true, pro: 'Handyman',
  },
  {
    id: 'locks-windows', system: 'safety', title: 'Check door and window locks',
    why: 'Locks should catch properly, and bedroom windows should still open easily in case you need to get out.',
    whyFamily: 'Locks should catch properly and bedroom windows should open easily for escape. With young kids, use window stops or guards that an adult can release quickly.',
    months: [6], minutes: 20, diy: true, safety: true, pro: 'Locksmith or handyman',
  },
  {
    id: 'radon', system: 'safety', title: 'Test for radon',
    why: 'Radon is an invisible gas that can seep up from the ground. A home test kit is cheap; test every 2 years, and in winter when windows are closed. At 4 pCi/L or higher, call a radon mitigation contractor.',
    months: ['winter'], condition: (p, c) => yearsSince(p.radonTestYear, c) >= 2, minutes: 15, diy: true, safety: true,
    pro: 'Radon mitigation contractor (if the result is high)',
  },
  {
    id: 'home-inventory', system: 'other', title: 'Update your home inventory photos',
    why: 'A quick video of each room makes an insurance claim much easier. Keep a copy off the phone, too.',
    months: [1], minutes: 30, diy: true,
  },

  // ---------- Electrical ----------
  {
    id: 'gfci-test', system: 'electrical', title: 'Press TEST and RESET on the GFCI outlets',
    why: 'These outlets in kitchens, baths, garages and outside protect you from shocks. If one won\'t trip or reset, call an electrician.',
    months: ALL, minutes: 10, diy: true, safety: true, pro: 'Electrician',
  },
  {
    id: 'panel-look', system: 'electrical', title: 'Look at the electrical panel area',
    why: 'Keep the area dry and clear. Look and listen only — scorch marks, buzzing, warm breakers or a burning smell mean call an electrician. Never take the cover off.',
    months: [7], minutes: 5, diy: true, safety: true, pro: 'Electrician',
  },
  {
    id: 'bath-fans', system: 'electrical', title: 'Clean the bathroom exhaust fan covers',
    why: 'Hold a tissue to the cover with the fan on — it should pull. A weak or noisy fan lets moisture build up and mold grow.',
    months: [2], minutes: 20, diy: true, pro: 'Electrician',
  },

  // ---------- Kitchen & laundry ----------
  {
    id: 'dryer-vent', system: 'appliances', title: 'Have the dryer vent duct cleaned',
    why: 'Lint packed in the duct is a leading cause of house fires, and it makes drying slow. Once a year is about right.',
    months: [9], minutes: 10, diy: false, safety: true, pro: 'Dryer vent cleaning service',
  },
  {
    id: 'dryer-flap', system: 'appliances', title: 'Check the dryer vent flap outside',
    why: 'With the dryer running, the flap outside should open and blow warm air. If it doesn\'t, the duct may be clogged.',
    months: [3], minutes: 5, diy: true, safety: true, pro: 'Dryer vent cleaning service',
  },
  {
    id: 'range-hood', system: 'appliances', title: 'Clean the range hood filter',
    why: 'A greasy filter doesn\'t pull smoke and steam — and grease can catch fire. Hot soapy water usually does it.',
    months: [2, 5, 8, 11], minutes: 15, diy: true, safety: true,
  },
  {
    id: 'fridge-coils', system: 'appliances', title: 'Vacuum the refrigerator coils',
    why: 'Dusty coils make the fridge work harder and wear out sooner. Unplug it first.',
    months: [6], minutes: 20, diy: true,
  },
  {
    id: 'dishwasher-filter', system: 'appliances', title: 'Clean the dishwasher filter',
    why: 'A clean filter means cleaner dishes and fewer smells. Most twist out from the bottom of the tub.',
    months: [3, 9], minutes: 10, diy: true,
  },

  // ---------- Outside & yard ----------
  {
    id: 'grading', system: 'outside', title: 'Check that the ground slopes away from the house',
    why: 'Walk all the way around. Soil and mulch should slope away from the foundation so rain runs off, not in.',
    months: ['early-spring'], minutes: 20, diy: true, pro: 'Landscaper / grading contractor',
  },
  {
    id: 'caulk-weatherstrip', system: 'outside', title: 'Check caulk and weatherstripping on windows and doors',
    why: 'Small gaps let in drafts, water and bugs. A tube of caulk and some weatherstripping go a long way.',
    months: ['fall'], minutes: 45, diy: true,
  },
  {
    id: 'siding-paint', system: 'outside', title: 'Look at siding and trim for peeling paint or rot',
    why: 'Paint protects the wood. Catching soft spots early is a small repair instead of a big one.',
    months: ['late-spring'], minutes: 20, diy: true, pro: 'Painter or carpenter',
  },
  {
    id: 'screens', system: 'outside', title: 'Check window screens and clean the window tracks',
    why: 'Torn screens let bugs in, and clogged tracks keep rainwater from draining out.',
    months: ['late-spring'], minutes: 30, diy: true,
  },
  {
    id: 'window-wells', system: 'outside', title: 'Clear leaves out of basement window wells',
    why: 'A window well full of leaves holds water right against the basement window.',
    months: ['fall'], condition: (p) => p.foundation === 'basement', minutes: 15, diy: true,
  },
  {
    id: 'walkways', system: 'outside', title: 'Look for trip hazards on walks and steps',
    why: 'Raised sidewalk edges, loose pavers and wobbly steps are easy to miss until someone trips.',
    whyFamily: 'With kids or older adults at home, a raised sidewalk edge or wobbly step is a real fall risk. Mark it or fix it now.',
    months: ['late-spring'], minutes: 15, diy: true, safety: true, pro: 'Concrete or masonry contractor',
  },
  {
    id: 'outdoor-lights', system: 'outside', title: 'Check outdoor and walkway lights',
    why: 'Days are short now. Replace burned-out bulbs so walks and steps are lit.',
    months: ['late-fall'], minutes: 15, diy: true, safety: true,
  },
  {
    id: 'deck-inspect', system: 'outside', title: 'Inspect the deck',
    why: 'Look for loose boards, wobbly railings, soft wood, rusty fasteners — and where the deck attaches to the house. If anything moves, stay off and call a pro.',
    months: ['late-spring'], condition: (p) => yes(p.deck), minutes: 30, diy: true, safety: true, pro: 'Deck builder or carpenter',
  },
  {
    id: 'deck-seal', system: 'outside', title: 'See if the deck needs sealing',
    why: 'Sprinkle some water on the boards. If it soaks in instead of beading up, it\'s time to clean and seal — usually every 2–3 years.',
    months: ['late-spring'], condition: (p) => yes(p.deck), minutes: 15, diy: true,
  },
  {
    id: 'garage-door', system: 'outside', title: 'Test the garage door safety reverse',
    why: 'Lay a roll of paper towels where the door closes — it should touch it and go back up. If not, call a garage door company. Never adjust the springs yourself.',
    months: [4, 10], minutes: 10, diy: true, safety: true, pro: 'Garage door company',
  },
  {
    id: 'pests-spring', system: 'outside', title: 'Look for signs of pests',
    why: 'Droppings, chewed wood, or thin mud tubes on the foundation (a sign of termites). Termites are a job for a pest control company.',
    months: ['spring'], minutes: 20, diy: true, pro: 'Pest control company',
  },
  {
    id: 'pests-fall', system: 'outside', title: 'Seal gaps where mice can get in',
    why: 'Mice look for a warm place in the fall and fit through a gap the size of a dime. Steel wool and caulk work well.',
    months: ['fall'], condition: (p, c) => coldish(c), minutes: 30, diy: true, pro: 'Pest control company',
  },
  {
    id: 'snow-ready', system: 'outside', title: 'Get ready for snow',
    why: 'Shovels, ice melt and a snowblower that starts — before the first storm, not during it.',
    months: ['late-fall'], condition: (p, c) => c.climate === 'cold', minutes: 30, diy: true,
  },
  {
    id: 'hurricane-prep', system: 'outside', title: 'Get ready for hurricane season',
    why: 'Check shutters or plywood, clear the yard of loose items, stock supplies, and take photos of the house for insurance.',
    months: [6], condition: (p, c) => c.climate === 'hothumid', minutes: 60, diy: true, safety: true,
  },
  {
    id: 'hurricane-midseason', system: 'outside', title: 'Mid-season check of hurricane supplies',
    why: 'Late summer is the busiest part of hurricane season. Restock water and batteries, and know your evacuation route.',
    months: [8], condition: (p, c) => c.climate === 'hothumid', minutes: 20, diy: true, safety: true,
  },
  {
    id: 'wildfire-space', system: 'outside', title: 'Clear a defensible space around the house',
    why: 'Clear dry brush, dead leaves and anything that burns within 5 feet of the house, and keep the roof and gutters clean.',
    months: ['spring'], condition: (p, c) => c.climate === 'hotdry', minutes: 120, diy: true, safety: true,
    pro: 'Landscaper or tree service',
  },
  {
    id: 'chimney', system: 'outside', title: 'Have the chimney inspected and swept',
    why: 'Creosote buildup and cracked flue liners cause chimney fires. Book it in late summer, before the fall rush.',
    months: ['late-summer'], condition: (p) => yes(p.fireplace), minutes: 10, diy: false, safety: true,
    pro: 'Certified chimney sweep',
  },
  {
    id: 'fireplace-first-fire', system: 'outside', title: 'Before the first fire of the season',
    why: 'Open the damper and look up with a flashlight for nests or blockages, and test the CO alarm nearby.',
    months: ['fall'], condition: (p) => yes(p.fireplace), minutes: 10, diy: true, safety: true, pro: 'Certified chimney sweep',
  },

  // ---------- Basement & foundation ----------
  {
    id: 'foundation-walk', system: 'basement', title: 'Walk around the foundation and look for cracks',
    why: 'Hairline cracks are common. Cracks wider than 1/4 inch, stair-step cracks, or ones that grow are worth having a structural engineer look at.',
    months: ['early-spring', 'fall'], minutes: 20, diy: true, pro: 'Structural engineer',
  },
  {
    id: 'basement-moisture', system: 'basement', title: 'Check the basement or crawlspace after heavy rain',
    why: 'Look for water, damp spots or a musty smell. Water problems are much cheaper to fix early.',
    months: ['early-spring', 'fall'], condition: notSlab, minutes: 15, diy: true, pro: 'Waterproofing contractor',
  },
  {
    id: 'crawlspace-look', system: 'basement', title: 'Look into the crawlspace',
    why: 'From the hatch with a good flashlight: the plastic ground cover should be in place, with no standing water or pests. Don\'t crawl in if you see wires down or animals — call a pro.',
    months: ['late-spring'], condition: (p) => p.foundation === 'crawlspace', minutes: 15, diy: true, safety: true,
    pro: 'Crawlspace or pest control contractor',
  },
  {
    id: 'humidity', system: 'basement', title: 'Check basement humidity',
    why: 'Below about 60% keeps mold and musty smells away. A cheap humidity meter tells you; a dehumidifier fixes it.',
    months: [7], condition: notSlab, minutes: 10, diy: true,
  },
];

// Typical lifespans for the "Systems at a glance" report — typical ranges, not predictions.
// [low, high] in years. high = null means "and up".
export const LIFESPANS = {
  roof: { asphalt: [20, 25], metal: [40, 70], tile: [50, null] },
  waterHeater: { 'tank-gas': [8, 12], 'tank-electric': [8, 12], tankless: [15, 20] },
  heating: {
    'gas-furnace': [15, 20], 'oil-furnace': [15, 20], 'electric-furnace': [20, 30],
    'gas-boiler': [15, 30], 'oil-boiler': [15, 30], 'heat-pump': [10, 15],
  },
  centralAC: [12, 17],
  sumpPump: [7, 10],
  smokeAlarm: [10, 10],
  coAlarm: [5, 7],
};
