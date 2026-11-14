/**
 * HTML templating with auto-escaping to eliminate XSS vulnerabilities.
 * Rule: innerHTML is strictly prohibited anywhere outside this module.
 */

class SafeHtml {
  constructor(html) {
    this.value = html;
  }
  toString() {
    return this.value;
  }
}

export function escapeHtml(value) {
  if (value == null) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Marks a string as trusted HTML (e.g. static icons, pre-sanitized markdown).
 */
export function raw(value) {
  return new SafeHtml(value == null ? '' : String(value));
}

/**
 * Tagged template literal for auto-escaped HTML generation.
 */
export function html(strings, ...values) {
  let result = '';
  for (let i = 0; i < strings.length; i++) {
    result += strings[i];
    if (i < values.length) {
      const val = values[i];
      if (val instanceof SafeHtml) {
        result += val.value;
      } else if (Array.isArray(val)) {
        result += val.map(v => (v instanceof SafeHtml ? v.value : escapeHtml(v))).join('');
      } else {
        result += escapeHtml(val);
      }
    }
  }
  return new SafeHtml(result);
}

/**
 * The single approved point of mutation for element innerHTML across the entire frontend.
 */
export function render(target, content) {
  const el = typeof target === 'string' ? document.querySelector(target) : target;
  if (!el) return;
  el.innerHTML = content instanceof SafeHtml ? content.value : escapeHtml(content);
}
