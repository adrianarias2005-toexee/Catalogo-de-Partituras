/* ============================================================
   Chat panel — Asistente de Partituras
   ============================================================ */

(function () {
  'use strict';

  // Historial de mensajes: máximo 20 pares {role, content}
  var history = [];
  var MAX_HISTORY = 20;

  // ----------------------------------------------------------------
  // Helpers de DOM
  // ----------------------------------------------------------------

  function chatMessages() {
    return document.getElementById('chat-messages');
  }

  function chatInput() {
    return document.getElementById('chat-input');
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /**
   * Convierte markdown básico a HTML:
   *   **texto**  →  <strong>texto</strong>
   *   *texto*    →  <em>texto</em>
   *   saltos de línea  →  <br>
   */
  function renderMarkdown(text) {
    var escaped = escapeHtml(text);
    // Bold
    escaped = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    escaped = escaped.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Bullet lines starting with • (ya escapadas)
    escaped = escaped.replace(/^• /gm, '<span class="chat-bullet">• </span>');
    // Newlines
    escaped = escaped.replace(/\n/g, '<br>');
    return escaped;
  }

  function scrollToBottom() {
    var msgs = chatMessages();
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  /**
   * Agrega un mensaje al panel y al historial.
   * @param {string} role  'user' | 'assistant'
   * @param {string} text  Contenido del mensaje
   * @param {boolean} skipHistory  Si es true, solo muestra (no guarda en history)
   */
  function appendMessage(role, text, skipHistory) {
    if (!skipHistory) {
      history.push({ role: role, content: text });
      // Mantener máximo MAX_HISTORY mensajes
      if (history.length > MAX_HISTORY) {
        history.splice(0, history.length - MAX_HISTORY);
      }
    }

    var div = document.createElement('div');
    div.className = 'chat-msg ' + (role === 'user' ? 'chat-user' : 'chat-bot');

    if (role === 'user') {
      div.textContent = text;
    } else {
      div.innerHTML = renderMarkdown(text);
    }

    var msgs = chatMessages();
    if (msgs) {
      msgs.appendChild(div);
      scrollToBottom();
    }
    return div;
  }

  /**
   * Muestra un indicador de "pensando..." y devuelve la función para quitarlo.
   */
  function showThinking() {
    var div = document.createElement('div');
    div.className = 'chat-msg chat-bot chat-thinking';
    div.textContent = 'Pensando…';
    var msgs = chatMessages();
    if (msgs) {
      msgs.appendChild(div);
      scrollToBottom();
    }
    return function removeThinking() {
      if (div.parentNode) div.parentNode.removeChild(div);
    };
  }

  // ----------------------------------------------------------------
  // Lógica principal: enviar mensaje
  // ----------------------------------------------------------------

  function sendChat() {
    var input = chatInput();
    if (!input) return;
    var text = input.value.trim();
    if (!text) return;

    input.value = '';
    appendMessage('user', text);

    var removeThinking = showThinking();

    // Deshabilitar input mientras se espera
    input.disabled = true;
    var sendBtn = document.getElementById('chat-send-btn');
    if (sendBtn) sendBtn.disabled = true;

    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history })
    })
      .then(function (res) {
        if (!res.ok) {
          return res.json().then(function (data) {
            throw new Error(data.detail || 'Error HTTP ' + res.status);
          });
        }
        return res.json();
      })
      .then(function (data) {
        removeThinking();
        var reply = data.response || data.reply || JSON.stringify(data);
        appendMessage('assistant', reply);
      })
      .catch(function (err) {
        removeThinking();
        var errMsg = document.createElement('div');
        errMsg.className = 'chat-msg chat-bot chat-error';
        errMsg.textContent = 'Error: ' + (err.message || 'No se pudo conectar con el asistente.');
        var msgs = chatMessages();
        if (msgs) {
          msgs.appendChild(errMsg);
          scrollToBottom();
        }
      })
      .finally(function () {
        input.disabled = false;
        if (sendBtn) sendBtn.disabled = false;
        input.focus();
      });
  }

  // ----------------------------------------------------------------
  // Toggle del panel
  // ----------------------------------------------------------------

  window.toggleChat = function () {
    var panel = document.getElementById('chat-panel');
    if (!panel) return;
    var isHidden = panel.style.display === 'none' || panel.style.display === '';
    panel.style.display = isHidden ? 'flex' : 'none';
    if (isHidden) {
      var input = chatInput();
      if (input) input.focus();
    }
  };

  // ----------------------------------------------------------------
  // Exponer sendChat globalmente (llamado desde onclick en HTML)
  // ----------------------------------------------------------------

  window.sendChat = sendChat;

  // ----------------------------------------------------------------
  // Event listeners al cargar el DOM
  // ----------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', function () {
    var input = chatInput();
    if (input) {
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendChat();
        }
      });
    }
  });
})();
