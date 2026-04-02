// js/dom.js
export const card                = document.getElementById('card');
export const titleEl             = document.getElementById('title');
export const descEl              = document.getElementById('desc');
export const conceptLabelEl      = document.getElementById('concept-label');
export const heroStateChipEl     = document.getElementById('hero-state-chip');
export const heroPrimaryActionEl = document.getElementById('hero-primary-action');
export const primaryControls     = document.getElementById('primary-controls');
export const drillControls       = document.getElementById('drill-controls');
export const consolidateControls = document.getElementById('consolidate-controls');
export const timerDisplay        = document.getElementById('timer-display');
export const devBtn              = document.getElementById('dev-btn');
export const drawer              = document.getElementById('drawer');
export const drawerToggle        = document.getElementById('drawer-toggle');
export const conceptListEl       = document.getElementById('concept-list');
export const addTriggerArea      = document.getElementById('add-trigger-area');
export const heroInfo            = document.getElementById('hero-info');
export const drillUi             = document.getElementById('drill-ui');
export const chatHistory         = document.getElementById('chat-history');
export const chatInput           = document.getElementById('chat-input');
export const drillTitle          = document.getElementById('drill-title');

export const TILE_IDS = ['tile-0','tile-1','tile-2','tile-3'];
export const tileEls  = TILE_IDS.map(id => document.getElementById(id));

export const POLYGON_IDS = [
  'cp-top','cp-upper-left','cp-upper-right',
  'cp-lower-left','cp-lower-right',
  'cp-bottom-tip','cp-specular','cp-glow',
];
