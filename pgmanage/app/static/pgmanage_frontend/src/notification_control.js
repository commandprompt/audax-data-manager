import { useToast } from 'vue-toast-notification';
import escape from 'lodash/escape';

/**
 * Show a toast notification with a specified type and message.
 *
 * @param {string} type - The type of the toast notification.
 *                       Possible values: 'success', 'info', 'warning', 'error', 'default'
 * @param {string} message - The message to display in the toast.
 */
function showToast(type, message) {
  const titleMap = {
    'error': 'Failed',
    'success': 'Success',
    'info': 'Information',
    'default': 'Done'
  };

  let title = titleMap[type] || titleMap['default']
  let scrollableClass = type === 'error' ? 'v-toast-scrollable' : ''
  let message_lines = message.split("\n").filter(l => l.trim())
  let message_formatted = message_lines.map((line) => {return `<p>${escape(line).replace('$install_guide$', '<a target="_blank" href="https://audax.readthedocs.io/en/latest/en/01_installation.html#install-postgres-client-binaries">Postgresql Client Installation</a>')}</p>`}).join('')
  let html_msg = `<div class="v-toast__body p-0" >
                    <h3 class="fw-bold">${title}</h3>
                    <p class="${scrollableClass}">${message_formatted}</p>
                  </div>`
  const $toast = useToast()

  $toast.open({
    message: html_msg,
    type: type,
    duration: type === 'error' ? 30000 : 3000,
    pauseOnHover: type === 'error',
    dismissible: type !== 'error' 
  })
}

export { showToast };
