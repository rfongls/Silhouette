// static/js/pipeline_bus.js
(() => {
  'use strict';
  const Bus = {
    payload: null,
    set(stage, text, meta = {}) {
      this.payload = { stage, text: String(text || ''), meta, ts: Date.now() };
    },
    take() {
      const current = this.payload;
      this.payload = null;
      return current;
    },
    peek() {
      return this.payload;
    }
  };
  window.PipelineBus = Bus;
})();
